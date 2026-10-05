import { toApiAmount } from '../money.js';
import { computeInvoiceTotals } from '../tax.js';
import { bogotaDate } from '../datetime.js';
import { DEFAULTS } from '../catalogs.js';
import { calcularDV } from '../utils/dv.js';

/**
 * Mapper de Facturas — Factus API v2.
 *
 * Traduce el modelo de formulario de la UI al payload estricto de
 * `POST /v2/bills/validate`. Reemplaza al mapper v1, que quedó obsoleto por los
 * cambios breaking de la v2:
 *
 *   v1                         →  v2
 *   ─────────────────────────────────────────────────────────────
 *   payment_form + method_code →  payment_details: [ { ... } ]
 *   customer.identification_document_id (num) → identification_document_code (str)
 *   customer.legal_organization_id → legal_organization_code
 *   customer.tribute_id        →  tribute_code
 *   customer.municipality_id   →  municipality_code
 *   items[].tax_rate (num)     →  items[].taxes: [ { code, rate, is_excluded } ]
 *   items[].price (bruto)      →  items[].price (NETO, sin impuestos)
 *   items[].unit_measure_id    →  items[].unit_measure_code
 *   items[].standard_id        →  items[].standard_code
 *
 * Además: valida las cantidades (nunca las asume) y deriva fechas en hora Colombia.
 * Ref: developers.factus.com.co/buenas-practicas/cambios-v2-v1
 */

/**
 * Error de validación de dominio con detalles por campo, para que la UI muestre
 * mensajes útiles en vez de un 422 crudo de la API.
 */
export class InvoiceValidationError extends Error {
    /** @param {string} message @param {Record<string,string>} [fieldErrors] */
    constructor(message, fieldErrors = {}) {
        super(message);
        this.name = 'InvoiceValidationError';
        this.fieldErrors = fieldErrors;
    }
}

/**
 * Normaliza los impuestos de un ítem del formulario al array `taxes` de v2.
 * Acepta: un `iva_rate` numérico (atajo de la UI) o un array `taxes` ya armado.
 * @param {object} item
 * @returns {Array<{code:string, rate:string, is_excluded?:boolean}>}
 */
function buildItemTaxes(item) {
    if (Array.isArray(item.taxes) && item.taxes.length > 0) {
        return item.taxes.map((t) => {
            if (t.is_excluded) return { code: t.code || DEFAULTS.tax_code, rate: '0', is_excluded: true };
            return { code: t.code || DEFAULTS.tax_code, rate: String(t.rate ?? 0) };
        });
    }
    // Atajo: la UI envía un iva_rate. -1 (o is_excluded) => excluido.
    const rate = item.iva_rate ?? item.tax_rate ?? DEFAULTS.iva_rate;
    if (item.is_excluded === true || Number(rate) < 0) {
        return [{ code: DEFAULTS.tax_code, rate: '0', is_excluded: true }];
    }
    return [{ code: DEFAULTS.tax_code, rate: String(rate) }];
}

/**
 * Valida un ítem y lanza si la cantidad o el precio son inválidos.
 * Esto cierra el bug crítico donde una cantidad vacía se emitía como 1.
 * @param {object} item @param {number} index
 */
function validateItem(item, index) {
    const qty = Number(item.quantity);
    if (!Number.isFinite(qty) || qty <= 0) {
        throw new InvoiceValidationError(
            `El ítem ${index + 1} tiene una cantidad inválida.`,
            { [`items.${index}.quantity`]: 'La cantidad debe ser un número mayor que 0.' }
        );
    }
    const price = Number(item.price);
    if (!Number.isFinite(price) || price < 0) {
        throw new InvoiceValidationError(
            `El ítem ${index + 1} tiene un precio inválido.`,
            { [`items.${index}.price`]: 'El precio debe ser un número mayor o igual a 0.' }
        );
    }
}

/**
 * Construye el payload de `POST /v2/bills/validate`.
 * @param {object} formData Modelo del formulario de la UI.
 * @param {object} [options]
 * @param {number|string} [options.numberingRangeId] Solo necesario si hay múltiples rangos activos (v2 lo hace opcional).
 * @param {Date} [options.now] Inyectable para tests deterministas.
 * @returns {object} Payload v2.
 */
