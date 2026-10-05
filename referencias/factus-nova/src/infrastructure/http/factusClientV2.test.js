import { describe, it, expect, vi } from 'vitest';
import { FactusClientV2 } from './factusClientV2.js';
import { validateBillResponse } from '../schemas/factusV2.js';

/** Construye una Response-like mock. */
function mockResponse({ ok = true, status = 200, json = {}, headers = {} } = {}) {
    return {
        ok,
        status,
        headers: { forEach: (cb) => Object.entries(headers).forEach(([k, v]) => cb(v, k)) },
        json: () => Promise.resolve(json),
    };
}

const okBill = {
    status: 'Created',
    message: 'ok',
    data: { number: 'SETP001', cufe: 'abc', totals: { total: '119000.00' }, links: { qr: 'x' } },
};

describe('FactusClientV2', () => {
    it('llama al BFF mismo-origen con credentials y devuelve la data validada', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockResponse({ json: okBill }));
        const client = new FactusClientV2({ fetchFn });

        const data = await client.validateBill({ items: [] }, { schema: validateBillResponse });

        expect(fetchFn).toHaveBeenCalledOnce();
        const [url, opts] = fetchFn.mock.calls[0];
        expect(url).toBe('/api/factus/v2/bills/validate');
        expect(opts.method).toBe('POST');
        expect(opts.credentials).toBe('same-origin');
        expect(data.data.cufe).toBe('abc');
    });

    it('adjunta Idempotency-Key cuando se pasa', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockResponse({ json: okBill }));
        const client = new FactusClientV2({ fetchFn });
        await client.validateBill({ items: [] }, { idempotencyKey: 'key-123' });
        expect(fetchFn.mock.calls[0][1].headers['Idempotency-Key']).toBe('key-123');
    });

    it('reintenta un 429 en un POST idempotente (con Idempotency-Key)', async () => {
        const fetchFn = vi
            .fn()
            .mockResolvedValueOnce(mockResponse({ ok: false, status: 429, headers: { 'retry-after': '0' } }))
            .mockResolvedValueOnce(mockResponse({ json: okBill }));
        const client = new FactusClientV2({ fetchFn, retry: { sleep: () => Promise.resolve(), rng: () => 0 } });

        const data = await client.validateBill({ items: [] }, { idempotencyKey: 'k', schema: validateBillResponse });
        expect(fetchFn).toHaveBeenCalledTimes(2);
        expect(data.data.number).toBe('SETP001');
    });

    it('NO reintenta un POST sin Idempotency-Key (evita doble facturación)', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockResponse({ ok: false, status: 429, headers: {} }));
        const client = new FactusClientV2({ fetchFn, retry: { sleep: () => Promise.resolve() } });
        await expect(client.validateBill({ items: [] })).rejects.toMatchObject({ status: 429 });
        expect(fetchFn).toHaveBeenCalledOnce();
    });

    it('lanza ContractValidationError si la respuesta no cumple el esquema', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockResponse({ json: { status: 'ok' } })); // sin data
        const client = new FactusClientV2({ fetchFn });
        await expect(
            client.validateBill({ items: [] }, { schema: validateBillResponse })
        ).rejects.toMatchObject({ name: 'ContractValidationError' });
    });

    it('GET de listado se reintenta ante 503 (idempotente por naturaleza)', async () => {
        const fetchFn = vi
            .fn()
            .mockResolvedValueOnce(mockResponse({ ok: false, status: 503, headers: {} }))
            .mockResolvedValueOnce(mockResponse({ json: { data: [] } }));
        const client = new FactusClientV2({ fetchFn, retry: { sleep: () => Promise.resolve(), rng: () => 0 } });
        await client.listBills({ page: 1 });
        expect(fetchFn).toHaveBeenCalledTimes(2);
    });
});
