# Feature Specification: Firebox - tienda en WhatsApp con factura electrónica y QR de pago (001-tienda-whatsapp)

**Feature Branch:** `001-tienda-whatsapp`
**Created:** 2026-10-05
**Status:** Borrador para revisión del equipo
**Evento:** API WARS Hackathon 2026 - Universidad Distrital (Facultad Tecnológica) + IEEE + Factus
**Input (palabras del equipo):** "Una tienda dentro de WhatsApp en la que se genere la facturación electrónica y el QR o pasarela de
pago dentro de la facturación electrónica, con todo lo que tenemos en el disco y en WhatsApp."

> Constitución que gobierna esta especificación: `.specify/memory/constitution.md`.
> Documentación formal derivada de esta especificación: `docs/documentacion/`.

## Contexto de producto

En Colombia los pequeños negocios ya venden por WhatsApp, pero lo hacen "a mano": mandan fotos sueltas, calculan el total con
calculadora, piden transferencia a una llave o a Nequi, revisan el extracto para ver si pagaron y casi nunca emiten factura
electrónica, aunque la DIAN la exige. **Firebox** convierte un número de WhatsApp en una tienda completa para muchos negocios a la
vez:

1. El cliente compra **sin salir del chat**: catálogo con fotos, carrito y total exacto con IVA.
2. Al confirmar, recibe en el mismo chat su **factura electrónica** (Factus, validada ante la DIAN) con una **página de pago con QR
   Bre-B** (Factus Pay) dentro del mismo PDF.
3. Cuando paga, el chat le confirma **"factura pagada"** sin que nadie revise un extracto.
4. El vendedor ve en un **panel web** cada pedido pasar de *facturado* a *pagado* en vivo.

Es la unión natural de los dos productos del patrocinador: **Factus emite la factura y Factus Pay la cobra**, con la factura y el cobro
amarrados por el mismo número.

### Actores

| Actor | Quién es | Cómo interactúa |
| --- | --- | --- |
| **Cliente** | Persona que compra | Solo por WhatsApp (botones, listas, imágenes, PDF) |
| **Vendedor** | Dueño del negocio | Panel web Laravel: registra su tienda y productos, sigue pedidos |
| **Plataforma (API)** | Nuestro servicio FastAPI | Orquesta WhatsApp, Factus y Factus Pay; dueña de los datos |
| **Meta Cloud API** | Sistema externo | Entrega y envía los mensajes de WhatsApp |
| **Factus API v2** | Sistema externo | Emite y valida la factura electrónica ante la DIAN |
| **Factus Pay** | Sistema externo | Crea el recaudo, genera el QR Bre-B, reporta el estado del pago |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comprar dentro del chat (Priority: P1)

Como **cliente**, quiero ver el catálogo de una tienda, elegir productos y armar un carrito **sin salir de WhatsApp**, para comprar en
el mismo lugar donde ya hablo con el negocio.

**Why this priority:** sin catálogo y carrito no hay compra; es el primer tramo de la demo.

**Independent Test:** con mensajes de WhatsApp simulados (webhook de prueba) se recorre: entrar a la tienda → abrir catálogo → ver un
producto → agregar 2 unidades → ver carrito con subtotal, IVA y total correctos.

**Acceptance Scenarios:**

1. **Given** una tienda activa con código `RELOJES`, **When** el cliente escribe `TIENDA-RELOJES` (o abre su enlace `wa.me`),
   **Then** recibe un saludo con el nombre de la tienda y el botón **[Ver catálogo]**.
2. **Given** el cliente escribe cualquier texto sin código de tienda y sin conversación previa, **When** el bot responde,
   **Then** le muestra una lista con las tiendas activas (máximo 10 por lista; "Ver más" si hay más).
3. **Given** el cliente pulsa **[Ver catálogo]**, **When** la tienda tiene categorías, **Then** recibe una lista interactiva de
   categorías; al elegir una, una lista de productos (título ≤ 24 caracteres, descripción ≤ 72 con el precio).
4. **Given** el cliente elige un producto, **When** el bot responde, **Then** recibe **un solo mensaje** con la foto como encabezado,
   nombre, precio con IVA incluido y los botones **[Agregar] [Ver otro] [Ver carrito]**.
