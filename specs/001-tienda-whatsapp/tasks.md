# Tasks: Firebox - tienda en WhatsApp con factura electrónica y QR de pago

**Entrada:** [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/api-panel.md](contracts/api-panel.md)
**Formato:** `[ID] [P?] [Historia] Descripción` · `[P]` = se puede hacer en paralelo · `[x]` hecho · `[ ]` pendiente.
**Estado al 2026-10-06:** Fases 0 y 1 hechas (US2, US3 y US5 parcial). US1, US4, US6 y US7 pendientes.

## Fase 1: Preparación

- [x] T001 Estructura del repo, `.gitignore` con `.env`, `.env.example` sin secretos
- [x] T002 [P] `scripts/verificar_credenciales.py`: token y lectura en Factus v2, Factus v1 (respaldo), Factus Pay equipo y personal
- [x] T003 [P] Número de WhatsApp +57 324 350 2241 registrado en Cloud API (`scripts/registrar_numero.py`, el PIN lo escribe el dueño)
- [x] T004 [P] `app/firebox/config.py`: lectura del `.env` y `User-Agent` propio (FR-031)

## Fase 2: Base que bloquea todo lo demás

- [x] T010 `app/firebox/dinero.py`: `Decimal`, `ROUND_HALF_EVEN`, IVA por línea, excluidos (FR-022) · pruebas `tests/test_dinero.py`
- [x] T011 [P] `app/firebox/facturacion/factus.py`: OAuth2 password, rango 389, `POST /v2/bills/validate`, ver, PDF y XML (FR-030..036)
- [x] T012 [P] `app/firebox/pagos/factus_pay.py`: `/auth`, crear, consultar y listar recaudos; rango 10.000-12.000.000 (FR-040..042)
- [x] T013 [P] `app/firebox/canal/whatsapp.py`: subir medio, texto, imagen, documento, estado del número (FR-005 parcial, FR-006 parcial)
- [x] T014 `app/firebox/documentos/pdf.py`: página "Paga aquí" con el QR y unión con el PDF de Factus (FR-050)

## Fase 3: US2 - Recibir la factura con su QR (P1) ✅

- [x] T020 [US2] `ventas.vender()`: calcula → factura → compara total → PDF → recaudo → PDF único → WhatsApp (FR-035, FR-051)
- [x] T021 [US2] `demo_corte_vertical.py` (CLI) con `--para`, `--sin-whatsapp`
- [x] T022 [US2] Corrida real con evidencia: `docs/documentacion/evidencias/fase0/corrida-2026-10-05-1246.md`
- [ ] T023 [US2] Bajar la entrega a WhatsApp de 17,2 s a ≤ 15 s (SC-002): subir PDF y QR en paralelo

## Fase 4: US3 - Pagar y recibir la confirmación (P1) ✅

- [x] T030 [US3] `ventas.vigilar()`: consulta cada 5 s y envía "✅ Pago recibido" una sola vez (FR-043, FR-044)
- [x] T031 [US3] Corrida real: pago en el simulador → confirmación 1,1 s después de detectarlo (SC-003)

## Fase 5: US5 - Seguir facturas y pagos en vivo (P2) ✅ parcial

- [x] T040 [US5] `firebox/web.py` + plantillas: 8 métricas, tabla en vivo cada 5 s, filtros, buscador
- [x] T041 [US5] Acciones por factura: PDF y XML (Factus), QR y Consultar (Factus Pay); exportar CSV
- [x] T042 [US5] Tarjeta de conexiones: llamada real a Factus, Factus Pay y Meta con latencia
- [x] T043 [US5] Venta de prueba desde el panel con actividad paso a paso
- [x] T044 [US5] Sesión única de Factus Pay + re-autenticación ante 401 (hallazgo: cada `/auth` invalida el token anterior)
- [x] T045 [US5] Responsive medido con Playwright en 6 tamaños (`scripts/verificar_panel_responsive.py`, 6/6)
- [ ] T046 [US5] Token por tienda y cookie firmada (FR-061, FR-062) en lugar de HTTP Basic

## Fase 6: US1 - Comprar dentro del chat (P1) ⏳

- [ ] T050 [US1] `GET/POST /webhooks/whatsapp` con verificación de Meta y firma `X-Hub-Signature-256` (FR-001, FR-002)
- [ ] T051 [US1] Respuesta 200 en < 2 s y proceso en segundo plano; dedupe por `id` de mensaje (FR-003, FR-004)
- [ ] T052 [US1] Máquina de estados de la conversación y palabras `cancelar`/`menu`/`carrito` (FR-010..013)
- [ ] T053 [US1] Catálogo en lista interactiva y carrito con botones (FR-020, FR-021)
- [ ] T054 [US1] Prueba: 10 webhooks repetidos → 1 pedido, 1 factura, 1 recaudo (SC-005)

## Fase 7: US4 - Registrar mi tienda y catálogo (P1) ⏳

- [ ] T060 [US4] Base de datos (modelo de la sección 3 de [data-model.md](data-model.md))
- [ ] T061 [US4] Registro de tienda con credenciales de Factus Pay cifradas con `FERNET_KEY` (FR-070, FR-071)
- [ ] T062 [US4] CRUD de productos desde el panel (SC-006)

## Fase 8: US6 y US7 (P2/P3) ⏳

- [ ] T070 [US6] Elegir cómo recibir el pedido
- [ ] T071 [US7] Buscar productos escribiendo (opcional)

## Fase final: entrega

- [x] T080 Documentación formal + PDF (`docs/documentacion/generar_pdf.py`)
- [x] T081 Video pitch con capturas y código reales (`video/`)
- [ ] T082 Despliegue en una URL pública y prueba de punta a punta 2 veces seguidas (SC-007)

## Controles negativos registrados (Constitución V, SC-008)

Cada prueba se validó rompiendo a propósito la línea que protege y confirmando que se pone roja.

| Resultado | Prueba | Qué se rompió |
| --- | --- | --- |
| DETECTA el bug | `test_redondeo_bancario_y_no_hacia_arriba` | `ROUND_HALF_EVEN` → `ROUND_HALF_UP` |
| DETECTA el bug | `test_resumen_suma_con_decimal` | Suma de montos en `float` |
| DETECTA el bug | `test_sin_clave_no_entra` | Quitar la exigencia de sesión del panel |
| DETECTA el bug | `test_fecha_y_cufe_vienen_de_factus_y_lo_reciente_va_arriba` | Usar `created_at` de Factus Pay (antes era TEST INÚTIL por datos coincidentes; se corrigió el dato de prueba) |
| DETECTA el bug | `test_metricas_tasa_de_cobro_ticket_e_iva` | Cálculo de la tasa de cobro |
| DETECTA el bug | `test_otra_sesion_invalida_el_token_y_el_cliente_se_recupera_solo` | Quitar la re-autenticación ante 401 |
| DETECTA el bug | `scripts/verificar_panel_responsive.py` | Panel sin tarjetas por factura: 4/6 tamaños (768 y 390 px se salían) → 6/6 tras el arreglo |
