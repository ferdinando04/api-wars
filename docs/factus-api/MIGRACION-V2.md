# Migración Factus API v1 → v2

Confirmado desde fuente primaria (guía oficial `cambios-v2-v1` de Factus y el SDK
`sbetav/factus-js`). La app estaba construida contra **v1**; la API es **v2** con
cambios breaking. Esta es la referencia de qué cambia.

## Endpoint

| v1 | v2 |
|----|----|
| `POST /v1/bills/validate` | `POST /v2/bills/validate` |

## Cambios de payload

| Área | v1 | v2 |
|------|----|----|
| **Precio del ítem** | `price` = bruto (con IVA) | `price` = **neto** (sin impuestos) |
| **Impuestos** | `items[].tax_rate: 19` (número) | `items[].taxes: [{ code, rate, is_excluded }]` (array) |
| **Excluido** | — | `taxes: [{ is_excluded: true }]` |
| **Exento** | — | `taxes: [{ code: "01", rate: 0 }]` |
| **Métodos de pago** | `payment_form` + `payment_method_code` (sueltos) | `payment_details: [{ payment_form, payment_method_code, amount, due_date? }]` |
| **Cliente: tipo doc** | `identification_document_id` (num) | `identification_document_code` (str) |
| **Cliente: organización** | `legal_organization_id` | `legal_organization_code` |
| **Cliente: tributo** | `tribute_id` | `tribute_code` (default `ZZ`) |
| **Cliente: municipio** | `municipality_id` | `municipality_code` |
| **Ítem: medida** | `unit_measure_id` | `unit_measure_code` |
| **Ítem: estándar** | `standard_id` | `standard_code` |
| **Rango numeración** | obligatorio (round-trip extra) | **opcional** (solo si hay múltiples) |
| **Nuevos campos** | — | `cash_rounding_amount`, `prepayment_details`, `allowance_charges` |

## Autenticación

- El cuerpo del token va como **form-data** (no JSON).
- El **refresh** exige header `Authorization: Bearer <access_token_actual>`.
- Token dura 1 hora. Rate limit: **80 req/min** → HTTP 429 con `Retry-After` y `X-RateLimit-*`.

## Respuesta v2 (crear factura)

Estructura relevante en `data`:
`cufe`, `number`, `is_validated`, `validated_at`, `errors` (notificaciones DIAN),
`totals.total`, `totals.tax_amount`, `links.qr`, `links.public_url`, `items[]`, `taxes[]`.

## Reglas fiscales DIAN

- **Redondeo bancario half-even** (NTC 3711), no el half-up de `toFixed`. Impuesto por
  línea → redondear → sumar, para coincidir con el validador de la DIAN.
- Excluido = sin impuesto; exento (0%) = base gravable con impuesto 0. Son distintos.

## Implementación en este repo

Los helpers v2 ya están escritos y testeados:
`domain/tax.js`, `domain/money.js`, `domain/mappers/InvoiceMapperV2.js`,
`domain/catalogs.js`, `infrastructure/http/factusClientV2.js`,
`infrastructure/schemas/factusV2.js`, `infrastructure/repositories/BillRepositoryV2.js`.

Pendiente: cablear la UI/repositorios de emisión a estos helpers vía el BFF y verificar
contra el sandbox real. Ver [`ESTADO-2026-07-02.md`](./ESTADO-2026-07-02.md).
