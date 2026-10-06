"""Corrige dos errores de digitación de la presentación de David en las imágenes que usa el video (06-oct-2026).

- Diapositiva 1: «FACTUS PAY • BRE-E» → «BRE-B». Se copia la «B» de «BRE» sobre la «E» final (misma tipografía, pixel a pixel).
- Diapositiva 8: «Firebase: de elegir a pagar…» → «Firebox: …». La línea no tiene una «x» que copiar, así que se reescribe la
  línea completa con Instrument Sans 700 a 36 px (calibrada: 1.014 px de ancho contra 1.016 del original) y se toma una captura.

Correr DESPUÉS de preparar_material.py (que vuelve a generar las diapositivas desde el PDF). Es idempotente.
Uso:  <python con playwright> video/corregir_diapositivas.py
"""
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

DIAPOS = Path(r"C:\Users\FERNANDO VEGA\Desktop\proyecto-video-ai\public\firebox")


def corregir_1() -> None:
    ruta = DIAPOS / "diapositiva_01.png"
    im = Image.open(ruta).convert("RGB")
    fondo = (245, 239, 230)                      # interior del chip, medido
    letra_b = im.crop((862, 872, 883, 906))      # la «B» de «BRE»
    for x in range(936, 958):
        for y in range(872, 906):
            im.putpixel((x, y), fondo)           # borra la «E» final
    im.paste(letra_b, (936, 872))
    im.save(ruta)


def corregir_8() -> None:
    ruta = DIAPOS / "diapositiva_08.png"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(ruta, tmp / "original.png")
        (tmp / "d8.html").write_text(
            '<html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@700'
            '&display=block" rel="stylesheet"><style>body{margin:0} #t{position:absolute;left:85px;top:963px;font-family:'
            "'Instrument Sans';font-weight:700;font-size:36px;line-height:1;white-space:nowrap;color:rgb(15,42,40)} "
            '#t b{color:rgb(236,100,68)}</style></head><body><div style="position:relative;width:1920px;height:1080px">'
            '<img src="original.png" style="position:absolute;left:0;top:0;width:1920px;height:1080px">'
            '<div style="position:absolute;left:75px;top:956px;width:1045px;height:56px;background:rgb(244,241,234)"></div>'
            '<div id="t"><b>Firebox:</b> de elegir a pagar, con factura en regla. <b>Vea la demo.</b></div></div></body></html>',
            encoding="utf-8")
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pg = nav.new_page(viewport={"width": 1920, "height": 1080})
            pg.goto((tmp / "d8.html").as_uri())
            pg.wait_for_function("document.fonts.ready.then(() => document.images[0].complete)")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(ruta))
            nav.close()


if __name__ == "__main__":
    corregir_1()
    corregir_8()
    print("diapositivas 1 y 8 corregidas en", DIAPOS)
