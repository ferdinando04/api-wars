import { describe, it, expect } from 'vitest';
import { toFactusV2Payload, InvoiceValidationError } from './InvoiceMapperV2.js';

const baseForm = {
    customer_identification: '1234567890',
    customer_names: 'Juan Pérez',
    customer_email: 'juan@example.com',
    items: [{ name: 'Servicio', quantity: 1, price: 100000, iva_rate: 19 }],
};

const NOW = new Date('2026-07-02T15:00:00Z'); // 10:00 Bogotá

describe('toFactusV2Payload — estructura v2', () => {
    it('produce payment_details como array (no payment_form/method sueltos de v1)', () => {
        const { payload } = toFactusV2Payload(baseForm, { now: NOW });
        expect(Array.isArray(payload.payment_details)).toBe(true);
        expect(payload.payment_details[0]).toMatchObject({ payment_form: '1', payment_method_code: '10' });
        expect(payload).not.toHaveProperty('payment_form');
        expect(payload).not.toHaveProperty('payment_method_code');
    });

    it('el cliente usa los campos *_code de v2', () => {
        const { payload } = toFactusV2Payload(baseForm, { now: NOW });
        expect(payload.customer).toHaveProperty('identification_document_code');
        expect(payload.customer).toHaveProperty('legal_organization_code');
        expect(payload.customer).toHaveProperty('tribute_code');
        expect(payload.customer).not.toHaveProperty('identification_document_id');
        expect(payload.customer).not.toHaveProperty('tribute_id');
    });

    it('los items usan taxes[] array y unit_measure_code/standard_code', () => {
        const { payload } = toFactusV2Payload(baseForm, { now: NOW });
        const item = payload.items[0];
        expect(Array.isArray(item.taxes)).toBe(true);
        expect(item.taxes[0]).toMatchObject({ code: '01', rate: '19' });
        expect(item).toHaveProperty('unit_measure_code');
        expect(item).toHaveProperty('standard_code');
        expect(item).not.toHaveProperty('tax_rate');
        expect(item).not.toHaveProperty('unit_measure_id');
    });

    it('price se envía como string neto con 2 decimales', () => {
        const { payload } = toFactusV2Payload(baseForm, { now: NOW });
        expect(payload.items[0].price).toBe('100000.00');
    });

    it('un ítem excluido produce taxes con is_excluded', () => {
        const form = { ...baseForm, items: [{ name: 'Libro', quantity: 1, price: 50000, is_excluded: true }] };
        const { payload } = toFactusV2Payload(form, { now: NOW });
        expect(payload.items[0].taxes[0]).toMatchObject({ is_excluded: true, rate: '0' });
    });

    it('envía dv solo cuando el documento es NIT (código 31)', () => {
        const nitForm = { ...baseForm, customer_identification_document_code: '31', customer_identification: '900123456' };
        const { payload } = toFactusV2Payload(nitForm, { now: NOW });
        expect(payload.customer).toHaveProperty('dv');

        const ccForm = { ...baseForm, customer_identification_document_code: '13' };
        const { payload: ccPayload } = toFactusV2Payload(ccForm, { now: NOW });
        expect(ccPayload.customer).not.toHaveProperty('dv');
    });

    it('numbering_range_id solo se incluye si se pasa (v2 lo hace opcional)', () => {
        const { payload: sinRango } = toFactusV2Payload(baseForm, { now: NOW });
        expect(sinRango).not.toHaveProperty('numbering_range_id');
        const { payload: conRango } = toFactusV2Payload(baseForm, { now: NOW, numberingRangeId: 8 });
        expect(conRango.numbering_range_id).toBe(8);
    });

    it('pago a crédito (form 2) agrega due_date', () => {
        const form = { ...baseForm, payment_form: '2' };
        const { payload } = toFactusV2Payload(form, { now: NOW });
        expect(payload.payment_details[0]).toHaveProperty('due_date');
    });
});

describe('toFactusV2Payload — validación (cierra bugs fiscales)', () => {
    it('REGRESIÓN C1: una cantidad vacía/NaN es rechazada, NO emitida como 1', () => {
        const form = { ...baseForm, items: [{ name: 'X', quantity: '', price: 100000 }] };
        expect(() => toFactusV2Payload(form, { now: NOW })).toThrow(InvoiceValidationError);
    });

    it('rechaza cantidad cero o negativa', () => {
        expect(() => toFactusV2Payload({ ...baseForm, items: [{ name: 'X', quantity: 0, price: 1 }] }, { now: NOW })).toThrow();
        expect(() => toFactusV2Payload({ ...baseForm, items: [{ name: 'X', quantity: -2, price: 1 }] }, { now: NOW })).toThrow();
    });

    it('rechaza precio inválido', () => {
        expect(() => toFactusV2Payload({ ...baseForm, items: [{ name: 'X', quantity: 1, price: 'abc' }] }, { now: NOW })).toThrow();
    });

    it('rechaza factura sin ítems', () => {
        expect(() => toFactusV2Payload({ ...baseForm, items: [] }, { now: NOW })).toThrow(InvoiceValidationError);
    });

    it('el error de validación expone fieldErrors para la UI', () => {
        try {
            toFactusV2Payload({ ...baseForm, items: [{ name: 'X', quantity: '', price: 1 }] }, { now: NOW });
        } catch (e) {
            expect(e).toBeInstanceOf(InvoiceValidationError);
            expect(e.fieldErrors).toHaveProperty('items.0.quantity');
        }
    });
});

describe('toFactusV2Payload — totales y fechas', () => {
    it('devuelve totals con IVA incluido, coincidiendo con lo que certifica la DIAN', () => {
        const { totals } = toFactusV2Payload(baseForm, { now: NOW });
        expect(totals.total.toString()).toBe('119000');
    });

    it('el reference_code por defecto usa la fecha de Colombia', () => {
        const { payload } = toFactusV2Payload(baseForm, { now: NOW });
        expect(payload.reference_code).toContain('2026-07-02');
    });
});
