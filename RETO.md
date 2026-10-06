# El reto - API WARS 2026

Fuente: sitio oficial del evento (`apiwars.ieeeudtecno.com`) y pantallas compartidas por el equipo, 05-oct-2026.

## Enunciado

"Equipos de estudiantes compiten diseñando e integrando APIs para construir soluciones funcionales en tiempo récord."
APIs propuestas: las de **Factus** (instrucciones y APIs en `developers.factus.com.co`): facturación electrónica v2 y Factus Pay.

## Cómo nos califican

| Criterio | Peso | Qué miran | Cómo lo atiende Firebox |
| --- | --- | --- | --- |
| Integración de APIs | **25 %** | Uso correcto y completo de las APIs propuestas | Factus v2 (token, rangos, adquirente DIAN, emitir y validar, PDF, envío por correo) + Factus Pay (auth, crear, consultar, listar) + WhatsApp Cloud API |
| Funcionamiento | **25 %** | Cumple su propósito y funciona sin fallos | Flujo de punta a punta probado dos veces seguidas antes de presentar; idempotencia; reintentos |
| Calidad del código | 15 % | Arquitectura, organización y documentación | SDD (constitución, spec, plan, tareas) + documentación formal + pruebas con control negativo |
| Innovación | 15 % | Originalidad y valor | Tienda dentro de WhatsApp con factura y QR de pago en el mismo PDF; multi-tienda |
| Experiencia de usuario | 10 % | Usabilidad, diseño y accesibilidad | Botones y listas de WhatsApp; panel claro; mensajes en español |
| Presentación | 10 % | Claridad de la exposición y del material | Presentación + video pitch con la demo real |

## Cronograma (05-oct-2026)

| Hora | Qué |
| --- | --- |
| 08:00 | Ingreso |
| 09:35 | Inicio del reto |
| **13:30** | **Pitches finales** |
| 13:50 | Cierre del evento |

## Qué se entrega y hasta cuándo

**Modificable hasta el martes 06-oct-2026, 4:00 p. m. (UTC-5).**

1. Enlace al repositorio de GitHub (público, o compartido con los jueces): `https://github.com/ferdinando04/api-wars`.
2. Presentación (archivo o enlace).
3. Enlace al video pitch.

El código no se sube a la plataforma: debe permanecer en el repositorio.

## Reglas

- Máximo 4 integrantes por equipo.
- (Pendiente de confirmar con la organización) si se permite código escrito antes del evento: por eso `referencias/` es solo guía.

## Equipo

| Nombre | GitHub | Línea |
| --- | --- | --- |
| Fernando Vega Benavides | ferdinando04 | líder técnico: integraciones (Factus, Factus Pay, WhatsApp), panel y documentación |
| Juan David Vargas Aparicio | DavNor04 | presentación del proyecto y voz del pitch (escenas 1, 3, 5, 7 y 9) |
| Dylan Gerhard Arce Triviño | GerhardArce | cuenta de Factus Pay del equipo y voz del pitch (escenas 2, 4, 6 y 8) |

## La historia de la demo (una sola, de punta a punta)

1. El cliente escribe a Firebox (+57 324 350 2241) desde su WhatsApp y entra a la tienda de relojes.
2. Elige un reloj, lo agrega y paga como consumidor final.
3. Recibe en el chat su factura electrónica validada (Factus v2) con la página "Paga aquí" y el QR (Factus Pay).
4. Se paga el QR con el simulador del sandbox.
5. El chat confirma "✅ Pago recibido" y el panel del vendedor muestra el pedido como pagado.
