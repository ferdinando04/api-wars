# -*- coding: utf-8 -*-
"""Genera docs/documentacion/Firebox_Documentacion_Tecnica.pdf desde los Markdown del repo.

Uso (con el Python que tiene Playwright):
  "C:/Users/FERNANDO VEGA/Desktop/Didier_Validacion_Pagos/sistema/services/api/.venv/Scripts/python.exe" docs/documentacion/generar_pdf.py
Tolera archivos faltantes: se puede volver a correr cuando existan.
"""
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "documentacion"
BUILD = DOC / "_pdf_build"
PDF = DOC / "Firebox_Documentacion_Tecnica.pdf"
INCLUIDOS, FALTANTES = [], []


def rel(p):
    return p.relative_to(RAIZ).as_posix()


def leer(ruta):
    p = RAIZ / ruta
    if p.is_file():
        INCLUIDOS.append(ruta)
        return p.read_text(encoding="utf-8")
    FALTANTES.append(ruta)
    return None


def md_a_html(texto, prefijo):
    def slug(valor, sep):
        s = re.sub(r"[^\w\s-]", "", valor.lower(), flags=re.UNICODE)
        return f"{prefijo}-" + re.sub(r"[\s_-]+", sep, s).strip(sep)

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"slugify": slug}},
    )
    out = md.convert(texto)
    out = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m: '<pre class="mermaid">' + m.group(1) + "</pre>",
        out, flags=re.S)
    # ids como RF-04 / CU-01 / FR-013 no deben partirse en el guion
    out = re.sub(r"<td>([A-Z]{1,4}-\d[\w.]*)</td>", lambda m: '<td class="id">' + m.group(1) + "</td>", out)
    return out


def seccion_md(ruta, prefijo, solo_seccion=None):
    t = leer(ruta)
    if t is None:
        return None
    if solo_seccion:
        m = re.search(r"^## " + re.escape(solo_seccion) + r".*?(?=^## |\Z)", t, re.S | re.M)
        t = m.group(0) if m else t
    return md_a_html(t, prefijo)


def titulo_de(h, defecto):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else defecto


