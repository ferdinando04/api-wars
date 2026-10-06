"""Prepara el material visual del video pitch de Firebox en public/firebox/ del proyecto Remotion.

- Diapositivas de David (PDF → PNG 1920 px).
- Capturas reales del 05-oct recortadas: sin pestañas del navegador, sin lista de chats personales, sin apps de clientes.
- Las dos páginas del PDF real que recibió el cliente (factura + "Paga aquí").
- Fragmentos del código REAL (con su número de línea) y la salida real de las pruebas → src/firebox/codigo.json.

Uso: python video/preparar_material.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
REMOTION = Path(r"C:\Users\FERNANDO VEGA\Desktop\proyecto-video-ai")
PUBLICO = REMOTION / "public" / "firebox"
CAPTURAS = Path(r"C:\Users\FERNAN~1\AppData\Local\Temp\claude\c--Users-FERNANDO-VEGA-Desktop-Api-Wars"
                r"\fa27dac4-9c67-49e6-94e4-fa00b177f515\images")
PRESENTACION = Path(r"C:\Users\FERNANDO VEGA\Downloads\Firebox API WARS.pdf")
PDF_DEMO = RAIZ / "app" / "salida" / "Factura-SETP990023179.pdf"

# (archivo, nombre de salida, caja de recorte (x0, y0, x1, y1) sobre la captura de 1366×768)
RECORTES = [
    ("11.png", "meta_numero_no_verificado.png", (296, 150, 1340, 400)),   # Administrador de WhatsApp: número "No verificado"
    ("12.png", "meta_verificacion.png", (546, 285, 1300, 768)),          # panel del número: "Verificación obligatoria"
    ("19.png", "meta_app_firebox.png", (0, 145, 1366, 768)),             # panel de la app Firebox
    ("23.png", "meta_permisos_token.png", (276, 118, 1076, 520)),        # permisos del token (solo los 2 de WhatsApp)
    ("24.png", "terminal_registrado.png", (305, 580, 960, 720)),          # terminal: {'success': True} REGISTRADO
    ("30.png", "factus_pay_simulador.png", (284, 470, 1080, 740)),       # simulador con monto, llave y Payment ID
    ("31.png", "whatsapp_factura_recibida.png", (396, 40, 1366, 768)),   # chat con Firebox: texto, PDF y QR (sin lista de chats)
]


def diapositivas() -> None:
    doc = fitz.open(PRESENTACION)
    for i, pagina in enumerate(doc, start=1):
        pix = pagina.get_pixmap(matrix=fitz.Matrix(1920 / pagina.rect.width, 1920 / pagina.rect.width))
        pix.save(PUBLICO / f"diapositiva_{i:02d}.png")
    print(f"diapositivas: {doc.page_count}")


def capturas() -> None:
    for origen, destino, caja in RECORTES:
        Image.open(CAPTURAS / origen).convert("RGB").crop(caja).save(PUBLICO / destino)
    print(f"capturas: {len(RECORTES)}")


def pdf_demo() -> None:
    doc = fitz.open(PDF_DEMO)
    for i, nombre in enumerate(["pdf_factura.png", "pdf_paga_aqui.png"]):
        doc[i].get_pixmap(dpi=150).save(PUBLICO / nombre)
    print("PDF de la demo: 2 páginas")


def fragmento(ruta: str, desde_patron: str, hasta_patron: str | None = None, max_lineas: int = 18) -> dict:
    """Corta el código real entre dos patrones y conserva el número de línea del archivo."""
    lineas = (RAIZ / ruta).read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(lineas) if re.search(desde_patron, l))
    fin = ini + max_lineas
    if hasta_patron:
        fin = next((i for i in range(ini + 1, len(lineas)) if re.search(hasta_patron, lineas[i])), fin)
    trozo = lineas[ini:fin]
    while trozo and not trozo[-1].strip():
        trozo.pop()
    return {"archivo": ruta, "desde": ini + 1, "lineas": trozo}


def codigo() -> None:
    f = "app/firebox/facturacion/factus.py"
    p = "app/firebox/pagos/factus_pay.py"
    w = "app/firebox/canal/whatsapp.py"
    d = "app/firebox/dinero.py"
    datos = {
        "factus_token": fragmento(f, r"def _obtener_token", r"def _pedir"),
        "factus_rango": fragmento(f, r"def rango_factura_de_venta", r"def emitir_factura"),
        "factus_emitir": fragmento(f, r"def emitir_factura", r"def descargar_pdf"),
        "factus_pdf": fragmento(f, r"def descargar_pdf", r"^def cuerpo_factura"),
        "user_agent": fragmento("app/firebox/config.py", r"^USER_AGENT", None, 1),
        "pay_crear": fragmento(p, r"def crear_recaudo", r"def consultar"),
        "pay_consultar": fragmento(p, r"def consultar", None, 3),
        "vigilante": fragmento("app/demo_corte_vertical.py", r"limite = time.time", r"paso\(\"Se acabó"),
        "wa_subir": fragmento(w, r"def subir_medio", r"def enviar_texto"),
        "wa_enviar": fragmento(w, r"def _enviar", r"def subir_medio"),
        "wa_documento": fragmento(w, r"def enviar_documento", None, 3),
        "dinero_redondear": fragmento(d, r"^def redondear", r"^@dataclass"),
        "dinero_linea": fragmento(d, r"def iva\(self\)", r"^@dataclass"),
        "dinero_rango": fragmento(p, r"^def monto_permitido", r"^def _a_recaudo"),
        "demo_igualdad": fragmento("app/demo_corte_vertical.py", r"if factura.total != totales.total", None, 3),
        "test_bancario": fragmento("app/tests/test_dinero.py", r"def test_redondeo_bancario", r"^def test_cantidad"),
    }
    datos["evidencia"] = [l for l in (RAIZ / "docs/documentacion/evidencias/fase0/corrida-2026-10-05-1246.md")
                          .read_text(encoding="utf-8").splitlines() if l.startswith("[")]
    destino = REMOTION / "src" / "firebox" / "codigo.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"código real: {len(datos) - 1} fragmentos + evidencia ({len(datos['evidencia'])} líneas)")


def control_negativo() -> None:
    """Corre la prueba de verdad: rompe el redondeo, la ve en rojo y restaura. Guarda la salida real."""
    app = RAIZ / "app"
    archivo = app / "firebox" / "dinero.py"
    original = archivo.read_bytes()
    correr = lambda: subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=app,
                                    capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()
    try:
        sano = correr()[-1]
        archivo.write_bytes(original.replace(b"rounding=ROUND_HALF_EVEN)", b'rounding="ROUND_HALF_UP")'))
        roto = [l for l in correr() if l.startswith("FAILED") or "failed" in l]
    finally:
        archivo.write_bytes(original)
    restaurado = correr()[-1]
    datos = json.loads((REMOTION / "src" / "firebox" / "codigo.json").read_text(encoding="utf-8"))
    datos["control_negativo"] = {"sano": sano, "roto": roto, "restaurado": restaurado}
    (REMOTION / "src" / "firebox" / "codigo.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("control negativo:", sano, "|", roto, "|", restaurado)


if __name__ == "__main__":
    PUBLICO.mkdir(parents=True, exist_ok=True)
    diapositivas()
    capturas()
    pdf_demo()
    codigo()
    control_negativo()
