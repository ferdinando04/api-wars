---
name: factus-pay
description: Cobrar con QR de Bre-B usando la API de Factus Pay (recaudos) - autenticar, crear un recaudo, mostrar el QR, consultar si ya pagaron (polling) y simular el pago en el sandbox. Usar cuando aparezca "Factus Pay", "recaudo", "cobro con QR", "Bre-B", "pasarela de pago", "link/QR de pago", "marcar la factura como pagada", "simular pago", o al cruzar facturación (Factus) con cobro.
---

# Factus Pay - cobro con QR de Bre-B

Todo lo de abajo está **medido contra el sandbox** (25-sep-2026, re-verificado el 05-oct-2026) más las respuestas
escritas de Factus del 26-sep. Detalle completo: `docs/factus-pay/FACTUS-PAY-ANALISIS-2026-09-25.md`.
Doc oficial en texto: `docs/factus-pay/doc/`. Cliente Python probado: `referencias/factus-pay-scripts/`.

## La API completa (son 4 llamadas)

| Llamada | Qué hace | Notas medidas |
|---|---|---|
| `POST /auth` `{email, password}` | Devuelve `{token}` | **El token no vence** (Factus). Límite **5 llamadas/min**: pedir UNA vez y reutilizar |
| `POST /v1/collections` `{reference_code, amount}` | Crea el recaudo y su QR | La doc dice 201/`started`/`qr:null`; **la API real da 200, `status: ready` y el QR ya generado** (~0,7 s) |
| `GET /v1/collections/{reference_code}` | Detalle + QR + estado | 404 `"Recaudo no encontrado"` |
| `GET /v1/collections?status=&reference_code=` | Lista paginada de 15 | `status` ∈ `started, ready, paid, failed, rejected`; otro valor → 422 |

- Base sandbox: `FACTUS_PAY_BASE_URL` (`https://pay-api-sandbox.factus.com.co`). Producción: `https://pay-api.factus.com.co` (sale a mediados de octubre de 2026).
- Cabeceras: `Authorization: Bearer <token>`, `Accept: application/json`, `Content-Type: application/json`.
- Respuesta: `{"data": {"reference_code", "amount", "status", "created_at", "qr": "data:image/png;base64,..."}, "status": "success", "message": ...}`.
  El `qr` ya es un data-URI: se pone directo en `<img src=...>`.
- Límite general `/v1`: **80 llamadas/min**.

## Reglas que muerden

1. `amount` entre **10.000 y 12.000.000 COP** (fuera de rango → 422).
2. `reference_code` ≤ 100 caracteres y **único**: repetirlo devuelve el MISMO recaudo e **ignora el monto nuevo**. Si ya está pagado devuelve `paid`.
   Usar referencias con prefijo y algo único: `APIWARS-<factura>-<timestamp>`.
3. **No hay webhook.** Para saber si pagaron: consultar `GET /v1/collections/{ref}` cada 5-15 s mientras el QR está en pantalla (polling), y parar al ver `paid`.
4. El QR **vence a las 24 h**. No existe cancelar, ni dispersión por API, ni "quién pagó" por API (solo en el panel).
5. Las credenciales de la API **son las mismas del panel**. Nunca en el frontend: las llamadas van desde el backend/BFF.

## Simular el pago en el sandbox (para la demo)

El panel sandbox tiene `/simulator`: se escanea el QR con la cámara y se pulsa «Simular pago» → el recaudo pasa a `paid` en el acto.
- Sin cámara (automatizado con Playwright): login en `/login` (el clic debe ir a `button[type=submit]`, no al ojo de la contraseña),
  ir a `/simulator` y ejecutar `window.Livewire.all()[0].$wire.call('handleScannedQr', <texto del QR decodificado>)`. Ejemplo completo en
  `referencias/factus-pay-scripts/simular_pago.py`.
- **Los 3 escenarios de fallo** (saldo, cuenta, timeout) responden «Error al simular el intento de pago en Mono» y el recaudo queda en
  `ready`: en el sandbox **no se puede mostrar un pago fallido**. Para la demo, simular el fallo en la propia app (timeout de polling).
- El QR del sandbox es formato Mono (`mono:breb-participant:sandbox:qr:...`), no lo lee una app bancaria. En producción será el estándar
  de llaves Bre-B, a nombre de «Factus Pay».

## Patrón de integración (el que cierra el círculo con Factus)

```
Factura validada en Factus (número, total)
  → POST /v1/collections {reference_code: número de factura, amount: total}
  → mostrar el QR (en pantalla / PDF / WhatsApp)
  → polling GET /v1/collections/{ref} hasta paid (o vencer)
  → marcar la factura como pagada
```

Costo real (para el pitch): $800 + IVA fijo por recaudo y $800 + IVA por cada dispersión semanal, sin importar el monto.

## Verificar antes de decir "funciona"

`python scripts/verificar_credenciales.py` (token + listado). Una integración se da por buena solo cuando un recaudo creado desde nuestro
código pasa a `paid` con el simulador y nuestro polling lo detecta.
