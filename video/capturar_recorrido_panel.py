"""Captura el panel real en cada estado que muestra la escena 8b del video (recorrido botón por botón).

Por cada estado guarda una imagen 1920×1344 (viewport 1600×1120 a 1,2x) y las cajas de cada botón en píxeles de esa imagen,
para que el cursor y la cámara del video lleguen exactamente a donde está cada cosa. También baja del panel el XML y el CSV
reales para mostrarlos. Solo lectura: el botón "Vender" se señala, nunca se oprime.

Uso (con el panel corriendo en 127.0.0.1:8800):
  <python con playwright> video/capturar_recorrido_panel.py
"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
ENV = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
REMOTION = Path(r"C:\Users\FERNANDO VEGA\Desktop\proyecto-video-ai")
IMAGENES = REMOTION / "public" / "firebox" / "panel"
JSON = REMOTION / "src" / "firebox" / "panel_recorrido.json"
EVIDENCIA = RAIZ / "docs" / "documentacion" / "evidencias" / "panel" / "recorrido"
URL = "http://127.0.0.1:8800"
ESCALA = 1.2
VIEWPORT = {"width": 1600, "height": 1120}

CAJAS = """(escala) => {
  const caja = (els) => {
    els = els.filter(Boolean);
    if (!els.length) return null;
    const rs = els.map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0);
    if (!rs.length) return null;
    const x = Math.min(...rs.map((r) => r.left)), y = Math.min(...rs.map((r) => r.top));
    const x2 = Math.max(...rs.map((r) => r.right)), y2 = Math.max(...rs.map((r) => r.bottom));
    return [x, y, x2 - x, y2 - y].map((v) => Math.round(v * escala));
  };
  const q = (s) => document.querySelector(s);
  const kpi = [...document.querySelectorAll('#tablero-kpis .kpi')];
  const fila = [...document.querySelectorAll('#tabla-cont tbody tr')].find((tr) => !tr.hidden);
  const filas = [...document.querySelectorAll('#tabla-cont tbody tr')].filter((tr) => !tr.hidden);
  const cajasAside = [...document.querySelectorAll('aside > .caja')];
  const btn = (i) => fila ? fila.querySelectorAll('td.acciones .btn')[i] : null;
  const dlg = q('#dialogo-qr');
  return {
    kpis1: caja(kpi.slice(0, 4)), kpis2: caja(kpi.slice(4, 8)),
    kpi_ventas: caja([kpi[0]]), kpi_facturado: caja([kpi[1]]), kpi_cobrado: caja([kpi[2]]), kpi_pendiente: caja([kpi[3]]),
    kpi_tasa: caja([kpi[4]]), kpi_ticket: caja([kpi[5]]), kpi_iva: caja([kpi[6]]), kpi_hora: caja([kpi[7]]),
    herramientas: caja([q('.herramientas')]), pestanas: caja([q('.pestanas')]),
    pagadas: caja([q('.pestanas [data-filtro=pagado]')]), porcobrar: caja([q('.pestanas [data-filtro=pendiente]')]),
    buscar: caja([q('.buscar')]), tabla: caja([q('.herramientas'), ...filas]),
    fila: caja([fila]), acciones: caja([fila && fila.querySelector('td.acciones')]),
    pdf: caja([btn(0)]), xml: caja([btn(1)]), qr: caja([btn(2)]), consultar: caja([btn(3)]),
    aviso: caja([q('#avisos .aviso')]), aviso_fila: caja([q('#avisos .aviso'), fila]),
    conexiones: caja([cajasAside[0]]), probar: caja([cajasAside[0] && cajasAside[0].querySelector('h2 .btn')]),
    venta: caja([cajasAside[1]]), campo: caja([q('#para')]), vender: caja([q('.vender')]), actividad: caja([cajasAside[2]]),
    csv: caja([q('header .enlace')]), cabecera: caja([q('header')]),
    dialogo: dlg && dlg.open ? caja([dlg]) : null,
    alto_pagina: Math.round(document.documentElement.scrollHeight * escala),
  };
}"""


def xml_destacado(xml: str) -> list[str]:
    """Las líneas del XML firmado que se muestran en el video, sacadas del XML real (recortadas si son largas)."""
    lineas = []
    for patron in [r"<cbc:ID>[^<]+</cbc:ID>", r"<cbc:UUID [^>]*>[^<]+</cbc:UUID>", r"<cbc:IssueDate>[^<]+</cbc:IssueDate>",
                   r"<cbc:IssueTime>[^<]+</cbc:IssueTime>", r"<cbc:Description>[^<]+</cbc:Description>",
                   r"<cbc:TaxAmount [^>]*>[^<]+</cbc:TaxAmount>", r"<cbc:PayableAmount [^>]*>[^<]+</cbc:PayableAmount>",
                   r"<ds:SignatureValue[^>]*>[^<]+</ds:SignatureValue>"]:
        m = re.search(patron, xml)
        if not m:
            continue
        l = re.sub(r' Id="[^"]+"', "", re.sub(r' schemeID="\d+"', "", m.group(0)))
        l = re.sub(r">([^<]{28})[^<]+<", r">\1…<", l)  # el CUFE y la firma son muy largos para pantalla
        lineas.append(l)
    return lineas


def main() -> None:
    IMAGENES.mkdir(parents=True, exist_ok=True)
    EVIDENCIA.mkdir(parents=True, exist_ok=True)
    datos: dict = {"ancho": int(VIEWPORT["width"] * ESCALA), "alto": int(VIEWPORT["height"] * ESCALA), "estados": {}}
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport=VIEWPORT, device_scale_factor=ESCALA,
                              http_credentials={"username": ENV["PANEL_USUARIO"].strip(), "password": ENV["PANEL_CLAVE"].strip()})
        pagina = ctx.new_page()
        pagina.goto(f"{URL}/panel", wait_until="domcontentloaded")
        pagina.wait_for_selector("#tablero-kpis .kpis", timeout=40000)
        pagina.wait_for_selector("ul.conexiones", timeout=40000)
        time.sleep(1.5)  # fuentes de Google
        factura = pagina.locator("#tabla-cont tbody tr td.mono").first.inner_text().split()[0]

        def foto(nombre: str) -> None:
            time.sleep(0.6)
            ruta = IMAGENES / f"{nombre}.png"
            pagina.screenshot(path=str(ruta))
            (EVIDENCIA / f"{nombre}.png").write_bytes(ruta.read_bytes())
            datos["estados"][nombre] = {"imagen": f"firebox/panel/{nombre}.png", "cajas": pagina.evaluate(CAJAS, ESCALA)}
            print(nombre, "listo")

        foto("base")
        pagina.click(".pestanas [data-filtro=pagado]")
        foto("pagadas")
        pagina.click(".pestanas [data-filtro=todas]")
        pagina.fill(".buscar", factura[-6:])
        foto("busqueda")
        pagina.fill(".buscar", "")
        pagina.dispatch_event(".buscar", "input")
        pagina.locator("#tabla-cont tbody tr").first.locator("td.acciones .btn").nth(2).click()
        pagina.wait_for_function("() => { const i = document.getElementById('qr-img'); return i.complete && i.naturalWidth > 0; }", timeout=30000)
        foto("qr")
        pagina.evaluate("document.getElementById('dialogo-qr').close()")
        pagina.locator("#tabla-cont tbody tr").first.locator("td.acciones .btn.primario").click()
        pagina.wait_for_selector("#avisos .aviso", timeout=30000)
        foto("consultar")

        xml = ctx.request.get(f"{URL}/panel/factura/{factura}.xml").text()
        csv = ctx.request.get(f"{URL}/panel/ventas.csv").text().lstrip("\ufeff").splitlines()
        nav.close()
    datos["factura"] = factura
    datos["xml"] = xml_destacado(xml)
    datos["csv"] = [";".join(c if len(c) < 20 else c[:12] + "…" for c in l.split(";")) for l in csv[:5]]
    JSON.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(JSON, "·", len(datos["xml"]), "líneas de XML ·", len(datos["csv"]), "de CSV")


if __name__ == "__main__":
    main()
