import { withRetry } from './retry.js';
import { safeValidate } from '../schemas/factusV2.js';

/**
 * Cliente HTTP para Factus API v2, orientado al patrón BFF.
 *
 * Diseño 10/10:
 *  - La SPA llama a este cliente, que a su vez llama al BFF mismo-origen
 *    (`/api/factus/*`). El BFF custodia el token; el navegador nunca ve secretos.
 *  - Reintentos resilientes (backoff + jitter, respeto de Retry-After) solo en
 *    operaciones idempotentes.
 *  - Validación de contrato con Zod: una respuesta con forma inesperada se vuelve
 *    un error explícito, no corrupción silenciosa.
 *
 * Es agnóstico del transporte: recibe un `fetchFn` (por defecto `fetch` global),
 * lo que lo hace 100% testeable con un mock sin tocar la red.
 */
export class FactusClientV2 {
    /**
     * @param {object} [opts]
     * @param {string} [opts.baseUrl='/api/factus'] Prefijo del BFF (mismo origen).
     * @param {typeof fetch} [opts.fetchFn] Inyectable para tests.
     * @param {object} [opts.retry] Opciones pasadas a withRetry.
     */
    constructor({ baseUrl = '/api/factus', fetchFn, retry = {} } = {}) {
        this._baseUrl = baseUrl.replace(/\/$/, '');
        this._fetch = fetchFn || globalThis.fetch?.bind(globalThis);
        this._retry = retry;
        if (!this._fetch) throw new Error('No hay una implementación de fetch disponible.');
    }

    /**
     * Realiza una petición al BFF y valida la respuesta.
     * @param {object} params
     * @param {string} params.path Ruta relativa (p.ej. '/v2/bills/validate').
     * @param {'GET'|'POST'|'PUT'|'DELETE'} [params.method='GET']
     * @param {object} [params.body]
     * @param {import('zod').ZodType} [params.schema] Esquema de validación de la respuesta.
     * @param {string} [params.idempotencyKey] Habilita reintentos seguros de un POST.
     * @returns {Promise<any>}
     */
    async request({ path, method = 'GET', body, schema, idempotencyKey }) {
        const idempotent = method === 'GET' || Boolean(idempotencyKey);
        const url = `${this._baseUrl}${path}`;

        const doFetch = async () => {
            const headers = { Accept: 'application/json' };
            if (body !== undefined) headers['Content-Type'] = 'application/json';
            if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;

            const res = await this._fetch(url, {
                method,
                headers,
                credentials: 'same-origin', // la cookie httpOnly del BFF viaja sola
                ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
            });

            if (!res.ok) {
                const err = new Error(`Factus BFF respondió ${res.status}`);
                err.status = res.status;
                err.headers = headersToObject(res.headers);
                err.body = await safeJson(res);
                throw err;
            }
            return safeJson(res);
        };

        const json = await withRetry(doFetch, { idempotent, ...this._retry });

        if (schema) {
            const result = safeValidate(schema, json);
            if (!result.ok) {
                const err = new Error(result.error);
                err.name = 'ContractValidationError';
                err.issues = result.issues;
                throw err;
            }
            return result.data;
        }
        return json;
    }

    /** Emite y valida una factura ante la DIAN. POST idempotente. */
    async validateBill(payload, { idempotencyKey, schema } = {}) {
        return this.request({
            path: '/v2/bills/validate',
            method: 'POST',
            body: payload,
            idempotencyKey,
            schema,
        });
    }

    /** Lista facturas (GET, idempotente por naturaleza). */
    async listBills({ page = 1, perPage = 10 } = {}, { schema } = {}) {
        return this.request({ path: `/v2/bills?page=${page}&per_page=${perPage}`, method: 'GET', schema });
    }
}

function headersToObject(headers) {
    const obj = {};
    if (headers?.forEach) headers.forEach((v, k) => { obj[k.toLowerCase()] = v; });
    return obj;
}

async function safeJson(res) {
    try {
        return await res.json();
    } catch {
        return null;
    }
}
