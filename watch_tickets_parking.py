#!/usr/bin/env python3
"""
Bot de surveillance - Parking Fête de l'Huma 2026.
Surveille Parking Campeurs + Parking Camping-Car.
"""

import argparse
import json
import os
import time

import requests

API_URL = (
    "https://resell.seetickets.com/api/categories"
    "?event=2916&isActive=1&activeEvent=true"
    "&order[rank]=asc&order[startDate]=asc&order[nbTicket]=desc"
    "&page=1&itemsPerPage=20"
)

TICKET_PAGE = "https://resell.seetickets.com/fete-de-lhumanite-2026/event/2916/fete-de-l-humanite-2026-parking"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/ld+json, application/json",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": TICKET_PAGE,
}

# Catégories à surveiller avec leurs mots-clés
WATCHED = [
    {"name": "Parking Campeurs", "keywords": ["campeur"]},
    {"name": "Parking Camping-Car", "keywords": ["camping-car", "camping car", "van"]},
]

STATE_FILE = os.path.join(os.path.dirname(__file__), "last_state_parking.json")
ERROR_FILE = os.path.join(os.path.dirname(__file__), "error_count_parking.txt")


def check_all() -> dict[str, int]:
    resp = requests.get(API_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    categories = resp.json().get("hydra:member", [])

    results = {}
    for w in WATCHED:
        nb = 0
        for cat in categories:
            name = cat.get("name", {})
            if isinstance(name, dict):
                name = " ".join(name.values())
            name = name.lower()
            if any(kw in name for kw in w["keywords"]):
                nb = cat.get("nbTicket", 0)
                break
        results[w["name"]] = nb
    return results


def send_discord(message: str) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    resp = requests.post(webhook_url, json={"content": message, "username": "Huma Parking Bot"}, timeout=15)
    if resp.status_code not in (200, 204):
        print(f"[!] Discord: {resp.status_code} {resp.text}")


def send_ntfy(message: str, title: str = "Huma Parking Bot", priority: int = 5) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    resp = requests.post("https://ntfy.sh", json={
        "topic": topic, "title": title, "message": message, "priority": priority, "tags": ["parking"],
    }, timeout=15)
    if resp.status_code != 200:
        print(f"[!] ntfy: {resp.status_code} {resp.text}")


def notify(message: str, title: str = "Huma Parking Bot", priority: int = 5) -> None:
    send_discord(message)
    send_ntfy(message, title=title, priority=priority)


def load_state() -> dict[str, int]:
    if os.path.exists(STATE_FILE):
        try:
            return json.loads(open(STATE_FILE).read())
        except (ValueError, json.JSONDecodeError):
            return {}
    return {}

def save_state(state: dict[str, int]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

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
        results = check_all()
    except Exception as e:
        error_count = load_error_count() + 1
        save_error_count(error_count)
        print(f"[!] Erreur ({error_count} consecutives): {e}")
        if error_count == 3:
            try:
                notify(f"Le bot PARKING a plante 3 fois d'affilee.\nErreur : {e}",
                       title="Bot parking en erreur", priority=3)
            except Exception:
                pass
        return

    save_error_count(0)
    last_state = load_state()

    parts = []
    for name, nb in results.items():
        prev = last_state.get(name, 0)
        parts.append(f"{name}: {nb} (prec: {prev})")

        if nb > prev:
            new_tickets = nb - prev
            try:
                notify(
                    f"{new_tickets} nouveau(x) billet(s) {name} en revente ! ({nb} au total)\n"
                    f"{TICKET_PAGE}\nFonce, ca part en secondes.",
                    title=f"BILLET(S) {name.upper()} DISPO !",
                    priority=5,
                )
            except Exception as e:
                print(f"[!] Erreur envoi notification: {e}")

    print(f"[PARKING] {' | '.join(parts)}")
    save_state(results)


def run_test() -> None:
    print("[PARKING] Mode test...")
    try:
        notify("Test PARKING reussi ! Le bot surveille Parking Campeurs + Camping-Car.",
               title="Test parking reussi", priority=5)
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
        print(f"[PARKING] Surveillance toutes les {args.interval}s.")
        while True:
            run_once()
            time.sleep(args.interval)
    elif not args.test:
        run_once()


if __name__ == "__main__":
    main()