5. **Given** el cliente pulsa **[Agregar]**, **When** el bot pregunta la cantidad (botones **[1] [2] [3]** o un número escrito de 1 a
   20), **Then** el producto queda en el carrito con esa cantidad y el bot confirma con el total parcial y los botones **[Pagar]
   [Seguir comprando] [Ver carrito]** (así se puede pagar sin abrir el carrito).
6. **Given** un carrito con productos, **When** el cliente pulsa **[Ver carrito]**, **Then** ve cada línea (cantidad × nombre = valor),
   el subtotal sin IVA, el IVA, el **total**, y los botones **[Pagar] [Seguir comprando] [Vaciar]**.
7. **Given** el cliente escribe texto libre cuando el bot esperaba un botón, **When** el texto no corresponde a ninguna opción,
   **Then** el bot repite las opciones válidas sin perder el carrito.

---

### User Story 2 - Recibir la factura electrónica con su QR de pago (Priority: P1)

Como **cliente**, quiero que al confirmar mi compra me llegue al chat la **factura electrónica** con el **QR para pagarla**, para tener
el soporte legal y pagar en el mismo paso.

**Why this priority:** es el corazón del reto (Factus + Factus Pay) y lo que diferencia el proyecto.

**Independent Test:** con un carrito armado se confirma la compra contra los sandbox reales de Factus v2 y Factus Pay, y se verifica:
factura validada (`is_validated = true`), número `SETP…`, CUFE, recaudo `ready` con QR, y un PDF enviado que contiene la factura y la
página de pago.

**Acceptance Scenarios:**

1. **Given** un carrito con total entre $10.000 y $12.000.000, **When** el cliente pulsa **[Pagar]**, **Then** el bot pregunta
   **[Factura a mi nombre] [Consumidor final]**.
2. **Given** el cliente elige **[Factura a mi nombre]**, **When** escribe tipo y número de documento, **Then** la plataforma consulta
   el adquirente en la DIAN vía Factus (`GET /v2/dian/acquirer`) y, si existe, pregunta *"¿Eres «nombre», «correo enmascarado»?"*
   **[Sí] [Corregir]**.
3. **Given** la consulta a la DIAN responde 404 (adquirente no encontrado), **When** el bot lo detecta, **Then** pide nombre completo y
   correo, uno por mensaje, y los valida (correo con formato válido).
4. **Given** el cliente elige **[Consumidor final]**, **When** continúa, **Then** no se le piden datos personales y la factura usa el
   cliente genérico definido por Factus.
5. **Given** los datos completos, **When** el bot muestra el resumen (productos, total, datos de factura) y el cliente pulsa
   **[Confirmar compra]**, **Then**:
   - se emite la factura en Factus v2 (`POST /v2/bills/validate`) con `reference_code` único,
   - se crea el recaudo en Factus Pay (`POST /v1/collections`) con `reference_code` = **número de la factura** y `amount` = **total de
     la factura**,
   - el cliente recibe, en este orden: (a) un texto "Tu factura SETP… está lista", (b) **un PDF** con la factura de Factus y una
     página final "Paga aquí" con el QR, el monto, la referencia y el vencimiento (24 h), (c) **la imagen del QR** sola, (d) un texto
     con instrucciones de pago.
6. **Given** el total del carrito es menor de $10.000 o mayor de $12.000.000, **When** el cliente pulsa **[Pagar]**, **Then** el bot
   explica el rango permitido por Factus Pay y **no** emite factura.
7. **Given** Factus rechaza la factura (HTTP 422), **When** la plataforma recibe el error, **Then** el cliente recibe un mensaje
   amable ("no pudimos emitir tu factura, el negocio ya fue avisado"), el pedido queda en `error_factura` con el detalle de Factus y
   **no** se crea cobro.

---

### User Story 3 - Pagar y recibir la confirmación automática (Priority: P1)

Como **cliente**, quiero que cuando pague el QR el chat me confirme solo que mi factura quedó pagada, para no tener que mandar
comprobantes.

**Why this priority:** cierra el ciclo de la demo (compra → factura → pago → confirmación).

