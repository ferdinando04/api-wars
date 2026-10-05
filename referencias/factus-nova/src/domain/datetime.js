/**
 * Utilidades de fecha ancladas a la zona horaria de Colombia (America/Bogota, UTC-5).
 *
 * Bug que esto evita: `new Date().toISOString()` produce fecha en UTC. Entre las
 * 19:00 y 23:59 hora Colombia, eso devuelve la fecha del día siguiente, corriendo
 * el periodo de facturación y el vencimiento un día. La DIAN registra la fecha de
 * emisión en hora local, así que siempre derivamos las fechas en America/Bogota.
 */

const BOGOTA_TZ = 'America/Bogota';

/**
 * Fecha actual en Colombia como 'YYYY-MM-DD'.
 * @param {Date} [now=new Date()]
 * @returns {string}
 */
export function bogotaDate(now = new Date()) {
    // 'en-CA' formatea como YYYY-MM-DD, y timeZone fuerza la hora local de Bogotá.
    return new Intl.DateTimeFormat('en-CA', {
        timeZone: BOGOTA_TZ,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).format(now);
}

/**
 * Hora actual en Colombia como 'HH:mm:ss' (24h).
 * @param {Date} [now=new Date()]
 * @returns {string}
 */
export function bogotaTime(now = new Date()) {
    return new Intl.DateTimeFormat('en-GB', {
        timeZone: BOGOTA_TZ,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    }).format(now);
}

/**
 * Suma días a una fecha 'YYYY-MM-DD' y devuelve 'YYYY-MM-DD', sin desfase de zona.
 * @param {string} isoDate 'YYYY-MM-DD'
 * @param {number} days
 * @returns {string}
 */
export function addDays(isoDate, days) {
    const [y, m, d] = isoDate.split('-').map(Number);
    // Construir en UTC a mediodía evita que un cambio de zona/DST cruce de día.
    const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
    dt.setUTCDate(dt.getUTCDate() + days);
    const yy = dt.getUTCFullYear();
    const mm = String(dt.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(dt.getUTCDate()).padStart(2, '0');
    return `${yy}-${mm}-${dd}`;
}

/**
 * Parsea un timestamp de Factus en formato day-first ('DD-MM-YYYY HH:mm:ss AM/PM')
 * a un objeto Date. Evita el bug de `new Date('13-02-2025')` que JS interpreta
 * como month-first (día 13 → mes 13 → Invalid Date).
 * @param {string} value
 * @returns {Date|null} Date válido o null si no se puede parsear.
 */
export function parseFactusDate(value) {
    if (!value || typeof value !== 'string') return null;
    const m = value.trim().match(
        /^(\d{2})-(\d{2})-(\d{4})(?:\s+(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?)?$/i
    );
    if (!m) {
        const fallback = new Date(value);
        return Number.isNaN(fallback.getTime()) ? null : fallback;
    }
    const [, dd, mm, yyyy, hh, min, ss, ampm] = m;
    let hour = hh ? Number(hh) : 0;
    if (ampm) {
        const isPM = ampm.toUpperCase() === 'PM';
        if (isPM && hour < 12) hour += 12;
        if (!isPM && hour === 12) hour = 0;
    }
    const dt = new Date(Number(yyyy), Number(mm) - 1, Number(dd), hour, Number(min || 0), Number(ss || 0));
    return Number.isNaN(dt.getTime()) ? null : dt;
}