export function toFactusV2Payload(formData, options = {}) {
    const items = Array.isArray(formData?.items) ? formData.items : [];
    if (items.length === 0) {
        throw new InvoiceValidationError('La factura debe tener al menos un ítem.', {
            items: 'Añade al menos un producto o servicio.',
        });
    }
    items.forEach(validateItem);

    const now = options.now instanceof Date ? options.now : new Date();
    const today = bogotaDate(now);

    const identification = String(formData.customer_identification ?? '').trim();
    const isNit = String(formData.customer_identification_document_code || DEFAULTS.identification_document_code) === '31';

    // Fuente única de verdad de los impuestos: se normaliza una vez y se reusa
    // tanto para el payload (items[].taxes) como para el cálculo de totales.
    const itemsWithTaxes = items.map((item) => ({ item, taxes: buildItemTaxes(item) }));

    const payload = {
        reference_code: formData.reference_code || `FN-${today}-${(formData.reference_seq ?? '').toString() || cryptoSeq()}`,
        observation: formData.observation || '',
        payment_details: buildPaymentDetails(formData, today),
        customer: {
            identification_document_code:
                formData.customer_identification_document_code || DEFAULTS.identification_document_code,
            identification,
            ...(isNit ? { dv: formData.customer_dv || calcularDV(identification) } : {}),
            legal_organization_code:
                formData.customer_legal_organization_code || DEFAULTS.legal_organization_code,
            tribute_code: formData.customer_tribute_code || DEFAULTS.tribute_code,
            company: formData.customer_company || '',
            trade_name: formData.customer_trade_name || '',
            names: formData.customer_names || '',
            address: formData.customer_address || '',
            email: formData.customer_email || '',
            phone: String(formData.customer_phone || ''),
            ...(formData.customer_municipality_code
                ? { municipality_code: String(formData.customer_municipality_code) }
                : {}),
        },
        items: itemsWithTaxes.map(({ item, taxes }) => ({
            code_reference: item.code_reference || `REF-${item.id ?? ''}` || 'REF',
            name: item.name || 'Producto',
            quantity: String(item.quantity),
            ...(item.discount_rate ? { discount_rate: String(item.discount_rate) } : {}),
            ...(item.discount_amount ? { discount_amount: toApiAmount(item.discount_amount) } : {}),
            price: toApiAmount(item.price), // v2: precio NETO
            unit_measure_code: item.unit_measure_code || DEFAULTS.unit_measure_code,
            standard_code: item.standard_code || DEFAULTS.standard_code,
            taxes,
        })),
    };

    if (options.numberingRangeId) {
        payload.numbering_range_id = options.numberingRangeId;
    }

    // Totales calculados localmente (exactos, half-even) para que la UI muestre
    // el mismo número que certificará la DIAN. No van en el payload — Factus los
    // recalcula — pero se devuelven aparte para la vista de confirmación.
    // Se usan los mismos taxes normalizados que van en el payload (fuente única).
    const totals = computeInvoiceTotals(
        itemsWithTaxes.map(({ item, taxes }) => ({
            quantity: item.quantity,
            price: item.price,
            discount_rate: item.discount_rate,
            discount_amount: item.discount_amount,
            taxes: taxes.map((t) => ({ code: t.code, rate: t.rate, is_excluded: t.is_excluded })),
        }))
    );

    return { payload, totals };
}

function buildPaymentDetails(formData, today) {
    const paymentForm = formData.payment_form || DEFAULTS.payment_form;
    const detail = {
        payment_form: paymentForm,
        payment_method_code: formData.payment_method_code || DEFAULTS.payment_method_code,
    };
    if (formData.payment_reference_code) detail.reference_code = formData.payment_reference_code;
    // due_date obligatorio solo en pago a crédito (payment_form = 2).
    if (paymentForm === '2') {
        detail.due_date = formData.payment_due_date || today;
    }
    return [detail];
}

/** Secuencia pseudo-única para reference_code cuando la UI no aporta una. */
function cryptoSeq() {
    if (typeof globalThis.crypto?.randomUUID === 'function') {
        return globalThis.crypto.randomUUID().slice(0, 8);
    }
    return Math.abs(Date.now() % 1e8).toString();
}