def armar():
    items = []
    n = [0]

    def cap(ruta, defecto):
        n[0] += 1
        h = seccion_md(ruta, "c%d" % n[0])
        if h is None:
            n[0] -= 1
            return
        if "<h1" not in h:
            h = "<h1>%s</h1>" % defecto + h
        items.append(("cap", "cap%d" % n[0], titulo_de(h, defecto), h))

    partes = []
    reto = seccion_md("RETO.md", "ra")
    ind = seccion_md("docs/documentacion/00_INDICE.md", "rb", solo_seccion="2. ")
    if reto:
        partes.append(re.sub(r"<h1[^>]*>.*?</h1>", "", reto, count=1, flags=re.S))
    if ind:
        partes.append("<h2>Qué hace Firebox</h2>" + re.sub(r"<h2[^>]*>.*?</h2>", "", ind, count=1, flags=re.S))
    if partes:
        items.append(("cap", "cap-intro", "Introducción y el reto",
                      "<h1>Introducción y el reto</h1>" + "".join(partes)))

    items.append(("parte", "PARTE I", "SDD · Spec-Driven Development",
                  "Método de trabajo: nada se programa sin especificación aprobada. "
                  "Orden: constitución, especificación, plan, modelo de datos, contratos, tareas y guía de arranque."))
    cap(".specify/memory/constitution.md", "Constitución del proyecto")
    cap("specs/001-tienda-whatsapp/spec.md", "Especificación")
    cap("specs/001-tienda-whatsapp/plan.md", "Plan de implementación")
    cap("specs/001-tienda-whatsapp/data-model.md", "Modelo de datos")
    for c in sorted((RAIZ / "specs/001-tienda-whatsapp/contracts").glob("*.md")):
        cap(rel(c), "Contrato " + c.stem)
    cap("specs/001-tienda-whatsapp/tasks.md", "Tareas")
    cap("specs/001-tienda-whatsapp/quickstart.md", "Guía de arranque")

    items.append(("parte", "PARTE II", "Análisis y diseño",
                  "Documentación formal derivada de la especificación: requisitos, casos de uso, historias e integraciones."))
    for p in sorted(DOC.glob("*.md")):
        if re.match(r"^[01]\d_", p.name) and not p.name.startswith("00_"):
            cap("docs/documentacion/" + p.name, p.stem)

    items.append(("parte", "PARTE III", "Pruebas y evidencias",
                  "Evidencias medidas de cada tarea: corridas reales, registros y capturas."))
    marca = len(items)
    ev = DOC / "evidencias"
    for p in sorted(ev.rglob("*.md")):
        n[0] += 1
        t = leer(rel(p))
        h = md_a_html(t, "c%d" % n[0])
        if "<h1" not in h:
            h = "<h1>%s</h1>" % p.stem + h
        items.append(("cap", "cap%d" % n[0], titulo_de(h, p.stem), h))
    # Un capítulo por carpeta de capturas (no uno por imagen), con su explicación y una leyenda por figura.
    grupos = {
        "panel": ("Evidencia gráfica: panel del vendedor", "Vista general del panel en vivo con ventas reales del sandbox."),
        "recorrido": ("Evidencia gráfica: recorrido del panel por estados",
                      "Capturas reales de cada estado que muestra el video (video/capturar_recorrido_panel.py)."),
        "responsive": ("Evidencia gráfica: panel responsive en 6 tamaños",
                       "Medido con scripts/verificar_panel_responsive.py (Playwright): antes del arreglo 4/6 (768 y 390 px se "
                       "salían de la pantalla); después 6/6 sin desborde. En tableta y celular cada factura pasa a tarjeta."),
    }
    leyendas = {"base": "Estado normal: métricas, tabla y columna de conexiones", "pagadas": "Pestaña «Pagadas» activa",
                "busqueda": "Buscador con parte del número de factura", "qr": "Botón QR: el código de pago de Factus Pay",
                "consultar": "Botón Consultar: estado del cobro en Factus Pay con su latencia",
                "panel_vendedor": "Panel del vendedor"}
    por_carpeta: dict = {}
    for p in ev.rglob("*.png"):
        por_carpeta.setdefault(p.parent, []).append(p)
    for carpeta in sorted(por_carpeta):
        titulo, intro = grupos.get(carpeta.name, ("Evidencia gráfica: " + carpeta.name, ""))
        fotos = sorted(por_carpeta[carpeta], key=lambda f: (-int(re.search(r"(\d+)$", f.stem).group(1))
                                                             if re.search(r"(\d+)$", f.stem) else 0, f.stem))
        n[0] += 1
        h = "<h1>%s</h1>" % titulo + ("<p>%s</p>" % intro if intro else "")
        for f in fotos:
            INCLUIDOS.append(rel(f))
            m = re.match(r"([a-z]+)-(\d+)$", f.stem)
            nombre = "%s · %s px de ancho" % (m.group(1).capitalize(), m.group(2)) if m else leyendas.get(f.stem, f.stem.replace("_", " "))
            h += ('<figure><img src="%s" alt="%s">' % (f.as_uri(), nombre)
                  + "<figcaption>Figura. %s (archivo %s).</figcaption></figure>" % (nombre, rel(f)))
        items.append(("cap", "cap%d" % n[0], titulo, h))
    if len(items) == marca:
        items.pop()

    caps = [i for i in items if i[0] == "cap"]
    lista = "".join("<li>%s</li>" % i[2] for i in caps)
    concl = (
        "<h1>Conclusiones</h1>"
        "<p>Este documento reúne, en un solo volumen, la documentación técnica de Firebox: una tienda "
        "dentro de WhatsApp que emite la factura electrónica con Factus API v2 y la cobra con un QR de "
        "Factus Pay, administrada desde un panel web. Su contenido es el de los archivos fuente del "
        "repositorio; no se añadieron cifras ni afirmaciones nuevas.</p>"
        "<ul>"
        "<li>El trabajo se organizó con Spec-Driven Development: constitución, especificación, plan, "
        "modelo de datos, contratos y tareas preceden al código (Parte I).</li>"
        "<li>El análisis y diseño se documentó con requisitos, casos de uso, historias de usuario e "
        "integraciones externas medidas (Parte II).</li>"
        "<li>Las pruebas quedan respaldadas por evidencias fechadas en el repositorio (Parte III).</li>"
        "<li>Las facturas del sandbox de Factus no tienen validez fiscal ante la DIAN, y Factus Pay "
        "se usó en su entorno de pruebas.</li></ul>"
        "<h2>Capítulos incluidos en esta edición</h2><ol>%s</ol>" % lista)
    refs = (
        "<h1>Referencias</h1><ol>"
        "<li>Factus. Documentación de la API de facturación electrónica. https://developers.factus.com.co</li>"
        "<li>Factus Pay. Documentación para desarrolladores. https://pay-developers.factus.com.co</li>"
        "<li>Meta. WhatsApp Cloud API. https://developers.facebook.com/docs/whatsapp/cloud-api</li>"
        "<li>GitHub. Spec Kit (Spec-Driven Development). https://github.com/github/spec-kit</li>"
        "<li>IEEE. IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications.</li>"
        "<li>FastAPI. Documentación oficial. https://fastapi.tiangolo.com</li>"
        "<li>HTMX. Documentación oficial. https://htmx.org</li>"
        "<li>Python Software Foundation. Módulo <code>decimal</code> de la biblioteca estándar. "
        "https://docs.python.org/3/library/decimal.html</li></ol>")
    items.append(("cap", "cap-concl", "Conclusiones", concl))
    items.append(("cap", "cap-refs", "Referencias", refs))
    return items


