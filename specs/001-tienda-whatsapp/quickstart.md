# Quickstart: correr Firebox en 5 pasos

**Requisitos:** Python 3.13, acceso a internet, el archivo `.env` del equipo (no está en git; se pide al equipo, nunca por el grupo).

## 1. Instalar

```bash
git clone https://github.com/ferdinando04/api-wars.git
cd api-wars
python -m pip install -r app/requirements.txt
```

## 2. Poner el `.env` y comprobar las credenciales

Copiar el `.env` del equipo en la raíz del repo (la plantilla sin secretos es `.env.example`) y correr:

```bash
python scripts/verificar_credenciales.py
```

Debe responder token OK en Factus v2 y Factus Pay. Solo hace lecturas.

## 3. Correr las pruebas

```bash
cd app
python -m pytest -q        # 11 pruebas: dinero, panel y sesión de Factus Pay
```

## 4. Levantar el panel del vendedor

```bash
cd app
python -m uvicorn firebox.web:app --host 127.0.0.1 --port 8800
```

Abrir **http://127.0.0.1:8800/panel** (usuario y clave: `PANEL_USUARIO` y `PANEL_CLAVE` del `.env`). La documentación de la API está
en **http://127.0.0.1:8800/docs**.

## 5. Hacer una venta de punta a punta

1. Desde el celular del cliente, escribir cualquier mensaje al WhatsApp de Firebox **+57 324 350 2241** (abre la ventana de 24 h).
2. En el panel, en **Nueva venta de prueba**, escribir ese celular y oprimir **Vender**.
3. Al celular llegan la factura en PDF (con la página "Paga aquí") y el QR.
4. Pagar el QR en el simulador de Factus Pay (sandbox).
5. En segundos llega "✅ Pago recibido" y el panel lo muestra como **Pagado**.

También se puede desde la terminal: `python app/demo_corte_vertical.py --para 57XXXXXXXXXX`.

## Verificaciones extra

```bash
# el panel no se sale de la pantalla en 6 tamaños (necesita Playwright)
python scripts/verificar_panel_responsive.py
```

> Sandbox: las facturas no tienen validez fiscal y no se mueve dinero real.
