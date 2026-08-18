#!/usr/bin/env python3
"""
Bot de surveillance des billets de camping - Fête de l'Huma 2026.
Version légère : appel API direct, sans navigateur.

Variables d'environnement requises :
    DISCORD_WEBHOOK_URL   URL du webhook Discord
    NTFY_TOPIC            Nom du topic ntfy

Utilisation :
    python watch_tickets.py              # une seule vérification
    python watch_tickets.py --loop       # en continu (toutes les 30s par défaut)
    python watch_tickets.py --test       # notification de test
"""

import argparse
import os
import time

import requests

API_URL = (
    "https://resell.seetickets.com/api/categories"
    "?event=2915&isActive=1&activeEvent=true"
    "&order[rank]=asc&order[startDate]=asc&order[nbTicket]=desc"
    "&page=1&itemsPerPage=9"
)

TICKET_PAGE = "https://resell.seetickets.com/fete-de-lhumanite-2026/event/2915/fete-de-l-humanite-2026-camping"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/ld+json, application/json",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": TICKET_PAGE,
}

STATE_FILE = os.path.join(os.path.dirname(__file__), "last_state.txt")
ERROR_FILE = os.path.join(os.path.dirname(__file__), "error_count.txt")


def check_availability() -> tuple[bool, int]:
    """Appelle l'API et retourne (dispo, nb_tickets)."""
    resp = requests.get(API_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    members = data.get("hydra:member", [])
    if not members:
        return False, 0

    nb_tickets = members[0].get("nbTicket", 0)
    return nb_tickets > 0, nb_tickets


def send_discord(message: str) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[!] DISCORD_WEBHOOK_URL non défini.")
        return
    resp = requests.post(
        webhook_url,
        json={"content": message, "username": "Huma Ticket Bot"},
        timeout=15,
    )
    if resp.status_code not in (200, 204):
        print(f"[!] Discord: {resp.status_code} {resp.text}")


def send_ntfy(message: str, title: str = "Huma Ticket Bot", priority: int = 5) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("[!] NTFY_TOPIC non défini.")
        return
    resp = requests.post(
        "https://ntfy.sh",
        json={
            "topic": topic,
            "title": title,
            "message": message,
            "priority": priority,
            "tags": ["tickets", "camping"],
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[!] ntfy: {resp.status_code} {resp.text}")


def notify(message: str, title: str = "Huma Ticket Bot", priority: int = 5) -> None:
    send_discord(message)
    send_ntfy(message, title=title, priority=priority)


def load_last_state() -> int:
    if os.path.exists(STATE_FILE):
        try:
            return int(open(STATE_FILE).read().strip())
        except ValueError:
            return 0
    return 0

def save_state(nb_tickets: int) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(str(nb_tickets))

def load_error_count() -> int:
    if os.path.exists(ERROR_FILE):
        return int(open(ERROR_FILE).read().strip())
    return 0

def save_error_count(count: int) -> None:
    with open(ERROR_FILE, "w") as f:
        f.write(str(count))


def run_once() -> None:
    try:
        available, nb_tickets = check_availability()
    except Exception as e:
        error_count = load_error_count() + 1
        save_error_count(error_count)
        print(f"[!] Erreur ({error_count} consecutives): {e}")
        if error_count == 3:
            try:
                notify(
                    f"Le bot a plante 3 fois d'affilee.\nErreur : {e}",
                    title="Bot en erreur", priority=3,
                )
            except Exception:
                print("[!] Impossible d'envoyer la notif d'erreur")
        elif error_count % 10 == 0:
            try:
                notify(
                    f"Le bot est en erreur depuis {error_count} checks.",
                    title="Bot bloque", priority=3,
                )
            except Exception:
                print("[!] Impossible d'envoyer la notif d'erreur")
        return

    save_error_count(0)
    last_count = load_last_state()
    print(f"[i] {nb_tickets} billet(s) en revente (precedent: {last_count})")

    if nb_tickets > last_count:
        new_tickets = nb_tickets - last_count
        try:
            notify(
                f"{new_tickets} nouveau(x) billet(s) CAMPING en revente ! ({nb_tickets} au total)\n"
                f"{TICKET_PAGE}\nFonce, ca part en secondes.",
                title=f"BILLET(S) CAMPING DISPO !", priority=5,
            )
        except Exception as e:
            print(f"[!] Erreur envoi notification: {e}")
    save_state(nb_tickets)


def run_test() -> None:
    print("[i] Mode test...")
    notify(
        "Test reussi ! Le bot fonctionne.\n"
        "Tu recevras un message ici des qu'un billet camping apparait.",
        title="Test reussi", priority=5,
    )
    print("[i] Verifie Discord ET ntfy !")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.loop:
        print(f"Surveillance toutes les {args.interval}s. Ctrl+C pour arreter.")
        while True:
            run_once()
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