CSS = """
@page { size: Letter; margin: 0.85in 0.8in 0.9in 0.8in; }
@page :first { margin: 0; }
:root { --crema:#F5F0E8; --verde:#0F3D2E; --coral:#E8613C; --tinta:#13241D; --gris:#5E6B64; --linea:#E3DACD; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Instrument Sans', 'Segoe UI', sans-serif; color: var(--tinta); font-size: 10.5pt; line-height: 1.55; margin:0; }
h1,h2,h3,h4 { font-family: 'Bricolage Grotesque', 'Segoe UI', sans-serif; color: var(--verde); line-height:1.2; break-after: avoid; }
h1 { font-size: 24pt; margin: 0 0 14pt; padding-bottom: 8pt; border-bottom: 3px solid var(--coral); }
h2 { font-size: 16pt; margin: 20pt 0 8pt; }
h3 { font-size: 12.5pt; margin: 14pt 0 6pt; }
h4 { font-size: 11pt; margin: 10pt 0 4pt; }
p { margin: 0 0 8pt; orphans:3; widows:3; }
a { color: var(--coral); text-decoration: none; }
ul, ol { padding-left: 20pt; margin: 0 0 8pt; }
li { margin-bottom: 2pt; }
blockquote { margin: 8pt 0; padding: 6pt 12pt; border-left: 4px solid var(--coral); background: #FBF8F2; color: var(--gris); }
hr { border: 0; border-top: 1px solid var(--linea); margin: 14pt 0; }
code { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 8.8pt; background: #F1EBDF; padding: 1px 4px; border-radius: 3px; word-break: break-word; }
pre { background: #0D1915; color: #E6EFE9; padding: 10pt 12pt; border-radius: 6px; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: anywhere; font-size: 8.3pt; line-height:1.45; }
pre code { background: transparent; color: inherit; padding: 0; font-size: inherit; }
pre.mermaid { background: #FFFFFF; color: var(--tinta); border: 1px solid var(--linea); text-align: center; white-space: normal; break-inside: avoid; }
pre.mermaid svg { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9pt; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: var(--verde); color: #fff; text-align: left; padding: 5pt 7pt; border: 1px solid var(--verde); font-weight: 600; }
td { padding: 4pt 7pt; border: 1px solid var(--linea); vertical-align: top; word-break: break-word; }
td.id { white-space: nowrap; }
tbody tr:nth-child(even) td { background: #FAF6EE; }
img { max-width: 100%; height: auto; }
figure { margin: 10pt 0; text-align: center; break-inside: avoid; }
figure img { border: 1px solid var(--linea); border-radius: 6px; }
figcaption { font-size: 9pt; color: var(--gris); margin-top: 4pt; }
.cap { break-before: page; }
.parte { break-before: page; min-height: 8.6in; display:flex; flex-direction:column; justify-content:center; }
.parte .et { font-family:'Bricolage Grotesque',sans-serif; color: var(--coral); font-size: 16pt; font-weight:700; letter-spacing: 3px; }
.parte h1 { font-size: 36pt; border: 0; margin: 6pt 0 14pt; }
.parte p { font-size: 13pt; color: var(--gris); max-width: 5.5in; }
.parte .barra { width: 90px; height: 5px; background: var(--coral); margin-bottom: 14pt; }
.portada { background: var(--crema); width: 8.5in; height: 10.98in; padding: 1.1in 0.95in 0.8in 1.2in; position: relative; overflow: hidden; break-after: page; }
.portada .franja { position:absolute; left:0; top:0; bottom:0; width: 0.35in; background: var(--verde); }
.portada .marca { font-family:'Bricolage Grotesque',sans-serif; color: var(--coral); letter-spacing: 4px; font-weight:700; font-size: 11pt; }
.portada h1 { font-size: 78pt; border: 0; margin: 1.3in 0 6pt; color: var(--verde); line-height:1; padding:0; }
.portada .barra { width: 120px; height: 7px; background: var(--coral); margin: 8pt 0 18pt; }
.portada .sub { font-size: 16pt; color: var(--tinta); max-width: 5.6in; line-height:1.35; font-family:'Bricolage Grotesque',sans-serif; }
.portada .evento { margin-top: 1.1in; font-size: 11pt; color: var(--gris); max-width: 5.6in; }
.portada .equipo { margin-top: 14pt; font-size: 11pt; color: var(--tinta); max-width: 5.6in; }
.portada .pie { position:absolute; left:1.2in; bottom:0.8in; font-size: 10.5pt; color: var(--gris); line-height:1.7; }
.portada .pie b { color: var(--verde); }
.toc { break-before: page; }
.toc ol { list-style: none; padding: 0; }
.toc li { padding: 5pt 0; border-bottom: 1px dotted var(--linea); font-size: 11pt; }
.toc li.p { margin-top: 12pt; border-bottom: 2px solid var(--verde); font-family:'Bricolage Grotesque',sans-serif; font-weight:700; letter-spacing:1px; }
.toc li.p a { color: var(--verde); }
.toc li.c { padding-left: 14pt; }
.toc a { color: var(--tinta); }
.toc .n { color: var(--coral); font-weight:700; margin-right: 8pt; }
"""


