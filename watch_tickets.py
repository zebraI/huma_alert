#!/usr/bin/env python3
"""
Bot de surveillance des billets de camping - Fête de l'Huma 2026.

Vérifie périodiquement la page officielle de billetterie et envoie une
notification Discord dès qu'un billet "Camping" redevient disponible
(revente officielle SeeTickets).

Variables d'environnement requises :
    DISCORD_WEBHOOK_URL   URL du webhook Discord (Paramètres du salon > Intégrations > Webhooks)

Utilisation locale :
    pip install playwright requests
    playwright install chromium
    python watch_tickets.py

En boucle continue (mode local) :
    python watch_tickets.py --loop --interval 300
"""

import argparse
import os
import sys
import time

import requests
from playwright.sync_api import sync_playwright

TICKET_URL = "https://resell.seetickets.com/fete-de-lhumanite-2026/event/2915/fete-de-l-humanite-2026-camping"

# Texte exact affiché quand aucun billet n'est en revente
NO_TICKET_TEXT = "aucun billet disponible"

STATE_FILE = os.path.join(os.path.dirname(__file__), "last_state.txt")


def check_availability() -> tuple[bool, str]:
    """Charge la page de revente avec un vrai navigateur headless."""
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
        # Laisse le temps aux scripts de la billetterie de charger le stock
        page.wait_for_timeout(3000)
        body_text = page.inner_text("body").lower()
        browser.close()

    available = NO_TICKET_TEXT not in body_text
    return available, body_text[:500]  # extrait pour debug


def send_discord(message: str) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[!] DISCORD_WEBHOOK_URL non défini, notification impossible.")
        print(message)
        return

    payload = {
        "content": message,
        "username": "Huma Ticket Bot 🎪",
    }
    resp = requests.post(webhook_url, json=payload, timeout=15)
    if resp.status_code not in (200, 204):
        print(f"[!] Échec envoi Discord: {resp.status_code} {resp.text}")


def load_last_state() -> str:
    if os.path.exists(STATE_FILE):
        return open(STATE_FILE).read().strip()
    return "unknown"


def save_state(state: str) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(state)


ERROR_FILE = os.path.join(os.path.dirname(__file__), "error_count.txt")


def load_error_count() -> int:
    if os.path.exists(ERROR_FILE):
        return int(open(ERROR_FILE).read().strip())
    return 0


def save_error_count(count: int) -> None:
    with open(ERROR_FILE, "w") as f:
        f.write(str(count))


def run_once() -> None:
    try:
        available, sample = check_availability()
    except Exception as e:
        error_count = load_error_count() + 1
        save_error_count(error_count)
        print(f"[!] Erreur pendant la vérification ({error_count} consécutive(s)): {e}")

        # Alerte au bout de 3 erreurs d'affilée, puis toutes les 10
        if error_count == 3:
            send_discord(
                "⚠️ **Le bot a planté 3 fois d'affilée.**\n"
                f"Erreur : `{e}`\n"
                "Le site bloque peut-être les requêtes. Vérifie dans les logs GitHub Actions."
            )
        elif error_count % 10 == 0:
            send_discord(
                f"🔴 **Le bot est en erreur depuis {error_count} checks.**\n"
                "Il est probablement bloqué par le site."
            )
        return

    # Remise à zéro du compteur d'erreurs si le check passe
    save_error_count(0)

    new_state = "available" if available else "sold_out"
    last_state = load_last_state()

    print(f"[i] État actuel: {new_state} (précédent: {last_state})")

    if new_state == "available":
        # On notifie à chaque check tant que c'est dispo, pour ne rater aucune fenêtre,
        # mais on peut réduire à "seulement si ça vient de changer" en décommentant la condition
        # if last_state != "available":
        send_discord(
            "🎪 **Billet(s) CAMPING disponible(s) pour la Fête de l'Huma !**\n"
            f"{TICKET_URL}\nFonce, le stock peut repartir vite."
        )

    save_state(new_state)


def run_test() -> None:
    """Envoie une notification de test pour vérifier que le webhook Discord fonctionne."""
    print("[i] Mode test : envoi d'une notification Discord...")
    send_discord(
        "✅ **Test réussi !** Le bot de surveillance Fête de l'Huma fonctionne.\n"
        "Tu recevras un message ici dès qu'un billet camping apparaît en revente."
    )
    print("[i] Si tu as reçu le message sur Discord, tout est bon !")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Tourne en continu")
    parser.add_argument("--interval", type=int, default=300, help="Intervalle en secondes (mode --loop)")
    parser.add_argument("--test", action="store_true", help="Envoie une notif de test et quitte")
    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.loop:
        print(f"Surveillance en continu, toutes les {args.interval}s. Ctrl+C pour arrêter.")
        while True:
            run_once()
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
