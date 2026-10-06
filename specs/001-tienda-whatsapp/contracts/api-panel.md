# Contrato: API y panel de Firebox (implementado)

**Servidor:** `uvicorn firebox.web:app --host 127.0.0.1 --port 8800` · **Documentación viva:** `/docs` (OpenAPI de FastAPI).
**Autenticación del panel:** HTTP Basic con `PANEL_USUARIO` / `PANEL_CLAVE` del `.env` (sin credenciales → `401`).

| Método | Ruta | Auth | Respuesta | Qué hace |
| --- | --- | --- | --- | --- |
| GET | `/` | - | 307 → `/panel` | Redirección |
| GET | `/salud` | - | `{"ok": true}` | Chequeo de vida |
| GET | `/panel` | Basic | HTML | Página del panel (HTMX) |
| GET | `/panel/tabla` | Basic | HTML parcial | 8 métricas + tabla de facturas y cobros (se pide cada 5 s) |
| GET | `/panel/conexiones` | Basic | HTML parcial | Llamada real a Factus, Factus Pay y Meta con latencia (cada 60 s o "Probar ahora") |
| GET | `/panel/actividad` | Basic | HTML parcial | Pasos de las ventas de prueba (cada 2 s) |
| GET | `/panel/factura/{numero}.pdf` | Basic | `application/pdf` | PDF descargado de Factus (`numero` debe cumplir `^[A-Z]{1,6}\d{1,15}$`, si no `400`) |
| GET | `/panel/factura/{numero}.xml` | Basic | `application/xml` | XML firmado descargado de Factus |
| GET | `/panel/qr/{numero}.png` | Basic | `image/png` | QR del recaudo en Factus Pay |
| POST | `/panel/consultar/{numero}` | Basic | HTML parcial | Estado del recaudo consultado en ese instante, con latencia |
| GET | `/panel/ventas.csv` | Basic | `text/csv` (`;`, UTF-8 con BOM) | factura, fecha, estado, cliente, total, iva, cufe |
| POST | `/panel/venta` | Basic | HTML parcial (`422` si el número es inválido) | Form `para` (celular de 10 dígitos o con 57): lanza `vender()` + `vigilar()` en segundo plano |

## Contratos externos

Los contratos con Factus API v2, Factus Pay y Meta Cloud API (endpoints, cuerpos, errores, límites y lo medido) están en
`docs/documentacion/07_Integraciones_Conexiones.md`.
