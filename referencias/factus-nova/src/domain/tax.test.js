import { describe, it, expect } from 'vitest';
import { computeLineTotals, computeInvoiceTotals } from './tax.js';

describe('computeLineTotals — semántica v2 (precio neto)', () => {
    it('una línea con IVA 19% suma la base + el impuesto', () => {
        const line = computeLineTotals({ quantity: 1, price: 100000, taxes: [{ code: '01', rate: 19 }] });
        expect(line.taxable.toString()).toBe('100000');
        expect(line.taxAmount.toString()).toBe('19000');
        expect(line.total.toString()).toBe('119000');
    });

    it('aplica descuento por porcentaje antes del impuesto', () => {
        const line = computeLineTotals({ quantity: 2, price: 50000, discount_rate: 10, taxes: [{ code: '01', rate: 19 }] });
        // bruto 100000, desc 10% = 10000, base 90000, IVA 19% = 17100, total 107100
        expect(line.gross.toString()).toBe('100000');
        expect(line.discount.toString()).toBe('10000');
        expect(line.taxable.toString()).toBe('90000');
        expect(line.taxAmount.toString()).toBe('17100');
        expect(line.total.toString()).toBe('107100');
    });

    it('ítem exento (0%) causa base gravable pero impuesto 0', () => {
        const line = computeLineTotals({ quantity: 1, price: 100000, taxes: [{ code: '01', rate: 0 }] });
        expect(line.taxable.toString()).toBe('100000');
        expect(line.taxAmount.toString()).toBe('0');
        expect(line.total.toString()).toBe('100000');
    });

    it('ítem excluido no causa impuesto', () => {
        const line = computeLineTotals({ quantity: 1, price: 100000, taxes: [{ is_excluded: true }] });
        expect(line.taxAmount.toString()).toBe('0');
        expect(line.total.toString()).toBe('100000');
    });

    it('soporta múltiples impuestos por ítem (IVA + INC)', () => {
        const line = computeLineTotals({
            quantity: 1,
            price: 100000,
            taxes: [{ code: '01', rate: 19 }, { code: '04', rate: 8 }],
        });
        expect(line.taxAmount.toString()).toBe('27000'); // 19000 + 8000
        expect(line.total.toString()).toBe('127000');
    });

    it('el descuento nunca excede el bruto', () => {
        const line = computeLineTotals({ quantity: 1, price: 100, discount_amount: 999, taxes: [] });
        expect(line.discount.toString()).toBe('100');
        expect(line.taxable.toString()).toBe('0');
    });
});

describe('computeInvoiceTotals — totales de factura', () => {
    it('agrega varias líneas y arma el resumen de impuestos', () => {
        const totals = computeInvoiceTotals([
            { quantity: 1, price: 100000, taxes: [{ code: '01', rate: 19 }] },
            { quantity: 2, price: 50000, taxes: [{ code: '01', rate: 5 }] },
        ]);
        expect(totals.taxableAmount.toString()).toBe('200000');
        // IVA: 19% de 100000 = 19000; 5% de 100000 = 5000
        expect(totals.taxAmount.toString()).toBe('24000');
        expect(totals.total.toString()).toBe('224000');
        expect(totals.taxBreakdown).toHaveLength(2); // dos tarifas distintas
    });

    it('el total incluye el IVA (regresión del bug donde la UI mostraba subtotal sin IVA)', () => {
        const totals = computeInvoiceTotals([{ quantity: 1, price: 100000, taxes: [{ code: '01', rate: 19 }] }]);
        // El bug: la UI mostraba 100000; el correcto (y lo que certifica la DIAN) es 119000.
        expect(totals.total.toString()).toBe('119000');
        expect(totals.total.toString()).not.toBe('100000');
    });

    it('agrupa el breakdown por (código, tarifa)', () => {
        const totals = computeInvoiceTotals([
            { quantity: 1, price: 100000, taxes: [{ code: '01', rate: 19 }] },
            { quantity: 1, price: 200000, taxes: [{ code: '01', rate: 19 }] },
        ]);
        expect(totals.taxBreakdown).toHaveLength(1); // misma tarifa se agrupa
        expect(totals.taxBreakdown[0].taxAmount.toString()).toBe('57000'); // 19% de 300000
    });

    it('lista vacía da totales en cero sin lanzar', () => {
        const totals = computeInvoiceTotals([]);
        expect(totals.total.toString()).toBe('0');
        expect(totals.taxBreakdown).toHaveLength(0);
    });
});
