# Factus Pay (pasarela de recaudo con Bre-B): análisis de la documentación y prueba real del sandbox — 25-sep-2026

> Encargo de Fernando (25-sep, 17:1x): *«analiza la documentación letra por letra y, si puedes, verifica y ensaya»*. Hecho entre las 17:2x y
> las 17:4x (hora medida con `date`) con las credenciales que Factus mandó por WhatsApp (guardadas en `.env`, no aquí). Todo lo de abajo está **medido contra el
> sandbox**, no leído: 8 recaudos creados, 1 pago simulado con éxito, 3 fallos simulados, 21 casos de API repetibles (`probar_api.py`, 21/21 como se esperaba a las 17:38), 2 sesiones en el panel.

## 0. En cristiano

1. **Qué es de verdad:** una API muy pequeña (4 llamadas) para crear cobros con QR de Bre-B y consultarlos. **Debajo está Mono** (la
   fintech colombiana que es participante de Bre-B): el QR lo emite Mono y el simulador dice «Error… en Mono». Factus revende Mono con
   su panel y su API.
2. **Funciona:** me autentiqué, creé un cobro de $10.000, recibí el QR al instante (no hay que esperar), simulé el pago y el cobro pasó a
   `paid` en el mismo segundo. Los errores están bien hechos (montos fuera de rango, referencia repetida, token malo, referencia
   inexistente). Responde en medio segundo.
3. **Lo que NO tiene y sí importa:** no hay **aviso de pago (webhook)**: hay que preguntar cada tanto si ya pagaron. No hay **dispersión por
   API** (lo que vendieron como «dispersión» es un campo en el panel: la plata queda en un saldo y «se transfiere a tu llave Bre-B cuando se
   realice una dispersión», sin decir cuándo ni quién la hace). No dice **quién pagó**. No hay **cancelar**. No hay **webhooks ni firma**.
4. **Tu pregunta (¿en cuántos días llega la plata?) sigue sin respuesta**: por lo que muestra el panel, no llega a tu cuenta sola: se acumula
   en Factus Pay y sale a la llave Bre-B que registres en «Empresa» (hoy está vacía) cuando haya una «dispersión». Hay que preguntarles
   la frecuencia y si esa dispersión también cuesta $800.
5. **Veredicto:** sirve para **cobrar por WhatsApp con un QR de Bre-B** (un cobro fijo de $800 + IVA = $952, en vez de un porcentaje), y la
   integración es de una tarde. Pero **no la pondría a cobrar de verdad hasta que Factus responda cinco preguntas** (sección 5), sobre todo la
   del QR en producción y la de la dispersión. Para nosotros el uso más claro es Vexon: el cobro de $129.000 costaría $952 en vez de la
   comisión porcentual de Bold.

## 1. La documentación, completa (pay-developers.factus.com.co)

Son **6 páginas** y una colección de Postman. Leídas enteras (texto extraído en `scripts/factus-pay/doc/*.txt`).

| Página | Lo que dice | Lo medido |
|---|---|---|
| Portada | API REST para crear y consultar recaudos; cada recaudo trae un QR | ✓ |
| Autenticación | `POST /auth` con `email` + `password` → `{token}`; usar `Authorization: Bearer <token>`; errores 401/422/429/500 | ✓ Token de 51 caracteres (formato Laravel Sanctum). **Límite: 5 intentos por minuto** (cabecera `X-RateLimit-Limit: 5`). No dice cuánto dura el token |
| Crear un recaudo | `POST /v1/collections` con `reference_code` (≤ 100, único) y `amount` (10.000 a 12.000.000 COP, 2 decimales); responde 201 `started` con `qr: null`, o 200 «ya existente» con QR | ✗ **La doc se contradice con la realidad**: respondió **200** con `status: ready` **y el QR ya generado** en 0,7 s (mensaje «Recaudo asignado y QR generado correctamente»). El 201/`started` no ocurrió nunca |
| Listar | `GET /v1/collections`, paginado de 15, filtros `status` (started/ready/paid/failed/rejected) y `reference_code` | ✓ Filtros funcionan; status inválido → 422. Límite 80 llamadas/min |
| Ver | `GET /v1/collections/{reference_code}` → detalle con QR; 404 si no existe | ✓ |
| Simulador | Página del sandbox que «escanea» el QR y simula pago exitoso o fallido (saldo, cuenta, timeout) | ✓ el éxito; ✗ **los tres fallos responden «Error al simular el intento de pago en Mono»** y el recaudo se queda en `ready`: no se pueden ver los estados `failed`/`rejected` en el sandbox |
| Colección Postman | Las 4 llamadas | Trae una cabecera **`X-Factus-Access-Key`** con un valor fijo que la doc no menciona y que la API no exige (funcionó sin ella), y variables `{{pay_url_local}}` de desarrollo. Es un archivo con restos internos |

