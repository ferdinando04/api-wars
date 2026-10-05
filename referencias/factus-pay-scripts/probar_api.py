# -*- coding: utf-8 -*-
"""Prueba repetible de la API de Factus Pay (sandbox): autenticar, crear un recaudo, verlo, listarlo con filtros, provocar cada
error documentado y comprobar que las rutas no documentadas no existen. Mide el tiempo de cada llamada. Credenciales del
`.env` del proyecto (FACTUS_PAY_SANDBOX_URL / _EMAIL / _PASSWORD); nunca se imprimen.

Uso:  python scripts/factus-pay/probar_api.py [--guardar-qr ruta.png]
Ojo: /auth permite 5 intentos por minuto; este guion hace 2 (uno bueno, uno malo)."""
import base64, io, json, sys, time, urllib.request, urllib.error
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
env = dict(l.strip().split("=", 1) for l in io.open(RAIZ / ".env", encoding="utf-8") if "=" in l and not l.startswith("#"))
BASE = env["FACTUS_PAY_SANDBOX_URL"].strip().rstrip("/")
EMAIL = env["FACTUS_PAY_SANDBOX_EMAIL"].strip()
PW = env["FACTUS_PAY_SANDBOX_PASSWORD"].strip()
GUARDAR_QR = sys.argv[sys.argv.index("--guardar-qr") + 1] if "--guardar-qr" in sys.argv else None
filas = []


def api(metodo, path, cuerpo=None, token=None):
    """Devuelve (estado, json, segundos, cabeceras)."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    h = {"Accept": "application/json", "User-Agent": "factus-pay-prueba/1.0"}
    if cuerpo is not None:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=datos, headers=h, method=metodo)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cuerpo_r = r.read()
            return r.status, (json.loads(cuerpo_r) if cuerpo_r else None), time.time() - t0, dict(r.headers)
    except urllib.error.HTTPError as e:
        cuerpo_r = e.read()
        try:
            j = json.loads(cuerpo_r)
        except Exception:
            j = None
        return e.code, j, time.time() - t0, dict(e.headers)


def caso(nombre, esperado, metodo, path, cuerpo=None, token=None):
    st, j, seg, cab = api(metodo, path, cuerpo, token)
    msg = (j or {}).get("message") if isinstance(j, dict) else None
    ok = "OK " if st == esperado else "!! "
    filas.append((ok, nombre, esperado, st, round(seg, 2), (msg or "")[:70]))
    return st, j, cab


# 1. autenticación
st, j, cab = caso("POST /auth (credenciales buenas)", 200, "POST", "/auth", {"email": EMAIL, "password": PW})
token = (j or {}).get("token")
limite_auth = cab.get("X-RateLimit-Limit") or cab.get("x-ratelimit-limit")
caso("POST /auth (clave mala) → 401", 401, "POST", "/auth", {"email": EMAIL, "password": "incorrecta-" + str(int(time.time()))})
if not token:
    print("No hubo token; revisa el .env"); sys.exit(1)
print(f"token: {len(token)} caracteres · límite de /auth por minuto: {limite_auth}")

# 2. crear, ver, listar
ref = "PRUEBA-API-" + time.strftime("%Y%m%d-%H%M%S")
st, j, cab = caso("POST /v1/collections $10.000", 200, "POST", "/v1/collections", {"reference_code": ref, "amount": 10000}, token)
d = (j or {}).get("data") or {}
qr = d.get("qr")
print(f"recaudo {ref}: status={d.get('status')} · amount={d.get('amount')} · qr={'sí (' + str(len(qr)) + ' chars)' if qr else 'NO'}")
limite_v1 = cab.get("X-RateLimit-Limit") or cab.get("x-ratelimit-limit")
if qr and GUARDAR_QR:
    Path(GUARDAR_QR).write_bytes(base64.b64decode(qr.split(",", 1)[1])); print("QR guardado en", GUARDAR_QR)
caso("POST misma referencia → «ya existente»", 200, "POST", "/v1/collections", {"reference_code": ref, "amount": 10000}, token)
caso(f"GET /v1/collections/{{ref}}", 200, "GET", f"/v1/collections/{ref}", token=token)
st, j, _ = caso("GET /v1/collections (lista)", 200, "GET", "/v1/collections", token=token)
print(f"lista: {len((j or {}).get('data') or [])} en la primera página · meta={json.dumps((j or {}).get('meta'), ensure_ascii=False)[:120]}")
st, j, _ = caso("GET ?status=ready", 200, "GET", "/v1/collections?status=ready", token=token)
st, j, _ = caso("GET ?reference_code=<ref>", 200, "GET", f"/v1/collections?reference_code={ref}", token=token)
print(f"filtro por referencia devolvió: {[x.get('reference_code') for x in (j or {}).get('data') or []]}")

# 3. errores documentados
caso("POST amount 9.999 → 422", 422, "POST", "/v1/collections", {"reference_code": ref + "-a", "amount": 9999}, token)
caso("POST amount 12.000.001 → 422", 422, "POST", "/v1/collections", {"reference_code": ref + "-b", "amount": 12000001}, token)
caso("POST sin reference_code → 422", 422, "POST", "/v1/collections", {"amount": 10000}, token)
caso("POST reference_code de 101 chars → 422", 422, "POST", "/v1/collections", {"reference_code": "X" * 101, "amount": 10000}, token)
caso("GET ?status=otro → 422", 422, "GET", "/v1/collections?status=otro", token=token)
caso("GET con token falso → 401", 401, "GET", "/v1/collections", token="token-falso")
caso("GET referencia inexistente → 404", 404, "GET", "/v1/collections/NO-EXISTE-" + ref, token=token)

# 4. rutas que NO están documentadas (para saber si existen a escondidas)
for ruta in ("/v1/disbursements", "/v1/payouts", "/v1/webhooks", "/v1/balance", "/v1/me", f"/v1/collections/{ref}/cancel"):
    caso(f"GET {ruta} (no documentada) → 404", 404, "GET", ruta, token=token)

print(f"\nlímite de /v1 por minuto: {limite_v1}\n")
print(f"{'':3}{'caso':46} {'esp':>4} {'obt':>4} {'seg':>5}  mensaje")
for ok, nombre, esperado, st, seg, msg in filas:
    print(f"{ok}{nombre:46} {esperado:>4} {st:>4} {seg:>5}  {msg}")
fallos = [f for f in filas if f[0].startswith("!!")]
print(f"\n{len(filas) - len(fallos)}/{len(filas)} casos como se esperaba" + (f" · FALLAN: {[f[1] for f in fallos]}" if fallos else ""))
