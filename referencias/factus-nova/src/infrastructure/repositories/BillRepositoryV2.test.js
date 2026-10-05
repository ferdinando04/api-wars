import { describe, it, expect, vi } from 'vitest';
import { BillRepositoryV2 } from './BillRepositoryV2.js';

const baseForm = {
    customer_identification: '1234567890',
    customer_names: 'Juan Pérez',
    items: [{ name: 'Servicio', quantity: 2, price: 100000, iva_rate: 19 }],
};

const okResponse = {
    data: { number: 'SETP001', cufe: 'abc', totals: { total: '238000.00' }, links: { qr: 'x' } },
};

describe('BillRepositoryV2.emitir', () => {
    it('construye el payload v2 y devuelve data + totals + idempotencyKey', async () => {
        const client = { validateBill: vi.fn().mockResolvedValue(okResponse) };
        const repo = new BillRepositoryV2(client);

        const result = await repo.emitir(baseForm);

        expect(client.validateBill).toHaveBeenCalledOnce();
        const [payload, opts] = client.validateBill.mock.calls[0];
        expect(payload.items[0].taxes[0]).toMatchObject({ code: '01', rate: '19' });
        expect(payload.reference_code).toBeTruthy();
        expect(opts.idempotencyKey).toBeTruthy();
        expect(result.data.cufe).toBe('abc');
        // totals calculados localmente: 2 × 100000 = 200000 + 19% = 238000
        expect(result.totals.total.toString()).toBe('238000');
    });

    it('reusa la misma Idempotency-Key en un reintento del mismo submit', async () => {
        const client = { validateBill: vi.fn().mockResolvedValue(okResponse) };
        const repo = new BillRepositoryV2(client);
        const key = 'key-fija-123';

        await repo.emitir(baseForm, { idempotencyKey: key });
        await repo.emitir(baseForm, { idempotencyKey: key });

        expect(client.validateBill.mock.calls[0][1].idempotencyKey).toBe(key);
        expect(client.validateBill.mock.calls[1][1].idempotencyKey).toBe(key);
        // El reference_code derivado de la misma key es idéntico → mismo documento lógico.
        expect(client.validateBill.mock.calls[0][0].reference_code)
            .toBe(client.validateBill.mock.calls[1][0].reference_code);
    });

    it('propaga el error de validación de cantidad (no llama a la API)', async () => {
        const client = { validateBill: vi.fn() };
        const repo = new BillRepositoryV2(client);
        const bad = { ...baseForm, items: [{ name: 'X', quantity: '', price: 1 }] };
        await expect(repo.emitir(bad)).rejects.toThrow();
        expect(client.validateBill).not.toHaveBeenCalled();
    });
});

describe('BillRepositoryV2.listar', () => {
    it('normaliza la respuesta paginada', async () => {
        const client = { listBills: vi.fn().mockResolvedValue({ data: { data: [{ number: 'A' }], pagination: { total: 1 } } }) };
        const repo = new BillRepositoryV2(client);
        const { bills, pagination } = await repo.listar(1, 10);
        expect(bills).toHaveLength(1);
        expect(pagination.total).toBe(1);
    });
});