## 2. La prueba, paso a paso (guiones en `scripts/factus-pay/`)

```
POST /auth                          200  0,79 s  token ok · con clave mala → 401 «Credenciales inválidas»
GET  /v1/collections                200  0,45 s  vacío (cuenta nueva)
POST /v1/collections  $10.000       200  0,77 s  status=ready, QR (PNG base64, 13,5 KB) al instante
GET  /v1/collections/{ref}          200  0,56 s  ready + QR
POST misma referencia               200          «Recaudo ya existente» (misma respuesta, mismo QR)
POST amount 9.999 / 12.000.001      422          «must be at least 10000» / «must not be greater than 12000000»
POST sin reference_code / 101 chars 422          mensajes claros (en inglés)
GET con token falso                 401          «Unauthenticated.»
GET referencia inexistente          404          «Recaudo no encontrado»
GET ?status=ready / ?reference_code 200          filtra bien · ?status=otro → 422
Rutas no documentadas (/v1/disbursements, /v1/payouts, /v1/webhooks, /v1/balance, /me, cancel) → 404: NO existen
```

**Pago de punta a punta:** creé `VEXON-SIM-OK-…` ($15.000), decodifiqué su QR, lo «escaneé» en el simulador llamando al mismo método que
usa la cámara (`handleScannedQr`), pulsé «Simular pago» → «Intento de pago simulado correctamente» → **la API lo devolvió `paid` en la
primera consulta**, y `?status=paid` lo lista. Volver a crear ese `reference_code` ya pagado devuelve 200 `paid` con el mismo QR, **y si
mandas otro monto lo ignora** (siguió en 15.000): la referencia manda; no se puede reutilizar.

**El QR por dentro** (decodificado): `mono:breb-participant:sandbox:qr:type=dynamic&id=<32 hex>&key_type=alphanumeric&key_value=@FC4Q…&value=1000000`
→ es un **QR dinámico de Mono** con una **llave Bre-B alfanumérica creada para ese cobro** (una llave por recaudo, se ve en el panel como
«Llave Bre-b: @FC4Q…») y el **monto en centavos**. En el sandbox **no es el QR estándar EMVCo** que exige la industria colombiana
(estándar EASPBV v1.5-2026, vigente desde el 6-feb-2026, con la llave en el TAG 26 y CRC): solo lo lee el simulador de Factus. **En
producción tiene que ser EMVCo para que lo lea Nequi, Bancolombia, Daviplata, etc.** Hay que confirmarlo con Factus.

## 3. Lo que vi en el panel (pay-api-sandbox.factus.com.co)

- **Recaudos:** lista con búsqueda, filtro por estado (Iniciado, Creado, Listo, Pagado, Fallido, Rechazado) y fechas; cada uno con su ID de
  Mono (`bbcol_…`), la llave Bre-B, monto, tu `reference_code` («Documento») y estado. Detalle con «Códigos QR».
- **Códigos QR:** por recaudo: monto, moneda, **una columna «Expiración»** (no documentada) y estado. Los valores son inconsistentes (4 horas en
  un caso, segundos en otros): no se puede saber cuánto dura un QR. Preguntar.
- **Empresa:** tus datos (NIT del titular, persona natural, «No aplica (ZZ)» = no responsable de IVA, Bogotá) y el campo **«Llave Bre-B para
  recibir dispersiones: a esta llave se transferirá el saldo disponible cuando se realice una dispersión»**. **Está vacío.** Es donde entra
  la plata. No hay pantalla de saldo, de movimientos ni de dispersiones.

## 4. Riesgos y huecos (ordenados por lo que más pesa)

