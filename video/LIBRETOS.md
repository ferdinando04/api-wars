# Libretos del video pitch de Firebox - API WARS 2026

Narran: **David** (escenas 1, 3, 5, 7 y 9) y **Dylan** (escenas 2, 4, 6 y 8). La escena 8b (el panel) va con la voz clonada de Fernando. Duración total aproximada: 3 min 30 s.
Todo lo que dicen está medido en la corrida real del 05-oct-2026 (`docs/documentacion/evidencias/fase0/`). Por favor no agreguen cifras.

## Cómo grabar (leer antes de empezar)

1. **Una grabación por escena.** Nombre del archivo: `E1_david`, `E2_dylan`, `E3_david`… (así se arma el video solo).
2. Usen la **grabadora de voz del celular** (no la nota de voz de WhatsApp: comprime mucho). Si no hay otra opción, la nota de voz sirve.
3. Lugar **silencioso**, sin ventilador ni música. Celular a **un palmo** de la boca, quieto, sin tocarlo mientras graban.
4. Antes de hablar, **1 segundo en silencio**; al terminar, **1 segundo en silencio**.
5. Lean **despacio y con calma**, como explicándole a un amigo. Sonrían un poco: se nota en la voz.
6. **Si se equivocan**, no corten: hagan una pausa de 2 segundos y repitan **la frase completa** desde el principio. Yo quito el error.
7. Envíen cada archivo a Fernando por WhatsApp **como documento** (clip → Documento), para que no se pierda calidad.

### Cómo se pronuncian las palabras técnicas

| Escrito | Se dice |
| --- | --- |
| API | "ei-pi-ái" o "a-pe-i" (elijan una y úsenla siempre) |
| WhatsApp Cloud API | "guatsap claud ei-pi-ái" |
| OAuth 2.0 | "o-auth dos punto cero" |
| bills validate | "bils válideit" |
| CUFE | "cu-fe" |
| Bre-B | "bre-be" |
| User-Agent | "iúser éiyent" |
| sandbox | "sándbox" |
| Factus Pay | "factus pei" |

---

## E1 - David (25 s) · Presentación y problema

> Hola, somos el equipo de **Firebox**, en API WARS. Soy David y me acompaña Dylan.
>
> En Colombia, muchos negocios ya venden por WhatsApp. Pero la compra, la factura y el pago ocurren por separado: se manda una foto, el total se calcula a mano, se pide una transferencia… y casi nunca se emite la factura electrónica que exige la DIAN.

## E2 - Dylan (25 s) · La solución

> Firebox une esos tres pasos en una sola conversación.
>
> El cliente compra por WhatsApp y, en ese mismo chat, recibe su factura electrónica validada ante la DIAN, con una página de pago con código QR Bre-B dentro del mismo PDF.
>
> Y cuando paga, el chat le confirma solo que su factura quedó pagada.

## E3 - David (25 s) · Las tres APIs

> Para lograrlo conectamos tres APIs, y cada una cumple una función concreta.
>
> WhatsApp Cloud API, la oficial de Meta, para conversar con el cliente y enviarle archivos. Factus API versión dos, para emitir y validar la factura. Y Factus Pay, para cobrar con QR.
>
> Firebox, escrito en Python, orquesta las tres. Y el número de la factura es la referencia que amarra el cobro.

## E4 - Dylan (35 s) · Cómo conectamos Factus

> Así conectamos Factus. Primero pedimos un token con OAuth dos punto cero.
>
> Después consultamos el rango de numeración activo, armamos la factura con los productos, el IVA y la forma de pago, y la enviamos al servicio bills validate.
>
> Factus nos devuelve el número de la factura, el CUFE y la validación de la DIAN. Con ese número descargamos el PDF.
>
> Un detalle que descubrimos probando: si la petición no lleva un User-Agent propio, el firewall de Factus la rechaza.

## E5 - David (30 s) · Cómo conectamos Factus Pay

