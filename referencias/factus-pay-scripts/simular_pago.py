# -*- coding: utf-8 -*-
"""Prueba de punta a punta de Factus Pay sandbox: crea 2 recaudos por la API, decodifica sus QR, los «escanea» en el simulador (llamando
al mismo método de Livewire que usa la cámara: handleScannedQr), simula un pago exitoso y uno fallido, y verifica por la API los estados
finales. Credenciales del .env de Retos_Factus; nada de secretos en la salida."""
import base64, io, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode
from playwright.sync_api import sync_playwright

ENV = Path("C:/Users/FERNANDO VEGA/Desktop/Retos_Factus/.env")
env = dict(l.strip().split("=", 1) for l in io.open(ENV, encoding="utf-8") if "=" in l and not l.startswith("#"))
BASE = env["FACTUS_PAY_SANDBOX_URL"].strip(); EMAIL = env["FACTUS_PAY_SANDBOX_EMAIL"].strip(); PW = env["FACTUS_PAY_SANDBOX_PASSWORD"].strip()
AQUI = Path(__file__).resolve().parent


def api(metodo, path, cuerpo=None, token=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    h = {"Accept": "application/json", "User-Agent": "vexon-prueba-factus-pay/1.0"}
    if cuerpo is not None: h["Content-Type"] = "application/json"
    if token: h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=datos, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, None


def qr_texto(data_uri):
    im = Image.open(io.BytesIO(base64.b64decode(data_uri.split(",", 1)[1]))).convert("RGB")
    r = decode(im) or decode(im.resize((im.width * 3, im.height * 3)))
    return r[0].data.decode("utf-8") if r else None


st, r = api("POST", "/auth", {"email": EMAIL, "password": PW}); token = r["token"]
sello = time.strftime("%Y%m%d-%H%M%S")
casos = {"exito": ("VEXON-SIM-OK-" + sello, ""), "fallo": ("VEXON-SIM-FALLA-" + sello, "tx_insufficient_funds")}
recaudos = {}
for nombre, (ref, error) in casos.items():
    st, r = api("POST", "/v1/collections", {"reference_code": ref, "amount": 15000}, token)
    d = r["data"]; texto = qr_texto(d["qr"]) if d.get("qr") else None
    recaudos[nombre] = {"ref": ref, "error": error, "qr": texto, "estado_inicial": d["status"]}
    print(f"creado {nombre}: {ref} · estado {d['status']} · QR: {texto}")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1366, "height": 900}, locale="es-CO"); page = ctx.new_page()
    page.goto(BASE + "/login", wait_until="networkidle"); time.sleep(1)
    page.fill("input[name=email]", EMAIL); page.fill("input[name=password]", PW); page.click("button[type=submit]")
    page.wait_for_url(lambda u: "/login" not in u, timeout=20000); page.wait_for_load_state("networkidle")
    for nombre, rc in recaudos.items():
        page.goto(BASE + "/simulator", wait_until="networkidle"); time.sleep(1.5)
        # lo mismo que hace la cámara al leer el QR: $wire.call("handleScannedQr", texto)
        page.evaluate("t => window.Livewire.all()[0].$wire.call('handleScannedQr', t)", rc["qr"]); time.sleep(2.5)
        antes = re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText"))
        print(f"== simulador tras escanear ({nombre}):", antes.replace("\n", " / ")[:400])
        page.screenshot(path=str(AQUI / f"sim-{nombre}-1-escaneado.png"), full_page=True)
        if rc["error"]:
            page.select_option("select[name=errorType]", rc["error"]); time.sleep(0.8)
        t0 = time.time()
        page.click("text=Simular pago"); time.sleep(3)
        despues = re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText"))
        print(f"== resultado ({nombre}, {time.time() - t0:.1f}s):", despues.replace("\n", " / ")[:600])
        page.screenshot(path=str(AQUI / f"sim-{nombre}-2-resultado.png"), full_page=True)
        rc["resultado_pantalla"] = despues[:600]
    b.close()

print("== estados por la API después de simular")
for nombre, rc in recaudos.items():
    for i in range(6):
        st, r = api("GET", f"/v1/collections/{rc['ref']}", token=token); estado = (r or {}).get("data", {}).get("status")
        if estado != rc["estado_inicial"]: break
        time.sleep(2)
    print(f"  {nombre}: {rc['ref']} → {estado} (antes {rc['estado_inicial']}; {i} esperas de 2 s)")
    rc["estado_final"] = estado
st, r = api("GET", "/v1/collections?status=paid", token=token); print("  listado status=paid:", [(x['reference_code'], x['status']) for x in r['data']])
st, r = api("GET", "/v1/collections", token=token); print("  todos:", [(x['reference_code'][-20:], x['status']) for x in r['data']])
json.dump(recaudos, io.open(AQUI / "simulacion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
