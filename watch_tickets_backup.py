#!/usr/bin/env python3
"""Version backup avec Playwright (plus lente mais vérifie le rendu réel de la page)."""

import os
import requests
from playwright.sync_api import sync_playwright

TICKET_URL = "https://resell.seetickets.com/fete-de-lhumanite-2026/event/2915/fete-de-l-humanite-2026-camping"
NO_TICKET_TEXT = "aucun billet disponible"
STATE_FILE = os.path.join(os.path.dirname(__file__), "last_state_backup.txt")


def check_availability() -> bool:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
        )
        page = context.new_page()
        page.goto(TICKET_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        body_text = page.inner_text("body").lower()
        browser.close()

    return NO_TICKET_TEXT not in body_text


def notify(message, title="Huma Backup Bot", priority=5):
    # Discord
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        requests.post(webhook_url, json={"content": message, "username": "Huma Backup Bot"}, timeout=15)
    # ntfy
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        requests.post("https://ntfy.sh", json={
            "topic": topic, "title": title, "message": message, "priority": priority,
        }, timeout=15)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print("[BACKUP] Mode test...")
        notify("Test backup reussi ! Le bot Playwright fonctionne.", title="Test backup reussi", priority=5)
        print("[BACKUP] Verifie Discord ET ntfy !")
        return

    last_state = "unknown"
    if os.path.exists(STATE_FILE):
        last_state = open(STATE_FILE).read().strip()

    try:
        available = check_availability()
    except Exception as e:
        print(f"[BACKUP] Erreur: {e}")
        return

    new_state = "available" if available else "sold_out"
    print(f"[BACKUP] Etat: {new_state} (precedent: {last_state})")

    if new_state == "available" and last_state != "available":
        notify(
            f"[BACKUP] Billet(s) CAMPING detecte(s) sur la page !\n{TICKET_URL}",
            title="BACKUP - BILLET CAMPING DISPO !",
        )

    with open(STATE_FILE, "w") as f:
        f.write(new_state)


if __name__ == "__main__":
    main()
