# ÍNDICE DE LA DOCUMENTACIÓN - TIENDACHAT (API WARS 2026)

**PROYECTO:** TiendaChat (nombre de trabajo) - tienda multi-negocio dentro de WhatsApp que emite la factura electrónica (Factus) con su
QR de pago (Factus Pay)
**EQUIPO:** Equipo API WARS (integrantes en `RETO.md`) · Líder técnico: Fernando Vega Benavides
**FECHA:** 05-oct-2026 · **VERSIÓN:** 1.0

---

## 1. ¿QUÉ ES ESTA HACKATHON?

**API WARS Hackathon** («El poder está en tus APIs» · Construye · Innova · Expande), organizada por el Semillero de Investigación
Pegasus y la Universidad Distrital Francisco José de Caldas, Facultad Tecnológica (IEEE Student Branch), con la IEEE Computer Society y
el patrocinio de **Factus** (equipo Halltec). Se realiza el 05-oct-2026 en el edificio Techne, piso 5, sala de informática 1, en
equipos de 3 a 4 personas. La organización entregó a los participantes credenciales de sandbox de **Factus API v2** (facturación
electrónica) y de **Factus Pay** (recaudos con QR Bre-B). Detalle del evento: `docs/evento/INFO-EVENTO.md`.

## 2. ¿QUÉ HACE ESTE PROYECTO?

Convierte un número de WhatsApp en una tienda para muchos negocios: el cliente compra en el chat, recibe su factura electrónica
validada por la DIAN con una página de pago con QR dentro del mismo PDF, paga, y el chat le confirma solo que la factura quedó pagada.
El vendedor administra su tienda y ve sus pedidos en vivo desde un panel web. Une los dos productos del patrocinador: **Factus emite y
Factus Pay cobra**, amarrados por el número de factura.

## 3. CÓMO ESTÁ ORGANIZADA LA DOCUMENTACIÓN

Se usan dos marcos a la vez:

- **SDD (Spec-Driven Development, Spec Kit):** primero la especificación, luego el plan técnico, luego las tareas, y solo después el
  código. Vive en `.specify/` y `specs/001-tienda-whatsapp/`.
- **Formato SENA (ADSO):** los mismos contenidos presentados como evidencias formales por fase (Análisis → Planeación → Ejecución),
  con el formato usado en el proyecto formativo NovaMarket (`Desktop/SENA/`). Vive en `docs/sena/`.

La **fuente de verdad es la especificación SDD**; los documentos SENA se derivan de ella y citan su origen.

## 4. MAPA DE DOCUMENTOS Y ESTADO

### Fase 1 - Análisis (qué y por qué) - ✅ escrita, en revisión del equipo

| Documento | SDD | SENA | Estado |
| --- | --- | --- | --- |
| Constitución (reglas que no se negocian) | `.specify/memory/constitution.md` | - | ✅ v1.0.0 |
| Especificación de la funcionalidad | `specs/001-tienda-whatsapp/spec.md` | - | ✅ en revisión |
| Especificación de requisitos (SRS) | ↑ derivado | `01_SRS_Especificacion_Requisitos.md` | ✅ |
| Casos de uso | ↑ derivado | `02_Casos_de_Uso.md` | ✅ |
| Historias de usuario | ↑ derivado | `03_Historias_de_Usuario.md` | ✅ |
| Integraciones y conexiones | `research.md` (parcial) | `07_Integraciones_Conexiones.md` | ✅ (C5 se completa con `contracts/`) |

### Fase 2 - Planeación (cómo) - ⏳ se escribe al aprobar la especificación

| Documento | SDD | SENA (código de evidencia del ADSO) | Estado |
| --- | --- | --- | --- |
| Plan técnico | `plan.md` | Plan de trabajo para construcción de software (GA7-220501096-AA1-EV01) → `09_Plan_de_Trabajo.md` | ⏳ |
| Investigación técnica | `research.md` | - | ⏳ |
| Modelo de datos | `data-model.md` | Modelo conceptual y lógico (GA4-220501095-AA1-EV01), normalización (GA6-220501096-AA1-EV01), modelo E-R (GA6-220501096-AA1-EV02), estructura y script SQL (GA6-220501096-AA2-EV02/EV03) → `04_Modelo_Datos.md` | ⏳ |
| Diagramas UML | - | Entregables UML (GA4-220501095-AA2-EV02), diagrama de clases (AA2-EV04) → `05_Diagramas_UML.md` (clases, secuencia, estados del pedido y de la conversación, actividades) | ⏳ |
| Arquitectura y despliegue | `plan.md` | Arquitectura de software (GA4-220501095-AA2-EV05), diagrama de despliegue (AA3-EV03) → `06_Arquitectura_Despliegue.md` | ⏳ |
| Contratos de la API | `contracts/api-panel.yaml` (OpenAPI) | Servicios web / API (GA7-220501096-AA5-EV02/EV04) → completa `07_Integraciones_Conexiones.md` §8 | ⏳ |
| Interfaces | - | Mapa de navegación y mockups (GA6-220501096-AA3-EV01..EV04) → `08_Interfaces_y_Navegacion.md` (flujo del chat + pantallas del panel) | ⏳ |
| Arranque rápido | `quickstart.md` | - | ⏳ |
| Tareas | `tasks.md` (por línea L1-L4, con responsable) | - | ⏳ |

### Fase 3 - Ejecución y cierre - ⏳ durante y después de la construcción

| Documento | SENA | Estado |
| --- | --- | --- |
| Plan y reporte de pruebas (con controles negativos) | `10_Plan_y_Reporte_de_Pruebas.md` + `evidencias/` | ⏳ |
| Manual técnico (instalación, variables, despliegue) | `11_Manual_Tecnico.md` | ⏳ |
| Manual de usuario (cliente y vendedor) | `12_Manual_Usuario.md` | ⏳ |
| Guion del pitch y del video de la demo | `13_Pitch_y_Demo.md` | ⏳ |

## 5. CÓMO LEER ESTA DOCUMENTACIÓN

- **Jurado o lector nuevo:** sección 2 de este índice → `spec.md` (historias) → `07_Integraciones_Conexiones.md` (cómo se conecta todo).
- **Integrante que va a programar:** constitución → `spec.md` → su línea en `03_Historias_de_Usuario.md` → `tasks.md` (cuando exista).
- **Evaluación tipo SENA:** documentos `01` a `13` en orden.
