import { describe, it, expect, vi } from 'vitest';
import {
    parseRetryAfter,
    computeBackoffDelay,
    shouldRetry,
    withRetry,
    RETRIABLE_STATUS,
} from './retry.js';

describe('parseRetryAfter', () => {
    it('interpreta segundos como ms', () => {
        expect(parseRetryAfter('5')).toBe(5000);
        expect(parseRetryAfter(2)).toBe(2000);
    });
    it('interpreta una fecha HTTP como delta desde ahora', () => {
        const now = new Date('2026-07-02T10:00:00Z');
        const future = new Date('2026-07-02T10:00:10Z').toUTCString();
        expect(parseRetryAfter(future, now)).toBe(10000);
    });
    it('devuelve null si no hay valor válido', () => {
        expect(parseRetryAfter(null)).toBeNull();
        expect(parseRetryAfter('')).toBeNull();
        expect(parseRetryAfter('no-fecha')).toBeNull();
    });
});

describe('computeBackoffDelay', () => {
    it('respeta Retry-After cuando viene, sin jitter propio', () => {
        expect(computeBackoffDelay(1, { retryAfterMs: 3000 })).toBe(3000);
    });
    it('aplica full jitter: nunca excede min(cap, base·2^n)', () => {
        const rng = () => 0.999999;
        // attempt 3 → base 500 · 2^2 = 2000
        expect(computeBackoffDelay(3, { baseMs: 500, capMs: 30000, rng })).toBeLessThanOrEqual(2000);
    });
    it('jitter con rng=0 da 0', () => {
        expect(computeBackoffDelay(5, { rng: () => 0 })).toBe(0);
    });
    it('respeta el techo capMs', () => {
        const rng = () => 0.9999;
        expect(computeBackoffDelay(20, { baseMs: 500, capMs: 8000, rng })).toBeLessThanOrEqual(8000);
    });
});

describe('shouldRetry', () => {
    it('reintenta 429 si es idempotente y quedan intentos', () => {
        expect(shouldRetry({ status: 429, attempt: 1, maxAttempts: 4, idempotent: true })).toBe(true);
    });
    it('NO reintenta operaciones no idempotentes (evita doble facturación)', () => {
        expect(shouldRetry({ status: 429, attempt: 1, idempotent: false })).toBe(false);
    });
    it('NO reintenta tras agotar intentos', () => {
        expect(shouldRetry({ status: 429, attempt: 4, maxAttempts: 4, idempotent: true })).toBe(false);
    });
    it('NO reintenta un 400/422 (no transitorio)', () => {
        expect(shouldRetry({ status: 422, attempt: 1, idempotent: true })).toBe(false);
        expect(shouldRetry({ status: 400, attempt: 1, idempotent: true })).toBe(false);
    });
    it('el set de códigos reintentables incluye 429 y 5xx', () => {
        expect(RETRIABLE_STATUS.has(429)).toBe(true);
        expect(RETRIABLE_STATUS.has(503)).toBe(true);
        expect(RETRIABLE_STATUS.has(404)).toBe(false);
    });
});

describe('withRetry', () => {
    const noSleep = () => Promise.resolve();

    it('devuelve el resultado al primer intento exitoso', async () => {
        const fn = vi.fn().mockResolvedValue('ok');
        await expect(withRetry(fn, { idempotent: true, sleep: noSleep })).resolves.toBe('ok');
        expect(fn).toHaveBeenCalledTimes(1);
    });

    it('reintenta un 429 idempotente y termina exitoso', async () => {
        const fn = vi
            .fn()
            .mockRejectedValueOnce({ status: 429, headers: {} })
            .mockResolvedValueOnce('ok');
        await expect(
            withRetry(fn, { idempotent: true, sleep: noSleep, rng: () => 0 })
        ).resolves.toBe('ok');
        expect(fn).toHaveBeenCalledTimes(2);
    });

    it('propaga inmediatamente un error no idempotente (no reintenta un create)', async () => {
        const fn = vi.fn().mockRejectedValue({ status: 429, headers: {} });
        await expect(withRetry(fn, { idempotent: false, sleep: noSleep })).rejects.toMatchObject({ status: 429 });
        expect(fn).toHaveBeenCalledTimes(1);
    });

    it('se rinde tras maxAttempts y lanza el último error', async () => {
        const fn = vi.fn().mockRejectedValue({ status: 503, headers: {} });
        await expect(
            withRetry(fn, { idempotent: true, maxAttempts: 3, sleep: noSleep, rng: () => 0 })
        ).rejects.toMatchObject({ status: 503 });
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it('honra Retry-After del header al calcular la espera', async () => {
        const sleeps = [];
        const sleep = (ms) => { sleeps.push(ms); return Promise.resolve(); };
        const fn = vi
            .fn()
            .mockRejectedValueOnce({ status: 429, headers: { 'retry-after': '2' } })
            .mockResolvedValueOnce('ok');
        await withRetry(fn, { idempotent: true, sleep, clock: () => new Date('2026-07-02T10:00:00Z') });
        expect(sleeps[0]).toBe(2000);
    });
});
