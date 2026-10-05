# -*- coding: utf-8 -*-
"""Registra el número de WhatsApp de Firebox en la Cloud API (paso que exige un PIN de 6 dígitos).

El PIN lo escribe la persona en la terminal: no se muestra, no se guarda en ningún archivo y no se imprime.
Guárdalo en tu gestor de contraseñas: Meta lo pide para volver a registrar o mover el número.

Requisitos en .env: META_GRAPH_BASE_URL, META_GRAPH_API_VERSION, META_PHONE_NUMBER_ID y META_ACCESS_TOKEN
(token con permisos whatsapp_business_management y whatsapp_business_messaging).

Uso (en TU terminal, no en el chat):  python scripts/registrar_numero.py
"""
import getpass, json, sys, urllib.error, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
env = {}
for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linea and not linea.lstrip().startswith("#"):
        k, v = linea.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

faltan = [k for k in ("META_GRAPH_BASE_URL", "META_GRAPH_API_VERSION", "META_PHONE_NUMBER_ID", "META_ACCESS_TOKEN") if not env.get(k)]
if faltan:
    sys.exit(f"Faltan en .env: {', '.join(faltan)}")

pin = getpass.getpass("PIN de 6 dígitos (no se verá al escribir): ").strip()
if len(pin) != 6 or not pin.isdigit():
    sys.exit("El PIN debe tener exactamente 6 dígitos. No se envió nada.")
if getpass.getpass("Repite el PIN: ").strip() != pin:
    sys.exit("Los PIN no coinciden. No se envió nada.")

url = f"{env['META_GRAPH_BASE_URL']}/{env['META_GRAPH_API_VERSION']}/{env['META_PHONE_NUMBER_ID']}/register"
req = urllib.request.Request(
    url,
    data=json.dumps({"messaging_product": "whatsapp", "pin": pin}).encode(),
    headers={"Authorization": "Bearer " + env["META_ACCESS_TOKEN"], "Content-Type": "application/json",
             "User-Agent": "Firebox/1.0"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        respuesta = json.loads(r.read() or b"{}")
        print("Respuesta de Meta:", respuesta)
        print("REGISTRADO. Guarda el PIN en tu gestor de contraseñas." if respuesta.get("success") else "Meta no confirmó el registro.")
except urllib.error.HTTPError as e:
    cuerpo = e.read().decode("utf-8", "replace")
    try:
        err = json.loads(cuerpo).get("error", {})
        print(f"Error HTTP {e.code}: código {err.get('code')} - {err.get('message')}")
    except Exception:
        print(f"Error HTTP {e.code}: {cuerpo[:300]}")
    sys.exit(1)
