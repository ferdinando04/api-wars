# -*- coding: utf-8 -*-
"""Comprueba que las credenciales del .env sirven HOY: Factus (v1 y, si hay, v2) y Factus Pay.
Solo pide tokens y hace lecturas (no crea facturas ni recaudos). Nunca imprime secretos.

Uso:  python scripts/verificar_credenciales.py
Sale con código 1 si alguna credencial configurada falla.
Ojo: Factus Pay permite 5 llamadas a /auth por minuto."""
import json, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
env = {}
for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linea and not linea.lstrip().startswith("#"):
        k, v = linea.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")


def llamar(metodo, url, datos=None, cabeceras=None, como_form=False):
    """Devuelve (estado, json o None)."""
    h = {"Accept": "application/json", "User-Agent": "api-wars-verificar/1.0", **(cabeceras or {})}
    cuerpo = None
    if datos is not None:
        if como_form:
            cuerpo = urllib.parse.urlencode(datos).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            cuerpo = json.dumps(datos).encode()
            h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=cuerpo, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None
    except urllib.error.URLError as e:
        return 0, {"message": str(e.reason)}


fallos = []


def informe(ok, texto):
    print(("OK    " if ok else "FALLA ") + texto)
    if not ok:
        fallos.append(texto)


def factus(prefijo, etiqueta):
    cid = env.get(f"{prefijo}CLIENT_ID")
    if not cid:
        print(f"--    {etiqueta}: sin credenciales en .env (se omite)")
        return
    base = env.get("FACTUS_BASE_URL", "https://api-sandbox.factus.com.co").rstrip("/")
    st, j = llamar("POST", base + "/oauth/token", {
        "grant_type": "password", "client_id": cid,
        "client_secret": env.get(f"{prefijo}CLIENT_SECRET", ""),
        "username": env.get(f"{prefijo}USERNAME", ""), "password": env.get(f"{prefijo}PASSWORD", ""),
    }, como_form=True)
    token = (j or {}).get("access_token")
    informe(st == 200 and bool(token), f"{etiqueta}: token OAuth (HTTP {st})")
    if not token:
        return
    for ver in ("v1", "v2"):
        st, j = llamar("GET", f"{base}/{ver}/numbering-ranges", cabeceras={"Authorization": "Bearer " + token})
        msg = (j or {}).get("message", "") if isinstance(j, dict) else ""
        print(f"      {etiqueta}: GET /{ver}/numbering-ranges -> HTTP {st} {msg[:60]}")


factus("FACTUS_", "Factus v2 (principal)")
factus("FACTUS_V1_", "Factus v1 (respaldo)")

pay = env.get("FACTUS_PAY_BASE_URL", "").rstrip("/")


def factus_pay(prefijo, etiqueta):
    if not env.get(f"{prefijo}EMAIL"):
        print(f"--    {etiqueta}: sin credenciales en .env (se omite)")
        return
    st, j = llamar("POST", pay + "/auth", {"email": env[f"{prefijo}EMAIL"], "password": env.get(f"{prefijo}PASSWORD", "")})
    token = (j or {}).get("token")
    informe(st == 200 and bool(token), f"{etiqueta}: token /auth (HTTP {st})")
    if token:
        st, j = llamar("GET", pay + "/v1/collections", cabeceras={"Authorization": "Bearer " + token})
        informe(st == 200, f"{etiqueta}: GET /v1/collections (HTTP {st})")


if pay:
    factus_pay("FACTUS_PAY_", "Factus Pay equipo")
    factus_pay("FACTUS_PAY_PERSONAL_", "Factus Pay personal")
else:
    print("--    Factus Pay: sin FACTUS_PAY_BASE_URL en .env (se omite)")

print("\nRESULTADO:", "todo bien" if not fallos else f"{len(fallos)} falla(s)")
sys.exit(1 if fallos else 0)
