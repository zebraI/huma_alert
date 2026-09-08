#!/usr/bin/env python3
"""
Bot de surveillance - Camping Fête de l'Huma 2026.
Version légère : appel API direct, sans navigateur.

Variables d'environnement requises :
    DISCORD_WEBHOOK_URL   URL du webhook Discord
    NTFY_TOPIC            Nom du topic ntfy
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
        return
    resp = requests.post(webhook_url, json={"content": message, "username": "Huma Camping Bot"}, timeout=15)
    if resp.status_code not in (200, 204):
        print(f"[!] Discord: {resp.status_code} {resp.text}")


def send_ntfy(message: str, title: str = "Huma Camping Bot", priority: int = 5) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    resp = requests.post("https://ntfy.sh", json={
        "topic": topic, "title": title, "message": message, "priority": priority, "tags": ["camping"],
    }, timeout=15)
    if resp.status_code != 200:
        print(f"[!] ntfy: {resp.status_code} {resp.text}")


def notify(message: str, title: str = "Huma Camping Bot", priority: int = 5) -> None:
    send_discord(message)
    send_ntfy(message, title=title, priority=priority)


def load_last_state() -> int:
    if os.path.exists(STATE_FILE):
        try:
            return int(open(STATE_FILE).read().strip())
        except ValueError:
            return 0
    return 0

def save_state(nb: int) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(str(nb))

def load_error_count() -> int:
    if os.path.exists(ERROR_FILE):
        try:
            return int(open(ERROR_FILE).read().strip())
        except ValueError:
            return 0
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
                notify(f"Le bot CAMPING a plante 3 fois d'affilee.\nErreur : {e}", title="Bot camping en erreur", priority=3)
            except Exception:
                pass
        elif error_count % 10 == 0:
            try:
                notify(f"Le bot CAMPING est en erreur depuis {error_count} checks.", title="Bot camping bloque", priority=3)
            except Exception:
                pass
        return

    save_error_count(0)
    last_count = load_last_state()
    print(f"[CAMPING] {nb_tickets} billet(s) en revente (precedent: {last_count})")

    if nb_tickets > last_count:
        new_tickets = nb_tickets - last_count
        try:
            notify(
                f"{new_tickets} nouveau(x) billet(s) CAMPING en revente ! ({nb_tickets} au total)\n"
                f"{TICKET_PAGE}\nFonce, ca part en secondes.",
                title="BILLET(S) CAMPING DISPO !", priority=5,
            )
        except Exception as e:
            print(f"[!] Erreur envoi notification: {e}")
    save_state(nb_tickets)


def run_test() -> None:
    print("[CAMPING] Mode test...")
    try:
        notify("Test CAMPING reussi ! Le bot fonctionne.", title="Test camping reussi", priority=5)
    except Exception as e:
        print(f"[!] Erreur test: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        run_test()
    if args.loop:
        print(f"[CAMPING] Surveillance toutes les {args.interval}s.")
        while True:
            run_once()
            time.sleep(args.interval)
    elif not args.test:
        run_once()


if __name__ == "__main__":
    main()
