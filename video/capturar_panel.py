"""Captura el panel del vendedor (local) para el video y la evidencia. Navegador sin ventana, una sola página.

Uso (con el panel corriendo en 127.0.0.1:8800):
  <python con playwright> video/capturar_panel.py
"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
ENV = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
DESTINOS = [Path(r"C:\Users\FERNANDO VEGA\Desktop\proyecto-video-ai\public\firebox\panel_vendedor.png"),
            RAIZ / "docs" / "documentacion" / "evidencias" / "panel" / "panel_vendedor.png"]

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1600, "height": 960}, device_scale_factor=1.2,
                          http_credentials={"username": ENV["PANEL_USUARIO"].strip(), "password": ENV["PANEL_CLAVE"].strip()})
    pagina = ctx.new_page()
    pagina.goto("http://127.0.0.1:8800/panel", wait_until="domcontentloaded")
    pagina.wait_for_selector("td.mono", timeout=30000)
    pagina.wait_for_selector("ol.actividad, p.vacio", timeout=10000)
    time.sleep(1.0)  # fuentes de Google
    for d in DESTINOS:
        d.parent.mkdir(parents=True, exist_ok=True)
        pagina.screenshot(path=str(d), full_page=False)
        print(d)
    nav.close()