def construir_html(items):
    toc, cuerpo, k = [], [], 0
    for it in items:
        if it[0] == "parte":
            pid = "p-" + it[1].replace(" ", "").lower()
            toc.append('<li class="p"><a href="#%s">%s · %s</a></li>' % (pid, it[1], it[2]))
            cuerpo.append('<section class="parte" id="%s"><div class="et">%s</div><h1>%s</h1>'
                          '<div class="barra"></div><p>%s</p></section>' % (pid, it[1], it[2], it[3]))
        else:
            k += 1
            toc.append('<li class="c"><span class="n">%d.</span><a href="#%s">%s</a></li>' % (k, it[1], it[2]))
            cuerpo.append('<section class="cap" id="%s">%s</section>' % (it[1], it[3]))
    portada = (
        '<section class="portada"><div class="franja"></div>'
        '<div class="marca">API WARS 2026</div><h1>Firebox</h1><div class="barra"></div>'
        '<div class="sub">Documentación técnica · Tienda en WhatsApp con factura electrónica (Factus v2) '
        'y cobro QR (Factus Pay)</div>'
        '<div class="evento">API WARS 2026 · Universidad Distrital Francisco José de Caldas, Facultad '
        'Tecnológica · Semillero Pegasus · IEEE · Factus</div>'
        '<div class="equipo"><b>Equipo Firebox</b><br>Fernando Vega Benavides (líder técnico)<br>'
        'Juan David Vargas Aparicio<br>Dylan Gerhard Arce Triviño</div>'
        '<div class="pie"><b>Octubre de 2026</b><br>Repositorio: github.com/ferdinando04/api-wars<br>'
        'Versión 1.0</div></section>')
    toc_html = '<section class="toc"><h1>Tabla de contenido</h1><ol>%s</ol></section>' % "".join(toc)
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<title>Firebox · Documentación técnica</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&'
        'family=Instrument+Sans:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" '
        'rel="stylesheet"><style>' + CSS + '</style>'
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>'
        '</head><body>' + portada + toc_html + "".join(cuerpo) + '</body></html>')


MERMAID_JS = """async () => {
  if (!window.mermaid) return 'sin-mermaid';
  mermaid.initialize({startOnLoad:false, theme:'neutral', securityLevel:'loose'});
  await mermaid.run({querySelector:'pre.mermaid', suppressErrors:true});
  const todos = [...document.querySelectorAll('pre.mermaid')];
  return todos.filter(e => e.querySelector('svg')).length + '/' + todos.length;
}"""


def imprimir(ruta_html):
    from playwright.sync_api import sync_playwright
    pie = ('<div style="width:100%;font-family:Segoe UI,sans-serif;font-size:8px;color:#5E6B64;'
           'padding:0 0.8in;display:flex;justify-content:space-between;">'
           '<span>Firebox · Documentación técnica</span>'
           '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
    with sync_playwright() as p:
        nav = p.chromium.launch()
        try:
            pg = nav.new_page()
            pg.goto(ruta_html.as_uri(), wait_until="networkidle", timeout=90000)
            pg.evaluate("document.fonts.ready")
            if pg.evaluate("document.querySelectorAll('pre.mermaid').length"):
                print("Mermaid renderizados:", pg.evaluate(MERMAID_JS))
            pg.wait_for_timeout(500)
            pg.pdf(path=str(PDF), format="Letter", print_background=True,
                   prefer_css_page_size=True, display_header_footer=True,
                   header_template="<span></span>", footer_template=pie,
                   margin={"top": "0.85in", "bottom": "0.9in", "left": "0.8in", "right": "0.8in"})
        finally:
            nav.close()


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    items = armar()
    ruta = BUILD / "firebox_doc.html"
    ruta.write_text(construir_html(items), encoding="utf-8")
    imprimir(ruta)
    print("Incluidos:", *INCLUIDOS, sep="\n  ")
    print("Faltantes:", *(FALTANTES or ["(ninguno)"]), sep="\n  ")
    print("PDF:", PDF, "%.0f KB" % (PDF.stat().st_size / 1024))


if __name__ == "__main__":
    main()
