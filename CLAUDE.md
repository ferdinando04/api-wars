# CLAUDE.md - API WARS (hackathon, 05-oct-2026)

Guía para Claude Code en esta carpeta. El `CLAUDE.md` del escritorio (perfil de Fernando y las tres reglas de trabajo) también
aplica aquí y se carga solo.

## Qué es

**API WARS Hackathon** - «El poder está en tus APIs» · Construye · Innova · Expande.

- **Organizan:** Semillero de investigación Pegasus + Universidad Distrital Francisco José de Caldas, Facultad Tecnológica
  (IEEE Student Branch) + IEEE Computer Society. **Patrocina:** Factus (equipo Halltec).
- **Cuándo / dónde:** lunes 05-oct-2026, edificio Techne, piso 5, sala de informática 1 (Facultad Tecnológica, Bogotá).
- **Equipos de 3 a 4 personas** (no se permite individual ni en pareja). Inscripciones cerradas el 02-oct.
- Detalle del evento, talleres y contactos: `docs/evento/INFO-EVENTO.md`.
- **El reto todavía no se conoce.** Cuando lo anuncien, copiarlo textual en `RETO.md` y seguir la skill `api-wars-hackathon`.

**La ventaja de Fernando:** ya integró la API de Factus en producción (Factus Nova, certificación Halltec del Reto Factus abr-2026),
tiene el motor fiscal v2 validado contra la DIAN y probó Factus Pay (cobro con QR Bre-B) antes de su lanzamiento. Cruzar
**factura electrónica + cobro con QR** es la idea natural si el reto lo permite.

## Estructura

```text
Api_Wars/
├── CLAUDE.md · README.md · RETO.md (enunciado, se llena al anunciarlo)
├── .env (secreto, ignorado) · .env.example · .gitignore
├── .claude/skills/
│   ├── facturas-crear-y-validar/   skill OFICIAL de Factus (igual a la publicada el 05-oct)
│   ├── factus-pay/                 recaudos con QR Bre-B: API, reglas, simulador, patrón factura→cobro
│   └── api-wars-hackathon/         cómo jugar el día: orden de trabajo, trampas de Factus, secretos, entrega
├── app/                            el código del reto (vacío hasta conocerlo)
├── scripts/verificar_credenciales.py
├── docs/
│   ├── evento/                     afiche, capturas del grupo de avisos, INFO-EVENTO.md
│   ├── factus-api/                 colección Postman v2 oficial (05-oct), entorno sin secretos, MIGRACION-V2.md
│   └── factus-pay/                 análisis medido del sandbox + doc oficial en texto + Postman
└── referencias/                    código YA probado (solo lectura; ver referencias/README.md)
    ├── factus-nova/                motor fiscal half-even, mapper v2, cliente con reintentos, BFF con sesión cifrada
    └── factus-pay-scripts/         cliente Python de Factus Pay + simulador con Playwright
```

## Credenciales (`.env`, verificadas el 05-oct-2026 con `scripts/verificar_credenciales.py`)

| Servicio | Estado |
| --- | --- |
| Factus API sandbox **v2** (`FACTUS_*`, principal) | ✅ token OK, `/v2/*` 200 (`/v1/*` da 403). Las dio la organización el 05-oct (`sandboxv2@factus.com.co`) |
| Factus API sandbox **v1** (`FACTUS_V1_*`, respaldo) | ✅ token OK, `/v1/*` 200 · `/v2/*` da 403. Venían de Factus Nova |
| Factus Pay sandbox **equipo** (`FACTUS_PAY_*`, principal) | ✅ token OK, listar recaudos 200. Cuenta que la organización (`retofactus@halltec.co`) envió a Dylan el 05-oct |
| Factus Pay sandbox **personal** (`FACTUS_PAY_PERSONAL_*`, respaldo) | ✅ token OK. Cuenta de Fernando (vegadev). El token no vence |

Origen: Factus v2 y Factus Pay del equipo los mandó la organización (`retofactus@halltec.co`) el 05-oct; Factus v1 y Factus Pay
personal vienen de `Desktop/Retos_Factus/.env` (Vexon y Didier remiten a ese mismo archivo). **Usar v2**: es la que documenta la
skill oficial `facturas-crear-y-validar`. **Señal:** si la organización reparte Factus Pay a los participantes, el reto
probablemente incluye cobros con QR. Usar la cuenta del equipo en la demo.
No se copió `Retos_Factus/emite/.env.local` (base Supabase de otra app, no tiene relación con Factus).

**Reglas de secretos:** el `.env` nunca se sube, nunca se pega en el grupo ni en el chat, y ningún secreto lleva prefijo `VITE_` /
`NEXT_PUBLIC_` (quedaría en el navegador). Las llamadas a Factus y Factus Pay van desde el servidor.

## Comandos

```bash
python scripts/verificar_credenciales.py     # ¿sirven las credenciales HOY? (solo tokens y lecturas)
# el stack de app/ se define cuando se conozca el reto
```

## Skills a usar

- **De este proyecto:** `facturas-crear-y-validar` (armar el JSON de la factura), `factus-pay` (cobro con QR), `api-wars-hackathon` (el día).
- **Globales útiles aquí:** `superpowers:brainstorming` (al definir la solución), `frontend-design` (UI que no parezca plantilla),
  `vercel-deploy` (desplegar temprano), `webapp-testing` / `playwright-skill` (probar la demo en la URL real),
  `superpowers:test-driven-development`, `simular-antes-de-desplegar`, `mcp-builder` (si el reto pide exponer una API a agentes),
  `supabase-postgres` (si hace falta base de datos), `n8n-workflow-patterns` (si conviene automatizar con n8n),
  `pdf` / `anthropic-skills:pptx` (material del pitch).

## Reglas propias de este proyecto

1. **Nada de código ni datos de SDi** (ARDIA, Mirai, migración A3): es IP del empleador. Lo reutilizable es solo Factus Nova y Factus Pay.
2. **Código previo:** `referencias/` existe para no reinventar lo ya validado, pero muchas hackathons exigen que el código se escriba en
   el evento. Confirmar la regla con la organización antes de copiar algo a `app/`; si no se permite, usarlo solo como guía.
3. **Sandbox ≠ DIAN:** las facturas del sandbox no tienen validez fiscal. Decirlo así si el jurado pregunta.
4. **Pitch honesto:** solo cifras medidas en la demo. No decir que Factus Pay está en producción (sale a mediados de octubre de 2026).
5. Trabajo en equipo: el repo del equipo se crea en GitHub cuando se forme el grupo; antes del primer push, confirmar con
   `git status` que `.env` no aparece.