> Luego, Factus Pay. Nos autenticamos y creamos un recaudo: como referencia, el número de la factura; como monto, el total de la factura. Factus Pay nos entrega el código QR al instante.
>
> Con ese QR armamos la página "Paga aquí" y la unimos al PDF de la factura.
>
> Como Factus Pay no avisa cuando entra el pago, Firebox consulta el estado cada cinco segundos. Apenas aparece pagado, le escribe al cliente.

## E6 - Dylan (30 s) · Cómo conectamos WhatsApp

> Para WhatsApp registramos un número propio en la API oficial de Meta.
>
> Lo verificamos con un código por SMS, creamos la app Firebox y generamos un token permanente.
>
> Con ese token subimos a WhatsApp el PDF y la imagen del QR, y se los enviamos al cliente junto con los mensajes de la compra.

## E7 - David (35 s) · La demo real

> Esta es una corrida real en el sándbox.
>
> A los ocho coma ocho segundos, la factura ya estaba emitida y validada, y el recaudo creado. A los diecisiete segundos, la factura y el QR ya estaban en el WhatsApp del cliente.
>
> Simulamos el pago en el simulador de Factus Pay y, un segundo después de detectarlo, Firebox envió la confirmación: "Pago recibido. Tu factura quedó pagada".
>
> El ciclo completo tomó cuatro minutos y diecinueve segundos, contando lo que tardamos en pagar.

## E8 - Dylan (30 s) · Precisión y pruebas

> Cuidamos mucho el dinero. Calculamos con decimales exactos y con el mismo redondeo bancario que usa la DIAN, línea por línea.
>
> Antes de cobrar, comprobamos que nuestro total sea idéntico al de la factura: doscientos dos mil ciento ochenta y un pesos, igual en los tres sistemas. Si el monto está fuera del rango que permite Factus Pay, no se factura.
>
> Y cada prueba importante la validamos rompiendo el código a propósito, para confirmar que la prueba sí detecta el error.

## E8b - Fernando (70 s) · El panel del vendedor, botón por botón

*(Voz clonada de Fernando con ElevenLabs: no hay que grabarla. En pantalla: capturas reales del panel; el cursor llega a cada botón
cuando la voz lo nombra.)*

> Soy Fernando, del equipo Firebox. Les muestro el panel del vendedor, botón por botón.
>
> Arriba están las métricas: las ventas, lo facturado ante la DIAN, lo cobrado y lo que falta por cobrar. Debajo, la tasa de cobro, el ticket promedio y el IVA, sacados de los totales de Factus. Todo se actualiza solo cada cinco segundos.
>
> Con las pestañas veo solo las pagadas o las que están por cobrar, y el buscador encuentra una factura por número, cliente o CUFE.
>
> Cada factura tiene cuatro botones. PDF descarga la factura desde Factus. XML trae el documento firmado que recibe la DIAN. QR abre el código de pago, el mismo que le llegó al cliente por WhatsApp. Y Consultar le pregunta a Factus Pay, en ese momento, si ya le pagaron.
>
> A la derecha, Conexiones llama de verdad a las tres APIs y muestra cuánto tarda cada una; Probar ahora repite la medición. En Nueva venta de prueba escribo un WhatsApp, y el sistema factura, cobra y envía. En Actividad aparece cada paso.
>
> Por último, Exportar descarga todas las ventas en un archivo CSV, listo para la contabilidad.

## E9 - David (25 s) · Cierre

> Todo está documentado en nuestro repositorio: la especificación, los requisitos, los casos de uso y cada conexión, con lo que medimos.
>
> Esto corre en el sándbox: las facturas no tienen validez fiscal y no se mueve dinero real.
>
> Lo que sigue: catálogo y carrito dentro del chat, varias tiendas en el mismo número y más funciones en el panel del vendedor.
>
> Firebox: de elegir a pagar, con factura, en una sola conversación. ¡Gracias!