**Independent Test:** con un recaudo `ready`, se simula el pago en el simulador del sandbox de Factus Pay y se verifica que en ≤ 10 s el
pedido pasa a `pagado` y el cliente recibe el mensaje de confirmación.

**Acceptance Scenarios:**

1. **Given** un pedido en `cobro_pendiente`, **When** el vigilante de pagos consulta `GET /v1/collections/{referencia}` y el estado es
   `paid`, **Then** el pedido pasa a `pagado`, se registra la hora, y el cliente recibe *"✅ Pago recibido. Tu factura SETP… quedó
   pagada. ¡Gracias por comprar en «tienda»!"*.
2. **Given** un pedido en `cobro_pendiente` con más de 24 h desde la creación del QR, **When** el vigilante lo revisa, **Then** el pedido
   pasa a `vencido` y se deja de consultar.
3. **Given** el cliente escribe "ya pagué" (o pulsa **[Ya pagué]**), **When** el pedido sigue pendiente, **Then** la plataforma consulta
   el estado en ese momento y responde con el resultado real (pagado o "aún no vemos el pago, puede tardar unos segundos").
4. **Given** el vigilante ya marcó un pedido como pagado, **When** vuelve a ver `paid` en la siguiente consulta, **Then** **no** envía un
   segundo mensaje de confirmación.

---

### User Story 4 - Registrar mi tienda y mi catálogo (Priority: P1)

Como **vendedor**, quiero registrar mi negocio y mis productos en un panel web, para tener mi tienda en WhatsApp sin programar.

**Why this priority:** es lo que convierte el proyecto en plataforma multi-tienda; sin tiendas no hay catálogo.

**Independent Test:** desde el panel Laravel desplegado, un vendedor nuevo crea la tienda, carga 3 productos (uno con IVA 19 %, uno con
5 % y uno excluido) con foto, y obtiene su enlace `wa.me`; al abrir el enlace, el bot muestra esa tienda.

**Acceptance Scenarios:**

1. **Given** el formulario de registro, **When** el vendedor ingresa nombre del negocio, NIT, correo, código corto de tienda (único,
   solo letras/números, 3-20) y sus credenciales de Factus Pay, **Then** la API crea la tienda, cifra las credenciales, y devuelve un
   token de acceso del panel y el enlace `https://wa.me/<número>?text=TIENDA-<CÓDIGO>`.
2. **Given** las credenciales de Factus Pay ingresadas son inválidas, **When** la API intenta autenticarse con ellas, **Then** el
   registro se rechaza con el mensaje "No pudimos conectar con tu cuenta de Factus Pay" y no se guarda nada.
3. **Given** una tienda creada, **When** el vendedor agrega un producto con nombre, categoría, precio **sin IVA**, tarifa de IVA
   (19 %, 5 %, 0 % exento o excluido) y una foto (JPG/PNG ≤ 5 MB), **Then** el producto queda activo y el panel muestra el precio con
   IVA calculado por la API.
4. **Given** un producto activo, **When** el vendedor lo desactiva, **Then** deja de aparecer en el catálogo de WhatsApp, pero los
   pedidos anteriores conservan su copia fija del producto.
5. **Given** el vendedor tiene un archivo CSV con columnas `nombre, categoria, precio_sin_iva, iva, foto_url`, **When** lo carga,
   **Then** la API crea los productos válidos y reporta fila por fila los rechazados con el motivo. *(P2 dentro de esta historia.)*

---

### User Story 5 - Seguir pedidos, facturas y pagos en vivo (Priority: P2)

Como **vendedor**, quiero ver mis pedidos y cómo pasan de facturado a pagado sin recargar la página, para saber qué despachar.

**Why this priority:** es el momento "wow" del panel en la demo, pero la compra funciona sin él.

**Independent Test:** con el panel abierto, se hace una compra por WhatsApp y se simula el pago; el panel muestra el pedido nuevo y su
cambio a `pagado` en ≤ 10 s sin recargar.

**Acceptance Scenarios:**

1. **Given** el panel de pedidos abierto, **When** entra un pedido nuevo, **Then** aparece en ≤ 10 s con: fecha, cliente (o
   "Consumidor final"), total, estado, número de factura y enlace al PDF.
