# Constitución del proyecto - TiendaChat (API WARS 2026)

> Reglas que NO se negocian durante la hackathon. Toda especificación, plan, tarea y revisión de código se contrasta contra este
> documento. Si una tarea choca con un principio, gana el principio y se replantea la tarea.
>
> **Versión:** 1.0.0 · **Ratificada:** 05-oct-2026 · **Proyecto:** TiendaChat (nombre de trabajo) - tienda multi-negocio dentro de
> WhatsApp que emite factura electrónica (Factus) con QR de pago (Factus Pay).

## Principios

### I. El dinero lo calcula el código, nunca un modelo de lenguaje

- Precios, impuestos, descuentos, totales y montos de cobro se calculan con `decimal.Decimal` y redondeo **ROUND_HALF_EVEN**
  (bancario, el que usa la DIAN), impuesto por línea, redondear y luego sumar. Prohibido `float` para dinero.
- Si algún día se agrega IA (búsqueda en lenguaje natural), solo puede **sugerir productos**; jamás escribe un precio ni un total.
- **Invariante:** total calculado por nosotros = `total` devuelto por Factus = `amount` del cobro en Factus Pay. Si difieren, el pedido
  se detiene en error y no se cobra.

### II. Una sola fuente de verdad: la API

- El servicio FastAPI es el **único** dueño de la base de datos y el **único** que habla con Meta, Factus y Factus Pay.
- El panel Laravel solo consume la API REST propia. No abre la base de datos ni llama a servicios externos.

### III. Los secretos viven solo en el servidor

- Credenciales de Factus, Factus Pay y Meta: variables de entorno del servicio o columnas cifradas (Fernet) por tienda.
- Nunca en el repositorio, nunca en Laravel, nunca en el navegador, nunca en logs ni en mensajes de error devueltos al cliente.
- Cada webhook de Meta se verifica con la firma `X-Hub-Signature-256` antes de procesarse.

### IV. Idempotencia en todo lo que mueve dinero o documentos fiscales

- Un mensaje de WhatsApp se procesa **una sola vez** (se registra su `id`).
- Un pedido se factura **una sola vez** (bloqueo por estado + `reference_code` único en Factus).
- Un pedido se cobra **una sola vez** (`reference_code` del cobro = número de factura; Factus Pay devuelve el mismo recaudo si se repite).

### V. Una prueba solo cuenta si falla cuando se rompe lo que protege

- Toda prueba de una regla crítica (dinero, idempotencia, firma, estados) se valida con **control negativo**: romper a propósito la
  línea protegida, ver la prueba en rojo, restaurar. Se reporta `DETECTA el bug` o `!!! TEST INUTIL`.
- Prohibido reportar "N pruebas pasan" como prueba de calidad.

### VI. Lo medido manda sobre lo documentado

- Cada contrato externo se verifica contra el sandbox antes de darlo por cierto. Ya medido el 05-oct-2026: Factus exige un
  `User-Agent` propio (sin él, Cloudflare responde 403); Factus Pay crea recaudos con **200 + `ready` + QR**, no 201/`started`
  como dice su documentación; el sandbox v2 de Factus es **compartido** con otros equipos.
- Si la documentación y la realidad difieren, se anota en `docs/sena/07_Integraciones_Conexiones.md` con fecha.

### VII. Honestidad en la demo y en el pitch

- Sandbox ≠ DIAN: las facturas de prueba no tienen validez fiscal y así se dice.
- Factus Pay sale a producción a mediados de octubre de 2026: no se presenta como "en producción".
- Ninguna cifra en el pitch que no se haya medido en la demo.

### VIII. Lo mínimo que demuestra el flujo completo (YAGNI)

- Primero el camino feliz de punta a punta funcionando y desplegado; después el pulido. Cada función nueva debe responder a una
  historia de usuario de `specs/001-tienda-whatsapp/spec.md`.

## Restricciones técnicas

| Tema | Decisión |
| --- | --- |
| API y bot | Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, httpx, pytest |
| Panel del vendedor | Laravel (PHP) + Livewire, consume la API propia con token Bearer |
| Base de datos | SQLite en local, PostgreSQL al desplegar (cambia solo `DATABASE_URL`) |
| WhatsApp | Meta Cloud API oficial, Graph API v25.0, número de prueba (máx. 5 destinatarios) |
| Facturación | Factus API v2 sandbox (`https://api-sandbox.factus.com.co`) |
| Cobro | Factus Pay sandbox (`https://pay-api-sandbox.factus.com.co`) |
| Despliegue | Docker (`docker-compose`: api + panel + db) con HTTPS público |
| Repositorio | `ferdinando04/api-wars` (privado), rama `main` protegida por revisión entre compañeros |

## Flujo de trabajo (SDD)

1. `spec.md` (qué y por qué) → revisión del equipo.
2. `plan.md`, `research.md`, `data-model.md`, `contracts/` (cómo) → revisión.
3. `tasks.md` (pasos ejecutables, con responsable) → implementación con TDD.
4. Toda tarea cierra con: prueba con control negativo + evidencia en `docs/sena/` (pantallazo o salida del comando).

## Gobierno

- Cambiar un principio exige acuerdo del equipo y subir la versión (MAYOR si se elimina o invierte un principio, MENOR si se agrega,
  PARCHE si se aclara redacción).
- En caso de duda durante la hackathon decide Fernando Vega (líder técnico), dejando la razón escrita en el commit.
