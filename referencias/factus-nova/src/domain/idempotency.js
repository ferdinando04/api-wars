/**
 * Idempotencia para la emisión de facturas.
 *
 * Problema: si un "crear factura" se reintenta (timeout de red, doble clic), no
 * debe producir dos facturas certificadas ante la DIAN. Patrón Stripe:
 *  - El cliente genera una Idempotency-Key (UUID v4) al PRIMER submit y la reusa
 *    en cada reintento (por eso se guarda con el borrador, no se regenera por render).
 *  - La clave se envía en el header `Idempotency-Key` y también se ata al
 *    `reference_code` de Factus, que es el guard nativo de deduplicación.
 * Ref: docs.stripe.com/api/idempotent_requests
 */

/**
 * Genera una Idempotency-Key (UUID v4). Usa crypto.randomUUID cuando está
 * disponible; si no, un fallback con suficiente entropía.
 * @returns {string}
 */
export function newIdempotencyKey() {
    if (typeof globalThis.crypto?.randomUUID === 'function') {
        return globalThis.crypto.randomUUID();
    }
    // Fallback RFC-4122-like sin crypto (entornos muy viejos).
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.floor(getRandomByte() / 16);
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

function getRandomByte() {
    if (typeof globalThis.crypto?.getRandomValues === 'function') {
        const buf = new Uint8Array(1);
        globalThis.crypto.getRandomValues(buf);
        return buf[0];
    }
    // Sin CSPRNG: entropía degradada (solo fallback de último recurso).
    return Math.floor((performance?.now?.() ?? 0) * 997) & 0xff;
}

/**
 * Deriva un `reference_code` estable y único a partir de la Idempotency-Key,
 * para que el reintento golpee el mismo documento lógico en Factus.
 * @param {string} idempotencyKey
 * @param {string} [prefix='FN']
 * @returns {string}
 */
export function referenceCodeFromKey(idempotencyKey, prefix = 'FN') {
    const compact = String(idempotencyKey || '').replace(/-/g, '').slice(0, 16).toUpperCase();
    return `${prefix}-${compact}`;
}

/**
 * Almacén de idempotencia en memoria (para la autoridad del lado BFF, o como
 * caché optimista en el cliente). Guarda el resultado de la primera ejecución
 * y lo devuelve en reintentos con la misma clave.
 *
 * En producción el BFF debe usar un store persistente y compartido (Vercel KV /
 * Redis) con TTL; esta implementación en memoria es la interfaz y el fallback.
 */
export class IdempotencyStore {
    /** @param {number} [ttlMs=86400000] Vida de una entrada (24h por defecto, como Stripe). */
    constructor(ttlMs = 24 * 60 * 60 * 1000) {
        /** @type {Map<string, {result: unknown, expiresAt: number}>} */
        this._map = new Map();
        this._ttlMs = ttlMs;
    }

    /**
     * Ejecuta `fn` solo la primera vez para una clave; los reintentos devuelven
     * el resultado cacheado sin re-ejecutar.
     * @template T
     * @param {string} key
     * @param {() => Promise<T>} fn
     * @param {number} [now=Date.now()]
     * @returns {Promise<T>}
     */
    async run(key, fn, now = Date.now()) {
        const existing = this._map.get(key);
        if (existing && existing.expiresAt > now) {
            return /** @type {T} */ (existing.result);
        }
        const result = await fn();
        this._map.set(key, { result, expiresAt: now + this._ttlMs });
        return result;
    }

    /** Elimina entradas vencidas. @param {number} [now=Date.now()] */
    prune(now = Date.now()) {
        for (const [k, v] of this._map) {
            if (v.expiresAt <= now) this._map.delete(k);
        }
    }

    /** @param {string} key @returns {boolean} */
    has(key) {
        return this._map.has(key);
    }
}