2. **Given** un pedido, **When** el vendedor abre su detalle, **Then** ve la línea de tiempo de eventos (mensaje recibido, factura
   emitida, cobro creado, pago recibido) con hora y, si hubo error, el detalle devuelto por Factus o Factus Pay.
3. **Given** un pedido en `error_cobro` (factura emitida pero el cobro falló), **When** el vendedor pulsa **[Reintentar cobro]**,
   **Then** la API vuelve a crear el recaudo con la misma referencia y, si funciona, envía el QR al cliente.
4. **Given** el panel, **When** el vendedor mira el resumen del día, **Then** ve cuántos pedidos, cuánto facturado y cuánto pagado
   (sumas calculadas por la API).

---

### User Story 6 - Elegir cómo recibir el pedido (Priority: P2)

Como **cliente**, quiero indicar si recojo en la tienda o me lo envían, para que el negocio sepa qué hacer con mi compra.

**Independent Test:** en el flujo de compra se elige **[Envío a domicilio]**, se escribe una dirección, y el panel muestra esa dirección
en el pedido.

**Acceptance Scenarios:**

1. **Given** el cliente pulsó **[Pagar]** y dio sus datos de factura, **When** el bot pregunta **[Recojo en tienda] [Envío a
   domicilio]**, **Then** con "Envío" pide la dirección en un mensaje de texto (5-200 caracteres) y la guarda en el pedido.
2. **Given** se eligió envío, **When** se emite la factura, **Then** el costo de envío **no** se suma (fuera de alcance v1; el
   vendedor coordina el envío por fuera) y el resumen lo dice explícitamente.

---

### User Story 7 - Buscar productos escribiendo (Priority: P3, opcional)

Como **cliente**, quiero escribir lo que busco ("reloj dorado para mujer") y recibir productos parecidos, para no recorrer todo el
catálogo.

**Independent Test:** con la tienda de relojes, escribir "dorado mujer" devuelve una lista con productos cuyo nombre, color o
categoría coinciden.

**Acceptance Scenarios:**

1. **Given** el cliente está dentro de una tienda, **When** escribe un texto que no es un comando, **Then** la API busca coincidencias
   (primero por texto; IA solo si hay tiempo) y responde con una lista de máximo 10 productos o "no encontré nada, mira el catálogo".
2. **Given** se usa IA para interpretar el texto, **When** devuelve resultados, **Then** los precios mostrados salen **siempre** de la
   base de datos, nunca del modelo (Constitución, principio I).

---

### Edge Cases

- **Mensaje repetido por Meta:** Meta reintenta webhooks; el mismo `message.id` se ignora la segunda vez (no crea pedido ni respuesta
  doble).
- **Número no autorizado:** el número de prueba de Meta solo escribe a 5 destinatarios registrados; un envío a otro número devuelve el
  error `131030`. La API lo registra y el panel muestra "destinatario no autorizado en modo de prueba".
- **Ventana de 24 h:** si pasan más de 24 h desde el último mensaje del cliente, WhatsApp no deja enviar texto libre (requiere
  plantilla). Como el QR también vence en 24 h, la confirmación de pago casi siempre cae dentro de la ventana; si no, se registra en el
  panel y no se reintenta.
- **Precio cambia mientras el cliente compra:** el carrito guarda el producto, pero al **confirmar** se recalcula con el precio vigente y
  se muestra el resumen actualizado antes de facturar. El pedido guarda una **copia fija** de nombre, precio e IVA.
- **Producto desactivado con el carrito abierto:** al pulsar **[Pagar]** se retira del carrito y se avisa.
- **Carrito vacío:** **[Pagar]** con carrito vacío responde "tu carrito está vacío" y muestra **[Ver catálogo]**.
- **Monto fuera de rango de Factus Pay:** menor de $10.000 o mayor de $12.000.000 → no se factura (historia 2, escenario 6).
- **Factus caído o lento:** 3 reintentos con espera creciente; si sigue fallando → `error_factura`, mensaje amable, aviso en el panel.
- **Factura emitida pero Factus Pay falla:** el pedido queda en `error_cobro`; se envía la factura sin QR y el panel ofrece
  **[Reintentar cobro]**.
