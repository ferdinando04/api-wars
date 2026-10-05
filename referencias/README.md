# referencias/ - código ya probado (solo lectura)

Copiado el 05-oct-2026. **No se edita aquí**: si algo sirve y las reglas de la hackathon permiten código previo, se copia a `app/` y se
adapta allá. Si no lo permiten, se usa solo como guía.

## factus-nova/ (de `Desktop/Retos_Factus`, rama `feat/factus-v2-foundation`)

| Archivo | Para qué sirve | Estado |
| --- | --- | --- |
| `src/domain/money.js` | Dinero con decimal.js y redondeo half-even (el de la DIAN) | Validado: total igual al de la DIAN al centavo (11-ago-2026) |
| `src/domain/tax.js` | Motor de impuestos v2 (gravado / exento / excluido) | ⚠️ bug conocido: el `taxableAmount` agregado suma las líneas excluidas (debe filtrarlas). Total e IVA sí cuadran |
| `src/domain/catalogs.js` | Tablas DIAN v2 | ⚠️ `DEFAULTS.unit_measure_code = '70'` no existe: usar `'94'`. Revisar `WHR`, tributos y `STANDARD_CODES` contra la doc oficial |
| `src/domain/mappers/InvoiceMapperV2.js` | Arma el JSON de la factura v2 | ⚠️ falta `payment_details[].amount` (obligatorio, sin él → 422) |
| `src/domain/utils/dv.js` | Dígito de verificación del NIT | Validado contra Factus |
| `src/domain/datetime.js`, `idempotency.js` | Fechas Bogotá, Idempotency-Key | Con tests |
| `src/infrastructure/http/factusClientV2.js`, `retry.js` | Cliente v2 + reintentos con `Retry-After` | ⚠️ el cliente no manda `X-Requested-With: fetch` que exige su propio BFF |
| `src/infrastructure/schemas/factusV2.js` | Validación Zod de respuestas v2 | Con tests |
| `src/infrastructure/repositories/BillRepositoryV2.js` | Crear/consultar facturas v2 | Con tests |
| `api/` | BFF para Vercel: login OAuth en servidor, sesión en cookie cifrada AES-256-GCM, proxy con refresh y CSRF | Nunca desplegado |

Dependencias que usa: `decimal.js`, `zod`, `vitest` para los tests.

## factus-pay-scripts/ (Python, solo librería estándar + Playwright para el panel)

`probar_api.py` (21 casos de la API), `simular_pago.py` y `sim_extra.py` (pago de punta a punta con el simulador), `panel_sandbox.py`
(recorre el panel). **Apuntan al `.env` de Retos_Factus por ruta fija**: para usarlos aquí, cambiar la ruta a la del `.env` de este
proyecto y los nombres a `FACTUS_PAY_BASE_URL` / `FACTUS_PAY_EMAIL` / `FACTUS_PAY_PASSWORD`.
