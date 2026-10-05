# ÍNDICE DE LA DOCUMENTACIÓN - FIREBOX (API WARS 2026)

**PROYECTO:** Firebox - tienda multi-negocio dentro de WhatsApp que emite la factura electrónica (Factus) con su QR de pago
(Factus Pay)
**EQUIPO:** Equipo API WARS (integrantes en `RETO.md`) · Líder técnico: Fernando Vega Benavides
**FECHA:** 05-oct-2026 · **VERSIÓN:** 1.1

---

## 1. ¿QUÉ ES ESTA HACKATHON?

**API WARS Hackathon** («El poder está en tus APIs» · Construye · Innova · Expande), organizada por el Semillero de Investigación
Pegasus y la Universidad Distrital Francisco José de Caldas, Facultad Tecnológica (IEEE Student Branch), con la IEEE Computer Society y
el patrocinio de **Factus** (equipo Halltec). Se realiza el 05-oct-2026 en el edificio Techne, piso 5, sala de informática 1, en
equipos de 3 a 4 personas. La organización entregó a los participantes credenciales de sandbox de **Factus API v2** (facturación
electrónica) y de **Factus Pay** (recaudos con QR Bre-B). Detalle del evento: `docs/evento/INFO-EVENTO.md`.

## 2. ¿QUÉ HACE FIREBOX?

Convierte un número de WhatsApp en una tienda para muchos negocios: el cliente compra en el chat, recibe su factura electrónica
validada por la DIAN con una página de pago con QR dentro del mismo PDF, paga, y el chat le confirma solo que la factura quedó pagada.
El vendedor administra su tienda y ve sus pedidos en vivo desde un panel web. Une los dos productos del patrocinador: **Factus emite y
Factus Pay cobra**, amarrados por el número de factura.

## 3. CÓMO ESTÁ ORGANIZADA LA DOCUMENTACIÓN

- **SDD (Spec-Driven Development, Spec Kit):** primero la especificación, luego el plan técnico, luego las tareas, y solo después el
  código. Vive en `.specify/` y `specs/001-tienda-whatsapp/`. **Es la fuente de verdad.**
- **Documentación formal por fases** (Análisis → Planeación → Ejecución): los mismos contenidos presentados como documentos completos
  para el jurado y para quien mantenga el proyecto. Vive en `docs/documentacion/` y cada documento cita de qué parte de la spec sale.

## 4. MAPA DE DOCUMENTOS Y ESTADO

### Fase 1 - Análisis (qué y por qué) - ✅ escrita, en revisión del equipo

| Documento | Archivo | Estado |
| --- | --- | --- |
| Constitución (reglas que no se negocian) | `.specify/memory/constitution.md` | ✅ v1.0.0 |
| Especificación de la funcionalidad (SDD) | `specs/001-tienda-whatsapp/spec.md` | ✅ en revisión |
| Especificación de requisitos (SRS, IEEE 830) | `docs/documentacion/01_SRS_Especificacion_Requisitos.md` | ✅ |
| Casos de uso | `docs/documentacion/02_Casos_de_Uso.md` | ✅ |
| Historias de usuario | `docs/documentacion/03_Historias_de_Usuario.md` | ✅ |
| Integraciones y conexiones | `docs/documentacion/07_Integraciones_Conexiones.md` | ✅ (la conexión panel → API se completa con `contracts/`) |

### Fase 2 - Planeación (cómo) - ⏳ se escribe al aprobar la especificación

| Documento | Archivo SDD | Documento formal | Estado |
| --- | --- | --- | --- |
| Plan técnico y plan de trabajo | `plan.md` | `09_Plan_de_Trabajo.md` | ⏳ |
| Investigación técnica | `research.md` | - | ⏳ |
| Modelo de datos (conceptual, lógico, entidad-relación, normalización, diccionario, script SQL) | `data-model.md` | `04_Modelo_Datos.md` | ⏳ |
| Diagramas UML (clases, secuencia, estados del pedido y de la conversación, actividades) | - | `05_Diagramas_UML.md` | ⏳ |
| Arquitectura y despliegue | `plan.md` | `06_Arquitectura_Despliegue.md` | ⏳ |
| Contratos de la API (OpenAPI) | `contracts/api-panel.yaml` | completa `07_Integraciones_Conexiones.md` §8 | ⏳ |
| Interfaces (flujo del chat y pantallas del panel) | - | `08_Interfaces_y_Navegacion.md` | ⏳ |
| Arranque rápido | `quickstart.md` | - | ⏳ |
| Tareas con responsable | `tasks.md` | - | ⏳ |

### Fase 3 - Ejecución y cierre - ⏳ durante y después de la construcción

| Documento | Archivo | Estado |
| --- | --- | --- |
| Plan y reporte de pruebas (con controles negativos) | `10_Plan_y_Reporte_de_Pruebas.md` + `evidencias/` | ⏳ |
| Manual técnico (instalación, variables, despliegue) | `11_Manual_Tecnico.md` | ⏳ |
| Manual de usuario (cliente y vendedor) | `12_Manual_Usuario.md` | ⏳ |
| Guion del pitch y del video de la demo | `13_Pitch_y_Demo.md` | ⏳ |

## 5. CÓMO LEER ESTA DOCUMENTACIÓN

- **Jurado o lector nuevo:** sección 2 de este índice → `spec.md` (historias) → `07_Integraciones_Conexiones.md` (cómo se conecta todo).
- **Integrante que va a programar:** constitución → `spec.md` → su línea en `03_Historias_de_Usuario.md` → `tasks.md` (cuando exista).
- **Revisión formal completa:** documentos `01` a `13` en orden.