- **Sandbox v2 compartido:** otros equipos usan la misma cuenta de Factus; nuestra `reference_code` de factura lleva prefijo único
  `FB-<TIENDA>-<id pedido>` para no chocar.
- **Doble clic en [Confirmar compra]:** el segundo clic encuentra el pedido ya en `facturando`/`facturado` y responde con el estado,
  sin facturar de nuevo.
- **Cliente cambia de tienda a mitad de compra:** escribir `TIENDA-<OTRO>` pregunta si quiere abandonar el carrito actual
  **[Sí, cambiar] [No, seguir]**.
- **Foto de producto inválida o > 5 MB:** el panel la rechaza al subirla; si una foto falla al enviarse por WhatsApp, se envía el
  producto como texto con los mismos botones.
- **Adquirente no encontrado en la DIAN:** se piden nombre y correo a mano (historia 2, escenario 3).
- **Cliente escribe "cancelar" antes de confirmar:** se vacía el carrito y se vuelve al saludo de la tienda.

## Requirements *(mandatory)*

### Functional Requirements

**Canal WhatsApp**

- **FR-001:** La API MUST exponer `GET /webhooks/whatsapp` para la verificación de Meta (`hub.mode`, `hub.verify_token`,
  `hub.challenge`) y `POST /webhooks/whatsapp` para recibir mensajes.
- **FR-002:** La API MUST verificar la firma `X-Hub-Signature-256` (HMAC-SHA256 con el App Secret) de cada POST y rechazar con 401 las
  firmas inválidas.
- **FR-003:** La API MUST responder 200 a Meta en < 2 s y procesar el mensaje en segundo plano.
- **FR-004:** La API MUST registrar el `id` de cada mensaje entrante y descartar duplicados.
- **FR-005:** La API MUST poder enviar: texto, lista interactiva, botones de respuesta (máx. 3, con encabezado de imagen opcional),
  imagen y documento PDF, respetando los límites de Meta (lista: 10 filas, título 24, descripción 72, botón 20 caracteres).
- **FR-006:** El envío por WhatsApp MUST estar aislado en un adaptador de canal con la interfaz `enviar_texto`, `enviar_lista`,
  `enviar_botones`, `enviar_imagen`, `enviar_documento`, para poder cambiar de proveedor sin tocar la conversación.

**Conversación**

- **FR-010:** La conversación MUST modelarse como una máquina de estados determinista por número de WhatsApp: `inicio` →
  `en_tienda` → `viendo_catalogo` → `viendo_producto` → `eligiendo_cantidad` → `en_carrito` → `datos_factura` → `entrega` →
  `confirmando` → `esperando_pago` → `cerrada`.
- **FR-011:** Cada estado MUST aceptar solo sus entradas válidas y, ante cualquier otra, repetir las opciones sin perder datos.
- **FR-012:** Las palabras `cancelar`, `menu` y `carrito` MUST funcionar en cualquier estado anterior a `confirmando`.
- **FR-013:** El código de tienda MUST reconocerse con el patrón `TIENDA-<CÓDIGO>` (mayúsculas o minúsculas) en cualquier mensaje.

**Catálogo y carrito**

- **FR-020:** El catálogo MUST mostrar solo productos activos de la tienda actual, agrupados por categoría, paginados de a 10.
- **FR-021:** El carrito MUST guardar por línea: producto, cantidad (1-20) y precio vigente; y MUST recalcular totales en cada cambio.
- **FR-022:** Los totales MUST calcularse por línea: `base = precio_sin_iva × cantidad`, `iva = round_half_even(base × tarifa / 100,
  2)`; `subtotal = Σ base`, `iva_total = Σ iva`, `total = subtotal + iva_total`. Las líneas excluidas no suman IVA y no se reportan
  como base gravable.

**Facturación (Factus v2)**

- **FR-030:** La API MUST autenticarse con OAuth2 `password` (form-urlencoded) y renovar con `refresh_token` antes de que venza
  (`expires_in` = 3600 s).
