#!/usr/bin/env python3
"""Capture toutes les requêtes réseau faites par la page de revente."""

from playwright.sync_api import sync_playwright

TICKET_URL = "https://resell.seetickets.com/fete-de-lhumanite-2026/event/2915/fete-de-l-humanite-2026-camping"

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

    # Capture TOUTES les requêtes
    requests_log = []

    def on_request(request):
        requests_log.append({
            "method": request.method,
            "url": request.url,
            "type": request.resource_type,
        })

    def on_response(response):
        req = response.request
        content_type = response.headers.get("content-type", "")
        # On ne log le body que pour les XHR/fetch JSON (pas les images/CSS/JS)
        body = ""
        if req.resource_type in ("xhr", "fetch") or "json" in content_type:
            try:
                body = response.text()[:2000]
            except Exception:
                body = "(impossible de lire le body)"

        print(f"\n{'='*80}")
        print(f"[{req.resource_type.upper()}] {req.method} {req.url}")
        print(f"  Status: {response.status}")
        print(f"  Content-Type: {content_type}")
        if body:
            print(f"  Body (2000 premiers chars):\n{body}")

    page.on("request", on_request)
    page.on("response", on_response)

    page.goto(TICKET_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    print(f"\n\n{'#'*80}")
    print(f"RÉSUMÉ: {len(requests_log)} requêtes capturées")
    print(f"{'#'*80}")
    for r in requests_log:
        print(f"  [{r['type']:>10}] {r['method']} {r['url']}")

    browser.close()