1. **Sin webhook.** Para saber si pagaron hay que consultar `GET /v1/collections/{ref}` cada tanto (permite 80/min). Para un cobro por
   WhatsApp sirve (se consulta cada 10-15 s durante unos minutos); para volumen alto, no.
2. **La plata no llega sola a tu cuenta.** Saldo en Factus Pay → dispersión a tu llave Bre-B. Sin frecuencia, sin API, sin costo declarado.
3. **QR del sandbox no estándar.** Si el de producción tampoco fuera EMVCo, nadie podría pagarlo con su banco.
4. **No dice quién pagó** (ni nombre ni banco ni hora): para conciliar solo tienes tu `reference_code`.
5. **Los fallos no se pueden probar** en el sandbox (los tres escenarios dan error de Mono).
6. **Documentación con contradicciones** (201/started vs 200/ready) y una colección de Postman con restos internos (`X-Factus-Access-Key`,
   URLs locales). Señal de producto muy nuevo (lanzamiento «a mediados de octubre»).
7. **Sin duración del token ni forma de revocarlo**; el login del panel y el de la API son la misma contraseña (la que viajó por WhatsApp
   en texto plano: cambiarla desde «Empresa → Contraseña del usuario» cuando pase a producción).
8. Límite por transacción 12.000.000 (la doc) vs 12.100.000 (el WhatsApp) vs 12.110.000 (tope de Bre-B 2026): da igual para nosotros.

## 5. Cinco preguntas para Factus antes de cobrar de verdad

1. ¿La dispersión a mi llave Bre-B es automática? ¿Cada cuánto (mismo día, diaria, semanal)? ¿Cuesta ($800 + IVA también)?
2. ¿El QR de producción es el estándar EMVCo de Bre-B (lo leen todas las apps bancarias)? ¿O el cliente tiene que pagar a la llave escrita?
3. ¿Van a tener webhook de pago (o al menos un `paid_at` y los datos del pagador en el detalle)? ¿Cuándo?
4. ¿Cuánto dura un QR/recaudo antes de vencer, y qué estado toma (`failed`/`rejected`)?
5. ¿Cuánto dura el token, y habrá credenciales de API separadas de la contraseña del panel?

## 6. Para qué nos sirve y cómo se integraría

- **Vexon (cobro del plan Conecta, $129.000):** hoy Bold con link de pago. Con Factus Pay: `POST /v1/collections` con
  `reference_code = "VEXON-<cliente>-<mes>"` → mandar el **QR por WhatsApp** (imagen) al dueño → un cron consulta el estado cada 15 s
  durante 10 min → al `paid`, marcar el pago y avisar. Costo fijo $952 por cobro. Integración: una tarde (`scripts/factus-pay/` ya tiene el
  cliente en Python probado).
- **Kivera / Factus Nova:** mismo patrón (QR + consulta), pero para dinero de terceros o volumen conviene esperar el webhook.
- **Regla que no cambia:** nada de esto entra a producción sin las cinco respuestas y sin un pago real de $10.000 verificado.

## 7. Estado: preguntas enviadas a Factus (25-sep 17:5x)

Fernando envió por WhatsApp las cinco preguntas de §5 más una sexta (los tres fallos del simulador dan «Error al simular el intento de
pago en Mono»: ¿es del sandbox o falta configurar algo?). **Esperando respuesta.** Cuando llegue, se actualiza §5 con lo que digan y se
decide el piloto: un cobro real de $10.000 en producción (mediados de octubre), verificado de punta a punta antes de cobrarle a nadie.

## 8. Ideas de uso (anotadas, no decididas)

1. **Vexon, plan Conecta ($129.000/mes):** en vez del link de Bold (comisión porcentual), el 324 manda el QR de Bre-B por WhatsApp y un
   cron consulta el estado cada 15 s durante 10 min; al `paid`, marca el pago y avisa. Costo fijo $952 por cobro. Una tarde de trabajo con el
   cliente Python de `scripts/factus-pay/`. Depende de las respuestas 1 y 2 (dispersión y QR EMVCo).
2. **Factus Nova:** cada factura electrónica sale con su QR de pago Bre-B (`reference_code` = número de la factura) en el PDF y el correo,
   y el estado `paid` marca la factura como pagada sin conciliar a mano. Es el cruce natural: Factus ya emite la factura; Factus Pay la cobra.