- **FR-031:** Toda llamada a Factus MUST enviar un `User-Agent` propio (`Firebox/1.0`); sin él Cloudflare responde 403.
- **FR-032:** La factura MUST emitirse con `POST /v2/bills/validate`, `document: "01"`, `operation_type: "10"`,
  `numbering_range_id` del rango de Factura de Venta activo, `reference_code` = `FB-<TIENDA>-<id pedido>`, ítems con precio **sin
  impuestos** en string con 2 decimales, `unit_measure_code: "94"`, `standard_code: "999"`, `taxes: [{code: "01", rate}]` (o
  `is_excluded: true` para excluidos), y `payment_details` con `payment_form: "2"` (crédito), `payment_method_code: "47"`
  (transferencia), `amount` = total y `due_date` = hoy + 1 día. Si el sandbox rechaza crédito con consumidor final, se usa
  `payment_form: "1"` (contado) con el mismo método, y la diferencia se anota en `docs/documentacion/07_Integraciones_Conexiones.md` §11.
- **FR-033:** Para consumidor final, el `customer` MUST ser exactamente el del ejemplo oficial de Factus v2 ("Con consumidor final").
- **FR-034:** La API MUST consultar `GET /v2/dian/acquirer?identification_document_code=&identification_number=` para autocompletar
  nombre y correo del cliente, tratando 404 como "no encontrado".
- **FR-035:** Tras emitir, la API MUST guardar número, CUFE, `is_validated`, `errors` (notificaciones DIAN) y `total` devuelto, y MUST
  comprobar que el `total` de Factus = total calculado (Constitución I); si difiere → `error_factura`.
- **FR-036:** La API MUST descargar el PDF con `GET /v2/bills/{numero}/download-pdf` (respuesta `{file_name, pdf_base_64_encoded}`).

**Cobro (Factus Pay)**

- **FR-040:** La API MUST autenticarse en Factus Pay (`POST /auth`) una vez por tienda y guardar el token cifrado (no vence).
- **FR-041:** La API MUST crear el recaudo con `POST /v1/collections` `{reference_code: <número de factura>, amount: <total>}` y aceptar
  tanto 200 como 201; si el QR llega `null`, MUST consultarlo con `GET /v1/collections/{referencia}` hasta 3 veces.
- **FR-042:** La API MUST validar antes de facturar que `10.000 ≤ total ≤ 12.000.000`.
- **FR-043:** El vigilante de pagos MUST consultar cada 5 s los pedidos en `cobro_pendiente` y pasar a `pagado` al ver `paid`, o a
  `vencido` a las 24 h. Límite: 80 llamadas/min por cuenta de Factus Pay; si una cuenta tiene más de 6 cobros pendientes, el intervalo
  de cada uno se alarga a `ceil(pendientes × 60 / 70)` segundos (deja margen de 10 llamadas/min para crear cobros y para [Ya pagué]),
  priorizando los cobros creados hace menos de 10 minutos.
- **FR-044:** Las transiciones a `pagado` MUST ser idempotentes: un solo mensaje de confirmación por pedido.

**Documento factura + pago**

- **FR-050:** La API MUST generar un único PDF = PDF de Factus + una página final "Paga aquí" con: nombre de la tienda, número de
  factura, total, QR (imagen del recaudo), referencia, fecha y hora de vencimiento, e instrucciones Bre-B.
- **FR-051:** La API MUST enviar ese PDF como documento de WhatsApp con nombre `Factura-<número>.pdf` y, aparte, la imagen PNG del QR.

**Panel y API REST propia**

- **FR-060:** La API MUST exponer endpoints REST documentados en OpenAPI (`/docs`) para: registro de tienda, inicio de sesión del
  vendedor, CRUD de productos, carga CSV, lista y detalle de pedidos, reintento de cobro y resumen del día.
- **FR-061:** Todo endpoint del panel MUST exigir `Authorization: Bearer <token de tienda>` y devolver solo datos de esa tienda.
- **FR-062:** El panel Laravel MUST refrescar la lista de pedidos cada 5 s (Livewire `wire:poll`) sin recargar la página.

**Multi-tienda y seguridad**

- **FR-070:** Cada tienda MUST tener su propio código, credenciales de Factus Pay cifradas y catálogo; ninguna consulta puede mezclar
  datos de dos tiendas.
- **FR-071:** Las credenciales MUST cifrarse con una llave maestra de entorno (`FERNET_KEY`) y nunca devolverse por la API.
- **FR-072:** Los logs MUST omitir tokens, contraseñas y el número completo de documento del cliente (enmascarado).

