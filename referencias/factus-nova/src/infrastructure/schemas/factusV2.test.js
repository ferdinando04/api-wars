import { describe, it, expect } from 'vitest';
import {
    tokenResponse,
    validateBillResponse,
    safeValidate,
} from './factusV2.js';

describe('tokenResponse', () => {
    it('acepta una respuesta OAuth v2 válida', () => {
        const r = safeValidate(tokenResponse, {
            token_type: 'Bearer',
            expires_in: 3600,
            access_token: 'abc',
            refresh_token: 'def',
        });
        expect(r.ok).toBe(true);
    });
    it('rechaza si falta access_token', () => {
        const r = safeValidate(tokenResponse, { token_type: 'Bearer', expires_in: 3600 });
        expect(r.ok).toBe(false);
    });
});

describe('validateBillResponse — respuesta de crear factura v2', () => {
    const validResponse = {
        status: 'Created',
        message: 'Documento registrado y validado con éxito',
        data: {
            reference_code: 'FN-2026-07-02-ABC',
            number: 'SETP990000550',
            cufe: 'a1b2c3d4e5f6',
            is_validated: true,
            totals: { total: '119000.00', tax_amount: '19000.00' },
            links: { qr: 'https://catalogo-vpfe.dian.gov.co/...', public_url: 'https://factus.com.co/...' },
        },
    };

    it('acepta la respuesta v2 completa y expone cufe/links/totals', () => {
        const r = safeValidate(validateBillResponse, validResponse);
        expect(r.ok).toBe(true);
        if (r.ok) {
            expect(r.data.data.cufe).toBe('a1b2c3d4e5f6');
            expect(r.data.data.links.qr).toContain('dian.gov.co');
            expect(r.data.data.totals.total).toBe('119000.00');
        }
    });

    it('tolera campos nuevos de la API sin romper (passthrough)', () => {
        const withExtra = { ...validResponse, data: { ...validResponse.data, campo_nuevo_2027: 'x' } };
        expect(safeValidate(validateBillResponse, withExtra).ok).toBe(true);
    });

    it('rechaza una respuesta a la que le falta data (drift de contrato)', () => {
        const r = safeValidate(validateBillResponse, { status: 'Created', message: 'ok' });
        expect(r.ok).toBe(false);
        if (!r.ok) expect(r.error).toMatch(/forma esperada/);
    });

    it('rechaza si totals no trae total (campo crítico ausente)', () => {
        const bad = { ...validResponse, data: { ...validResponse.data, totals: { tax_amount: '0' } } };
        expect(safeValidate(validateBillResponse, bad).ok).toBe(false);
    });

    it('safeValidate devuelve issues cuando falla, sin lanzar', () => {
        const r = safeValidate(validateBillResponse, null);
        expect(r.ok).toBe(false);
        if (!r.ok) expect(r.issues).toBeDefined();
    });
});
