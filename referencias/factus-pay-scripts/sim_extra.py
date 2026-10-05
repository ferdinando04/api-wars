# -*- coding: utf-8 -*-
"""Pruebas extra del sandbox de Factus Pay: (1) los otros dos escenarios de fallo del simulador (error de cuenta, timeout);
(2) vencimiento de los QR (columna «Expiración» del panel) para saber cuánto dura un cobro; (3) ¿un recaudo pagado se puede volver a
crear? (4) tiempos de respuesta de la API."""
import base64, io, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode
from playwright.sync_api import sync_playwright

ENV = Path("C:/Users/FERNANDO VEGA/Desktop/Retos_Factus/.env")
env = dict(l.strip().split("=", 1) for l in io.open(ENV, encoding="utf-8") if "=" in l and not l.startswith("#"))
BASE = env["FACTUS_PAY_SANDBOX_URL"].strip(); EMAIL = env["FACTUS_PAY_SANDBOX_EMAIL"].strip(); PW = env["FACTUS_PAY_SANDBOX_PASSWORD"].strip()
AQUI = Path(__file__).resolve().parent
tiempos = []


def api(metodo, path, cuerpo=None, token=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    h = {"Accept": "application/json", "User-Agent": "vexon-prueba-factus-pay/1.0"}
    if cuerpo is not None: h["Content-Type"] = "application/json"
    if token: h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=datos, headers=h, method=metodo); t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            tiempos.append((metodo + " " + path.split("?")[0][:22], round(time.time() - t0, 2))); return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        tiempos.append((metodo + " " + path.split("?")[0][:22], round(time.time() - t0, 2)))
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, None


def qr_texto(data_uri):
    im = Image.open(io.BytesIO(base64.b64decode(data_uri.split(",", 1)[1]))).convert("RGB")
    r = decode(im) or decode(im.resize((im.width * 3, im.height * 3))); return r[0].data.decode("utf-8") if r else None


st, r = api("POST", "/auth", {"email": EMAIL, "password": PW}); token = r["token"]
sello = time.strftime("%Y%m%d-%H%M%S")
casos = {"cuenta": ("VEXON-SIM-CUENTA-" + sello, "tx_account_error"), "timeout": ("VEXON-SIM-TIMEOUT-" + sello, "tx_timeout")}
rec = {}
for n, (ref, err) in casos.items():
    st, r = api("POST", "/v1/collections", {"reference_code": ref, "amount": 20000}, token); d = r["data"]
    rec[n] = {"ref": ref, "error": err, "qr": qr_texto(d["qr"]), "antes": d["status"]}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1366, "height": 900}, locale="es-CO"); page = ctx.new_page()
    page.goto(BASE + "/login", wait_until="networkidle"); time.sleep(1)
    page.fill("input[name=email]", EMAIL); page.fill("input[name=password]", PW); page.click("button[type=submit]")
    page.wait_for_url(lambda u: "/login" not in u, timeout=20000); page.wait_for_load_state("networkidle")
    for n, rc in rec.items():
        page.goto(BASE + "/simulator", wait_until="networkidle"); time.sleep(1.5)
        page.evaluate("t => window.Livewire.all()[0].$wire.call('handleScannedQr', t)", rc["qr"]); time.sleep(2.5)
        page.select_option("select[name=errorType]", rc["error"]); time.sleep(0.8)
        page.click("text=Simular pago"); time.sleep(3)
        txt = re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText"))
        rc["pantalla"] = txt.split("Limpiar")[-1].strip()[:200]
        print(f"== {n} ({rc['error']}): {rc['pantalla']}")
    # vencimiento de los QR: lista de recaudos → cada detalle → /qrcodes/{id}
    page.goto(BASE + "/collections", wait_until="networkidle"); time.sleep(1.5)
    enlaces = sorted(set(page.evaluate("() => [...document.querySelectorAll('a[href*=\"/collections/\"]')].map(a => a.href)")))
    print("== vencimiento de los QR (creación → expiración), según el panel")
    for h in enlaces:
        cid = h.rstrip("/").split("/")[-1]
        page.goto(BASE + f"/qrcodes/{cid}", wait_until="networkidle"); time.sleep(1)
        t = re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText"))
        m = re.search(r"\$ ([\d.,]+)\s+COP\s+([\d\-]+ [\d:]+)\s+(\w+)", t)
        page.goto(h, wait_until="networkidle"); time.sleep(0.8)
        t2 = re.sub(r"\n\s*\n+", "\n", page.evaluate("() => document.body.innerText"))
        m2 = re.search(r"ID Externo\n([^\n]+)", t2); f = re.search(r"Fecha\n([^\n]+)", t2); e = re.search(r"Estado\n([^\n]+)", t2)
        print(f"   {(m2.group(1) if m2 else cid)[-24:]:24s} creado {f.group(1) if f else '?'} · QR expira {m.group(2) if m else '?'} ({m.group(3) if m else '?'}) · estado {e.group(1) if e else '?'}")
    b.close()

print("== estados por la API tras los fallos")
for n, rc in rec.items():
    st, r = api("GET", f"/v1/collections/{rc['ref']}", token=token); print(f"   {n}: {(r or {}).get('data', {}).get('status')}")
st, r = api("GET", "/v1/collections?status=paid", token=token); pagado = (r["data"] or [{}])[0].get("reference_code")
if pagado:
    st, r = api("POST", "/v1/collections", {"reference_code": pagado, "amount": 15000}, token)
    print(f"== volver a crear el recaudo ya pagado {pagado[-20:]}: {st} · status={r['data']['status']} · mensaje «{r.get('message')}» · qr {'sí' if r['data'].get('qr') else 'no'}")
    st, r = api("POST", "/v1/collections", {"reference_code": pagado, "amount": 99000}, token)
    print(f"   con OTRO monto: {st} · status={r['data']['status']} · amount={r['data']['amount']} (¿ignoró el monto nuevo?)")
print("== tiempos de respuesta:", tiempos)
