---
name: api-wars-hackathon
description: Cómo trabajar durante la hackathon API WARS (05-oct-2026, Universidad Distrital + Factus) - arrancar cuando anuncien el reto, recortar el alcance, construir la demo de punta a punta, integrar la API de Factus sin caer en sus trampas conocidas, desplegar temprano y preparar el pitch. Usar con "el reto", "qué hacemos", "cuánto falta", "la demo", "el pitch", "la entrega", "desplegar", "Factus da error", "401/403/422 de Factus", "redondeo", "IVA", "rango de numeración".
---

# API WARS - cómo jugar la hackathon

## 1. Cuando anuncien el reto (primeros 20 minutos)

1. Copiar el enunciado **textual** a `RETO.md` (criterios de evaluación, tiempo, qué se entrega, si piden usar API de Factus/Factus Pay).
2. Preguntar a la organización: ¿dan credenciales de sandbox por equipo? ¿se permite código escrito antes del evento? ¿cómo se entrega (repo, video, deploy)?
3. Correr `python scripts/verificar_credenciales.py` y anotar qué funciona.
4. Elegir **UNA historia de punta a punta** que se pueda mostrar en 3 minutos. Lo demás es "siguiente versión" en el pitch.

## 2. Orden de construcción

1. **Esqueleto vivo** (primera hora): repo + app mínima desplegada en Vercel, aunque solo diga "hola". Un deploy roto a última hora mata la demo.
2. **El camino feliz real** contra el sandbox (nada de datos falsos en la parte que se evalúa).
3. **Pulido visible** (lo que ve el jurado): estados de carga, errores en español, QR/PDF visibles.
4. **Pitch y respaldo**: video corto de la demo grabado ANTES de presentar (si el wifi falla, se muestra el video).

Reparto sugerido en equipo de 3-4: integración Factus/backend · frontend · datos/pruebas/despliegue · pitch y video.

## 3. Trampas de la API de Factus ya medidas (no redescubrirlas)

- **Auth**: `POST /oauth/token` con `grant_type=password`, `client_id`, `client_secret`, `username`, `password` como
  **form-urlencoded**. Token de 3600 s. Refresh (`grant_type=refresh_token`) exige además `Authorization: Bearer <token actual>` en v2.
- **v1 vs v2**: la API se habilita por empresa. La cuenta principal del `.env` (`FACTUS_*`, `sandboxv2@...`, de la organización)
  solo funciona en **`/v2/*`** y da 403 en `/v1/*`; la de respaldo (`FACTUS_V1_*`) es al revés. Un 403 «Version de API no
  disponible para esta empresa» = credenciales de la versión equivocada, no un bug del código. Trabajar en v2 (es lo que documenta la
  skill oficial `facturas-crear-y-validar`).
- **Diferencias v2** (ver `docs/factus-api/MIGRACION-V2.md`): `price` va **sin impuestos**; `taxes: [{code, rate, is_excluded}]`;
  `payment_details: [{payment_form, payment_method_code, amount}]` con **`amount` obligatorio** (sin él → 422); códigos en vez de ids
  (`municipality_code`, `identification_document_code`...); números como **string** con máx. 2 decimales.
- **`unit_measure_code` = `"94"` (unidad)**. El `"70"` no existe → 422.
- **Redondeo**: la DIAN usa **half-even (bancario)**, no `toFixed`. Impuesto por línea, redondear, luego sumar.
  Implementación probada contra la DIAN: `referencias/factus-nova/src/domain/money.js` y `tax.js`.
- **Excluidos vs exentos**: excluido = `is_excluded: true`; exento = `rate: 0`. La base gravable NO suma las líneas excluidas.
- Las "notificaciones" DIAN en `errors` (FAK08, FAJ44b, RUT01...) **no invalidan** la factura si `is_validated: true`.
- **Rate limit**: 80 req/min, 429 con `Retry-After`. Cliente con reintentos: `referencias/factus-nova/src/infrastructure/http/retry.js`.
- **Sin webhooks** en Factus ni en Factus Pay: todo es consulta (pull/polling).
- Sandbox = sin validez ante la DIAN. Decirlo así en el pitch si preguntan.

## 4. Secretos

- `client_secret` y contraseñas **solo en el servidor** (API routes / BFF). Nada con prefijo `VITE_` o `NEXT_PUBLIC_` que sea secreto:
  queda visible en el navegador. Patrón listo: `referencias/factus-nova/api/` (BFF con sesión cifrada).
- Las credenciales se pasan al equipo por privado, nunca por el grupo de WhatsApp ni en un commit. Antes de cada push:
  `git status` y confirmar que `.env` no aparece.

## 5. Antes de decir "listo"

- La demo se prueba **en la URL desplegada**, no en localhost, de punta a punta, dos veces seguidas.
- Un test solo cuenta si falla cuando se rompe lo que protege (romper la línea, ver rojo, restaurar).
- Nada de cifras inventadas en el pitch: solo lo medido en la demo (tiempos, número de documentos emitidos, etc.).
