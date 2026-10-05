import { describe, it, expect, vi } from 'vitest';
import { newIdempotencyKey, referenceCodeFromKey, IdempotencyStore } from './idempotency.js';

describe('newIdempotencyKey', () => {
    it('genera un UUID v4 con formato válido', () => {
        const key = newIdempotencyKey();
        expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    });
    it('genera claves distintas en llamadas sucesivas', () => {
        expect(newIdempotencyKey()).not.toBe(newIdempotencyKey());
    });
});

describe('referenceCodeFromKey', () => {
    it('deriva un reference_code estable de la misma clave', () => {
        const key = '11111111-2222-4333-8444-555555555555';
        expect(referenceCodeFromKey(key)).toBe(referenceCodeFromKey(key));
    });
    it('usa el prefijo dado', () => {
        expect(referenceCodeFromKey('abc-def', 'FACT')).toMatch(/^FACT-/);
    });
});

describe('IdempotencyStore — evita doble ejecución', () => {
    it('ejecuta fn solo la primera vez; el reintento devuelve el cacheado', async () => {
        const store = new IdempotencyStore();
        const fn = vi.fn().mockResolvedValue({ number: 'SETP001' });

        const r1 = await store.run('key-1', fn);
        const r2 = await store.run('key-1', fn); // reintento con la misma clave

        expect(fn).toHaveBeenCalledTimes(1); // NO se re-ejecuta → no doble facturación
        expect(r1).toEqual(r2);
    });

    it('claves distintas ejecutan por separado', async () => {
        const store = new IdempotencyStore();
        const fn = vi.fn().mockResolvedValue('x');
        await store.run('a', fn);
        await store.run('b', fn);
        expect(fn).toHaveBeenCalledTimes(2);
    });

    it('una entrada vencida se vuelve a ejecutar', async () => {
        const store = new IdempotencyStore(1000); // TTL 1s
        const fn = vi.fn().mockResolvedValue('x');
        await store.run('k', fn, 0); // now = 0
        await store.run('k', fn, 2000); // 2s después → vencida
        expect(fn).toHaveBeenCalledTimes(2);
    });

    it('prune elimina entradas vencidas', async () => {
        const store = new IdempotencyStore(1000);
        await store.run('k', () => Promise.resolve('x'), 0);
        expect(store.has('k')).toBe(true);
        store.prune(5000);
        expect(store.has('k')).toBe(false);
    });
});