3. **Vex cobrando para nuestros clientes** (pizzerías, clínicas, academias): anticipos de reserva o del pedido por QR dentro de la misma
   conversación de WhatsApp. **Congelada** hasta tener el primer cliente (regla de Kevin, S118 de Vexon): funciones nuevas solo cuando un
   cliente las pida.
4. **Kivera:** no aplica hoy (la app no cobra a terceros); se anota por si un día hay cobros entre conductores.

## 9. Cómo se hizo (para repetirlo)

`scripts/factus-pay/probar_api.py` (autenticar, crear, ver, listar, errores) · `panel_sandbox.py explorar|ver` (Playwright: entra al panel,
fotografía y vuelca controles) · `simular_pago.py` y `sim_extra.py` (punta a punta con el simulador vía Livewire `handleScannedQr`) ·
`doc/` (las 6 páginas en texto + `postman.json`). Credenciales: `.env` (`FACTUS_PAY_SANDBOX_*`), ignorado por git. QR decodificado con pyzbar.

## 10. Respuestas de Factus (26-sep-2026, 8:53 a. m., por WhatsApp; textual, resumido)

| Pregunta | Respuesta de Factus | Qué cambia |
|---|---|---|
| ¿Cómo me llega la plata? | «Entra a la cuenta de Factus, posteriormente puede ser dispersada.» | Confirmado: no llega sola. |
| ¿La dispersión es automática? ¿Cada cuánto? | «Se hará **semanalmente**; más adelante la misma empresa podrá hacer la dispersión cuando quiera y las veces que quiera.» | Plata cada semana, a la llave Bre-B de «Empresa». |
| ¿La dispersión cobra $800 + IVA? | «Sí, $800 + IVA, **no importa el monto** y **tampoco importa si es la suma de varios recaudos**.» | Un cargo fijo por dispersión, no por recaudo dispersado. |
| ¿El QR de producción es el estándar Bre-B? | «En producción el QR saldrá **a nombre de Factus Pay** y se podrá leer con cualquier aplicación financiera que cuente con transacciones a través de llaves.» | Sí, estándar de llaves (EMVCo). El pagador verá «Factus Pay» como beneficiario, no «vegadev». |
| ¿El cliente escribe la llave? | «No, el QR ya va generado con el monto a cobrar; no lo puede modificar; solo da clic en pagar.» | Monto fijo por QR. |
| ¿Webhook de pago? | «Tenemos un endpoint de consulta de estado por referencia para hacer el proceso de **polling**.» | No hay webhook: sondear. |
| ¿Se ve quién pagó y a qué hora? | «Dentro de la plataforma se tiene el detalle de quién pagó cada recaudo.» | En el panel sí; por API no lo dijeron (hoy el detalle no lo trae). |
| ¿Cuánto dura un QR? | «Por defecto el QR vence en **24 horas**.» | Explica la columna «Expiración» del panel. |
| ¿Cuánto dura el token? | «**No vence**, puede usarse siempre el mismo.» | Un token guardado en `.env` basta. |
| ¿Credenciales de API aparte? | «No: son las del panel; se pueden cambiar desde la configuración y entonces hay que generar otro token.» | Cambiar la contraseña que vino por WhatsApp y regenerar el token. |

**Con esto, el veredicto queda así:** sirve para cobrar por QR con costo **fijo**: $952 por recaudo + $952 por cada dispersión semanal
(sin importar cuántos recaudos junte). Para Vexon con un cliente al mes: $1.904 sobre $129.000 (1,5 %); con cinco clientes: $4.760 + $952
= $5.712 sobre $645.000 (0,9 %). El pagador verá «Factus Pay» en su app, no el nombre de Vexon. Faltan por preguntar cuando llegue
producción (mediados de octubre): si el detalle del pagador vendrá por API, y cómo avisan cuándo abren producción.

**Siguiente paso:** esperar el aviso de producción; ese día: cambiar la contraseña, generar el token definitivo, registrar la llave
Bre-B en «Empresa», y hacer **un cobro real de $10.000** de punta a punta (QR → pago desde la app del banco → `paid` → dispersión
semanal → llegada a la llave) antes de cobrarle a un cliente.