**Trazabilidad**

- **FR-080:** Cada cambio de estado de un pedido MUST registrar un evento con hora, tipo y detalle (sin secretos).

### Key Entities

- **Tienda:** negocio vendedor. Código único, nombre, NIT, correo, logo, credenciales Factus Pay (cifradas), token del panel (hash),
  activa.
- **Producto:** pertenece a una tienda. Categoría, nombre, descripción corta, precio sin IVA, tarifa de IVA (19/5/0/excluido), unidad
  (`94`), foto, activo.
- **Conversación:** una por número de WhatsApp. Tienda actual, estado de la máquina, carrito (líneas), datos de factura, tipo de
  entrega, dirección, último mensaje.
- **Pedido:** compra confirmada. Tienda, número de WhatsApp, copia fija de líneas (nombre, cantidad, precio, IVA), subtotal, IVA, total,
  datos de factura, entrega, estado, número de factura, CUFE, referencia del cobro, QR, ruta del PDF, fechas.
- **Evento:** bitácora de un pedido (tipo, detalle, hora).
- **MensajeProcesado:** `id` de mensaje de Meta ya atendido (idempotencia).

Estados del pedido: `confirmado → facturando → facturado → cobro_pendiente → pagado`; salidas de error: `error_factura`, `error_cobro`,
`vencido`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001:** Un cliente completa la compra de un producto como consumidor final (desde "TIENDA-RELOJES" hasta recibir factura + QR)
  en **≤ 3 minutos** y **≤ 15 toques** (cada lista de WhatsApp cuesta 2: abrir y elegir), medido en la demo.
- **SC-002:** Desde **[Confirmar compra]** hasta recibir el PDF y el QR pasan **≤ 15 s** (sandbox), medido en 5 compras seguidas.
- **SC-003:** Desde que se simula el pago hasta el mensaje "✅ Pago recibido" pasan **≤ 10 s**.
- **SC-004:** En 20 compras de prueba con IVA mezclado (19 %, 5 %, excluido), **0 diferencias** entre total calculado, total de Factus y
  monto del recaudo.
- **SC-005:** Reenviar 10 veces el mismo webhook produce **1** pedido, **1** factura y **1** recaudo.
- **SC-006:** Un vendedor nuevo registra su tienda y 3 productos en **≤ 5 minutos** desde el panel desplegado.
- **SC-007:** La prueba de punta a punta pasa **2 veces seguidas** sobre la URL desplegada antes de presentar.
- **SC-008:** Cada prueba de reglas críticas tiene control negativo registrado (`DETECTA el bug`).

## Assumptions

- La demo corre en **sandbox**: facturas de Factus sin validez fiscal; el QR se paga con el **simulador** de Factus Pay.
- Todas las tiendas de la demo facturan con la **misma cuenta sandbox v2** de Factus (la que entregó la organización); en producción
  cada tienda tendría la suya. El modelo de datos ya separa credenciales por tienda.
- Factus Pay: la tienda de relojes usa la cuenta del equipo y una segunda tienda usa la cuenta personal de Fernando, para demostrar que
  el dinero de cada negocio va a su propia cuenta.
- WhatsApp: número de prueba de Meta con hasta 5 destinatarios registrados (los 4 integrantes + 1 jurado).
- Moneda COP; impuestos soportados: IVA 19 %, 5 %, 0 % (exento) y excluido. Sin retenciones ni INC en v1.
- La tienda de ejemplo carga el catálogo real de NovaMarket (`catalogo_tienda.json`, 74 relojes con fotos).
- El equipo trabaja en español; mensajes del bot en español colombiano con tuteo.

## Out of Scope (v1)

- Costos y logística de envío, inventario/stock, devoluciones.
- Anulación automática con nota crédito cuando el QR vence (queda para v2; en v1 el pedido pasa a `vencido`).
- Pagos con tarjeta u otras pasarelas; múltiples monedas.
- Mensajes iniciados por la tienda (requieren plantillas aprobadas por Meta).
- Registro de nuevos números de WhatsApp por tienda (v1: un número para todas, con código de tienda).
- App móvil; roles múltiples dentro de una tienda.
