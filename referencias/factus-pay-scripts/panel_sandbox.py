# -*- coding: utf-8 -*-
"""Entra al panel sandbox de Factus Pay con las credenciales del .env de Retos_Factus (nunca en el chat), fotografía el panel y el
simulador, y vuelca los controles de cada pantalla. Uso: python panel_sandbox.py [explorar|simular <reference_code> <resultado>]"""
import io, re, sys, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ENV = Path("C:/Users/FERNANDO VEGA/Desktop/Retos_Factus/.env")
env = dict(l.strip().split("=", 1) for l in io.open(ENV, encoding="utf-8") if "=" in l and not l.startswith("#"))
BASE = env["FACTUS_PAY_SANDBOX_URL"].strip(); EMAIL = env["FACTUS_PAY_SANDBOX_EMAIL"].strip(); PW = env["FACTUS_PAY_SANDBOX_PASSWORD"].strip()
AQUI = Path(__file__).resolve().parent
modo = sys.argv[1] if len(sys.argv) > 1 else "explorar"


def controles(page):
    return page.evaluate("""() => [...document.querySelectorAll('a[href], button, input, select, textarea, [role=button]')]
      .filter(e => e.offsetParent !== null)
      .map(e => ({tag: e.tagName.toLowerCase(), tipo: e.type || null, nombre: (e.name === 'password' || e.type === 'password') ? '(contraseña)' : (e.getAttribute('aria-label') || e.innerText || e.value || e.placeholder || e.name || e.title || '').trim().replace(/\\s+/g,' ').slice(0, 80), href: e.getAttribute('href') || null, name: e.getAttribute('name') || null}))""")


def texto(page):
    return re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText")).strip()


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1366, "height": 900}, locale="es-CO")
    page = ctx.new_page()
    page.goto(BASE + "/login", wait_until="networkidle"); time.sleep(1)
    page.fill("input[name=email], input[type=email]", EMAIL)
    page.fill("input[name=password], input[type=password]", PW)
    page.click("button[type=submit]")
    try:
        page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
    except Exception:
        print("no salió de /login; texto:", texto(page)[:400])
    page.wait_for_load_state("networkidle"); time.sleep(2)
    print("después del login:", page.url, "·", page.title())
    page.screenshot(path=str(AQUI / "panel-01-inicio.png"), full_page=True)
    print("== controles del inicio"); [print("  ", c) for c in controles(page)]
    io.open(AQUI / "panel-01-inicio.txt", "w", encoding="utf-8").write(texto(page))
    # recorrer los enlaces del menú (mismo dominio) y fotografiar cada pantalla
    vistos = set()
    for c in controles(page):
        h = c.get("href") or ""
        if h.startswith(BASE) and h not in vistos and "logout" not in h:
            vistos.add(h)
    if modo == "explorar":
        for i, h in enumerate(sorted(vistos), start=2):
            try:
                page.goto(h, wait_until="networkidle"); time.sleep(1.5)
                nombre = re.sub(r"[^a-z0-9]+", "-", h.replace(BASE, "").lower()).strip("-") or "raiz"
                page.screenshot(path=str(AQUI / f"panel-{i:02d}-{nombre}.png"), full_page=True)
                io.open(AQUI / f"panel-{i:02d}-{nombre}.txt", "w", encoding="utf-8").write(texto(page))
                print(f"== {h} → panel-{i:02d}-{nombre}.png"); [print("  ", c) for c in controles(page)[:40]]
            except Exception as e:
                print("   error en", h, e)
    if modo == "ver":
        for ruta, nombre in (("/qrcodes/01m3cwy8r48fhzeqm6mzkf9cyn", "qrcodes"), ("/simulator", "simulador")):
            page.goto(BASE + ruta, wait_until="networkidle"); time.sleep(1.5)
            print("==", ruta, "→", page.url); [print("  ", c) for c in controles(page)]
            io.open(AQUI / f"{nombre}.html", "w", encoding="utf-8").write(page.content())
            io.open(AQUI / f"{nombre}.txt", "w", encoding="utf-8").write(texto(page))
            page.screenshot(path=str(AQUI / f"{nombre}-00.png"), full_page=True)
            print("   texto:", texto(page)[:900].replace(chr(10), " / "))
    b.close()
