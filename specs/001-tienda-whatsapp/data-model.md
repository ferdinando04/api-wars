# Data Model: Firebox

**Fecha:** 2026-10-06 · **Fuente:** [spec.md](spec.md) (Key Entities) y el código en `app/firebox/`.

En la versión construida (Fases 0 y 1) **no hay base de datos propia**: las facturas viven en Factus y los cobros en Factus Pay, y
Firebox los consulta. Las entidades de abajo son objetos inmutables del código. La Fase 2 agrega persistencia (sección 3).

## 1. Entidades implementadas (en memoria)

| Entidad | Módulo | Campos | Reglas |
| --- | --- | --- | --- |
| `Linea` | `dinero.py` | referencia, nombre, cantidad (int), precio_sin_iva (`Decimal`), tarifa_iva (`Decimal` o `None` = excluido) | base = precio × cantidad redondeado half-even; IVA por línea; excluida no suma IVA ni base gravable |
| `Totales` | `dinero.py` | subtotal, base_gravable, iva, total | total = subtotal + iva; todo `Decimal` a 2 decimales |
| `FacturaEmitida` | `facturacion/factus.py` | numero, cufe, total, validada, notificaciones, crudo | `total` se compara contra `Totales.total` antes de cobrar |
| `Recaudo` | `pagos/factus_pay.py` | referencia (= número de factura), monto, estado (`started`/`ready`/`paid`/`failed`/`rejected`), qr_png | monto entre 10.000 y 12.000.000 COP |
| `Venta` | `ventas.py` | tienda, factura, recaudo, documento (ruta del PDF único) | resultado de `vender()`; entrada de `vigilar()` |
| `Fila` | `web.py` | referencia, monto, estado, clase, fecha, cufe, validada, iva, cliente, url | una por recaudo, completada con el detalle de Factus |
| `Resumen` | `web.py` | ventas, facturado, cobrado, pendiente, iva, pagadas, por_cobrar; `tasa_cobro`, `ticket_promedio` | sumas con `Decimal`; tasa y ticket con redondeo half-even |

### Estados del cobro (Factus Pay → panel)

```mermaid
stateDiagram-v2
    [*] --> started: POST /v1/collections
    started --> ready: QR generado
    [*] --> ready: (lo medido: llega ya en ready)
    ready --> paid: pago Bre-B
    ready --> failed
    ready --> rejected
    paid --> [*]
```

| Estado Factus Pay | En el panel | Cuenta en |
| --- | --- | --- |
| `paid` | Pagado | Cobrado |
| `ready`, `started` | Esperando pago / Creando QR | Por cobrar |
| `failed`, `rejected` | Fallido / Rechazado | (ninguno) |

## 2. Datos externos que se leen

| Sistema | Dato | Uso |
| --- | --- | --- |
| Factus v2 `GET /v2/bills/{n}` | `cufe`, `is_validated`, `validated_at`, `totals.tax_amount`, `customer.names`, `links.public_url` | Fila del panel, IVA facturado, fecha real |
| Factus Pay `GET /v1/collections` | `reference_code`, `amount`, `status`, `qr` | Tabla y métricas del panel |
| Meta `GET /{phone_number_id}` | `display_phone_number`, `status`, `platform_type`, `name_status` | Tarjeta de conexiones |

## 3. Modelo persistente planificado (Fase 2)

```mermaid
erDiagram
    TIENDA ||--o{ PRODUCTO : vende
    TIENDA ||--o{ PEDIDO : recibe
    CONVERSACION }o--|| TIENDA : "está en"
    PEDIDO ||--|{ LINEA_PEDIDO : contiene
    PEDIDO ||--o{ EVENTO : registra
    TIENDA {
        string codigo PK
        string nombre
        string nit
        bytes  credenciales_factus_pay_cifradas
        string token_panel_hash
    }
    PRODUCTO {
        int id PK
        string tienda_codigo FK
        string nombre
        decimal precio_sin_iva
        decimal tarifa_iva
        string foto
        bool activo
    }
    CONVERSACION {
        string wa_id PK
        string tienda_codigo FK
        string estado
        json carrito
    }
    PEDIDO {
        int id PK
        string tienda_codigo FK
        string wa_id
        decimal subtotal
        decimal iva
        decimal total
        string estado
        string numero_factura UK
        string cufe
    }
    LINEA_PEDIDO {
        int pedido_id FK
        string nombre
        int cantidad
        decimal precio_sin_iva
        decimal tarifa_iva
    }
    EVENTO {
        int id PK
        int pedido_id FK
        string tipo
        string detalle
        datetime fecha
    }
```

Claves que sostienen la idempotencia en Fase 2: `MENSAJE_PROCESADO.id` (id del mensaje de Meta), `PEDIDO.numero_factura`,
`TIENDA.codigo`.
