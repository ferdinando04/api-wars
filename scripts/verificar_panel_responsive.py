"""Verifica que el panel no se salga de la pantalla en ningún ancho (escritorio, portátil, tableta, celular).

Abre el panel real (127.0.0.1:8800) con Playwright en varios tamaños, mide si la página tiene scroll horizontal y qué
elementos se salen por la derecha, y guarda una captura por tamaño en docs/documentacion/evidencias/panel/responsive/.
Sale con código 1 si algún tamaño se desborda.

Uso (con el panel corriendo):
  <python con playwright> scripts/verificar_panel_responsive.py
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
ENV = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
SALIDA = RAIZ / "docs" / "documentacion" / "evidencias" / "panel" / "responsive"
URL = "http://127.0.0.1:8800/panel"

# (nombre, ancho, alto): el 1351 es el área útil de Chrome en una pantalla de 1366 con su barra de scroll.
TAMANOS = [("escritorio-1920", 1920, 1080), ("portatil-1366", 1351, 657), ("portatil-1280", 1280, 720),
           ("tableta-1024", 1024, 768), ("tableta-768", 768, 1024), ("celular-390", 390, 844)]

MEDIR = """() => {
  const ancho = document.documentElement.clientWidth;
  const fuera = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.tabla-scroll') && !el.classList.contains('tabla-scroll')) continue;  // la tabla puede tener su propio scroll
    if (el.closest('dialog')) continue;
    const r = el.getBoundingClientRect();
    if (r.width && r.right > ancho + 1) fuera.push((el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ').join('.') : '')) + ' → ' + Math.round(r.right) + ' px');
  }
  const t = document.querySelector('.tabla-scroll');
  return { ancho, pagina: document.documentElement.scrollWidth, fuera: fuera.slice(0, 8),
           tabla: t ? { visible: t.clientWidth, contenido: t.scrollWidth } : null };
}"""


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    fallas = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nombre, ancho, alto in TAMANOS:
            ctx = nav.new_context(viewport={"width": ancho, "height": alto},
                                  http_credentials={"username": ENV["PANEL_USUARIO"].strip(), "password": ENV["PANEL_CLAVE"].strip()})
            pagina = ctx.new_page()
            pagina.goto(URL, wait_until="domcontentloaded")
            pagina.wait_for_selector("#tablero-kpis .kpis", timeout=40000)
            pagina.wait_for_selector("ul.conexiones", timeout=40000)
            time.sleep(1.2)  # fuentes de Google
            m = pagina.evaluate(MEDIR)
            desborda = m["pagina"] > m["ancho"] + 1 or m["fuera"]
            tabla = m["tabla"]
            scroll_tabla = tabla and tabla["contenido"] > tabla["visible"] + 1
            estado = "SE SALE" if desborda else "ok"
            print(f"{nombre:16} {estado:8} página {m['pagina']}/{m['ancho']} px · tabla "
                  f"{'con scroll propio' if scroll_tabla else 'cabe entera'}" + (f" ({tabla['contenido']}/{tabla['visible']})" if scroll_tabla else ""))
            for f in m["fuera"]:
                print("      fuera:", f)
            if desborda:
                fallas += 1
            pagina.screenshot(path=str(SALIDA / f"{nombre}.png"), full_page=True)
            ctx.close()
        nav.close()
    print(f"\n{len(TAMANOS) - fallas}/{len(TAMANOS)} tamaños sin desborde · capturas en {SALIDA.relative_to(RAIZ)}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
