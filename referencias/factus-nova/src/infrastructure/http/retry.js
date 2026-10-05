/**
 * Resiliencia HTTP para la API de Factus (límite: 80 solicitudes/minuto).
 *
 * Reglas (fuentes: AWS Builders' Library, Google Cloud, MDN/RFC 9110):
 *  - Ante 429/503, si hay header `Retry-After`, esperar EXACTAMENTE eso (no
 *    apilar backoff propio encima).
 *  - Si no, backoff exponencial con "full jitter": random(0, min(cap, base·2^n)).
 *  - Reintentar SOLO operaciones idempotentes (GET, o POST con Idempotency-Key).
 *  - Cap de intentos (por defecto 4) y respeto del límite superior de espera.
 *
 * Todas las funciones son puras e inyectan el RNG para poder testearlas.
 */

/** Códigos HTTP que justifican reintento (transitorios). */
export const RETRIABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

/**
 * Parsea el header `Retry-After` (delay en segundos o fecha HTTP) a milisegundos.
 * @param {string|number|null|undefined} headerValue
 * @param {Date} [now=new Date()]
 * @returns {number|null} ms de espera, o null si no aplica.
 */
export function parseRetryAfter(headerValue, now = new Date()) {
    if (headerValue === null || headerValue === undefined || headerValue === '') return null;
    const asNumber = Number(headerValue);
    if (Number.isFinite(asNumber)) return Math.max(0, asNumber * 1000);
    const asDate = new Date(headerValue);
    if (!Number.isNaN(asDate.getTime())) return Math.max(0, asDate.getTime() - now.getTime());
    return null;
}

/**
 * Calcula el retardo (ms) antes del próximo intento.
 * @param {number} attempt Número de intento ya fallido (1 = primer fallo).
 * @param {object} [opts]
 * @param {number} [opts.baseMs=500] Base del backoff exponencial.
 * @param {number} [opts.capMs=30000] Techo del retardo.
 * @param {number|null} [opts.retryAfterMs] Si viene, se respeta tal cual (con jitter mínimo).
 * @param {() => number} [opts.rng=Math.random] Fuente de aleatoriedad [0,1).
 * @returns {number} ms de espera.
 */
export function computeBackoffDelay(attempt, opts = {}) {
    const { baseMs = 500, capMs = 30000, retryAfterMs = null, rng = Math.random } = opts;
    if (retryAfterMs !== null && retryAfterMs !== undefined) {
        return Math.min(capMs, Math.max(0, retryAfterMs));
    }
    const exp = Math.min(capMs, baseMs * 2 ** Math.max(0, attempt - 1));
    // Full jitter: random(0, exp) — evita el "thundering herd".
    return Math.floor(rng() * exp);
}

/**
 * ¿Se debe reintentar esta operación tras `attempt` fallos?
 * @param {object} params
 * @param {number} params.status Código HTTP recibido.
 * @param {number} params.attempt Intentos ya realizados.
 * @param {number} [params.maxAttempts=4]
 * @param {boolean} [params.idempotent=false] La operación es segura de reintentar.
 * @returns {boolean}
 */
export function shouldRetry({ status, attempt, maxAttempts = 4, idempotent = false }) {
    if (attempt >= maxAttempts) return false;
    if (!idempotent) return false;
    return RETRIABLE_STATUS.has(status);
}

/**
 * Espera `ms` milisegundos (promesa). Inyectable para tests.
 * @param {number} ms
 * @param {(fn: () => void, ms: number) => void} [setTimeoutFn=setTimeout]
 * @returns {Promise<void>}
 */
export function delay(ms, setTimeoutFn = setTimeout) {
    return new Promise((resolve) => setTimeoutFn(resolve, ms));
}

/**
 * Ejecuta una función async con reintentos resilientes. `fn` debe lanzar un
 * error con forma `{ status, headers }` (como axios) para que se evalúe el
 * reintento; cualquier otro error se propaga sin reintentar.
 *
 * @template T
 * @param {() => Promise<T>} fn
 * @param {object} [opts]
 * @param {number} [opts.maxAttempts=4]
 * @param {boolean} [opts.idempotent=false]
 * @param {number} [opts.baseMs=500]
 * @param {number} [opts.capMs=30000]
 * @param {() => number} [opts.rng=Math.random]
 * @param {(ms:number)=>Promise<void>} [opts.sleep=delay]
 * @param {() => Date} [opts.clock=() => new Date()]
 * @returns {Promise<T>}
 */
export async function withRetry(fn, opts = {}) {
    const {
        maxAttempts = 4,
        idempotent = false,
        baseMs = 500,
        capMs = 30000,
        rng = Math.random,
        sleep = delay,
        clock = () => new Date(),
    } = opts;

    let attempt = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
        try {
            return await fn();
        } catch (error) {
            attempt += 1;
            const status = error?.status ?? error?.response?.status;
            if (!shouldRetry({ status, attempt, maxAttempts, idempotent })) {
                throw error;
            }
            const headers = error?.headers ?? error?.response?.headers ?? {};
            const retryAfterMs = parseRetryAfter(headers['retry-after'] ?? headers['Retry-After'], clock());
            const wait = computeBackoffDelay(attempt, { baseMs, capMs, retryAfterMs, rng });
            await sleep(wait);
        }
    }
}
