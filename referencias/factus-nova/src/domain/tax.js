import { toDecimal, roundMoney, Decimal } from './money.js';

/**
 * Motor de cálculo fiscal — Factus API v2.
 *
 * Semántica v2 (¡cambió respecto a v1!):
 *  - `items[].price` es el precio unitario NETO, sin impuestos ni descuento.
 *    (En v1 el precio era bruto con impuestos incluidos.)
 *  - Los impuestos van en `items[].taxes[]` como array de { code, rate, is_excluded },
 *    permitiendo múltiples tributos por ítem (IVA + INC, etc.).
 *  - Un ítem excluido lleva `is_excluded: true` (no causa impuesto).
 *  - Un ítem exento es rate 0 (causa base gravable pero impuesto 0).
 *
 * Redondeo: half-even por línea, luego se suma — así el total coincide con el
 * que calcula el validador de la DIAN (ver money.js).
 * Ref: developers.factus.com.co/buenas-practicas/cambios-v2-v1
 */

/**
 * @typedef {Object} TaxSpec
 * @property {string} code   Código del impuesto DIAN (p.ej. "01" = IVA).
 * @property {number|string} rate Porcentaje (p.ej. 19).
 * @property {boolean} [is_excluded] El ítem está excluido de este impuesto.
 */

/**
 * @typedef {Object} InvoiceItemInput
 * @property {number|string} quantity
 * @property {number|string} price          Precio unitario NETO (sin impuestos).
 * @property {number|string} [discount_rate] Descuento en % (0-100).
 * @property {number|string} [discount_amount] Descuento en monto absoluto (alternativo a discount_rate).
 * @property {TaxSpec[]} [taxes]
 */

/**
 * @typedef {Object} LineTotals
 * @property {Decimal} gross     Precio neto × cantidad, antes de descuento.
 * @property {Decimal} discount  Monto del descuento aplicado.
 * @property {Decimal} taxable   Base gravable (gross − discount).
 * @property {Decimal} taxAmount Suma de impuestos de la línea (redondeada por tributo).
 * @property {Decimal} total     taxable + taxAmount.
 * @property {Array<{code:string, rate:Decimal, taxable:Decimal, amount:Decimal, isExcluded:boolean}>} taxes
 */

/**
 * Calcula los totales de una sola línea de la factura.
 * @param {InvoiceItemInput} item
 * @returns {LineTotals}
 */
export function computeLineTotals(item) {
    const quantity = toDecimal(item?.quantity);
    const price = toDecimal(item?.price);
    const gross = roundMoney(price.times(quantity));

    // Descuento: por porcentaje o por monto absoluto (v2 acepta cualquiera).
    let discount = new Decimal(0);
    if (item?.discount_amount !== undefined && item?.discount_amount !== '' && item?.discount_amount !== null) {
        discount = roundMoney(item.discount_amount);
    } else if (item?.discount_rate) {
        discount = roundMoney(gross.times(toDecimal(item.discount_rate)).dividedBy(100));
    }
    if (discount.greaterThan(gross)) discount = gross; // el descuento no puede exceder el bruto

    const taxable = roundMoney(gross.minus(discount));

    const taxes = (item?.taxes || []).map((t) => {
        const rate = toDecimal(t?.rate);
        const isExcluded = t?.is_excluded === true;
        // Excluido: no causa impuesto. Exento (rate 0): base gravable con impuesto 0.
        const amount = isExcluded ? new Decimal(0) : roundMoney(taxable.times(rate).dividedBy(100));
        return { code: t?.code ?? '', rate, taxable, amount, isExcluded };
    });

    const taxAmount = taxes.reduce((acc, t) => acc.plus(t.amount), new Decimal(0));
    const total = roundMoney(taxable.plus(taxAmount));

    return { gross, discount, taxable, taxAmount, total, taxes };
}

/**
 * @typedef {Object} InvoiceTotals
 * @property {Decimal} grossAmount   Suma de los brutos de línea.
 * @property {Decimal} discountAmount Suma de descuentos de línea.
 * @property {Decimal} taxableAmount Base gravable total.
 * @property {Decimal} taxAmount     Impuesto total.
 * @property {Decimal} total         Total a pagar (taxable + tax).
 * @property {Array<{code:string, rate:string, taxableAmount:Decimal, taxAmount:Decimal}>} taxBreakdown
 *           Resumen de impuestos agrupado por (código, tarifa), como en data.taxes de la respuesta v2.
 * @property {LineTotals[]} lines
 */

/**
 * Calcula los totales de la factura completa a partir de sus ítems.
 * Replica la forma en que la DIAN/Factus totalizan: impuesto por línea
 * (redondeado), luego agregación.
 * @param {InvoiceItemInput[]} items
 * @returns {InvoiceTotals}
 */
export function computeInvoiceTotals(items) {
    const lines = (items || []).map(computeLineTotals);

    const grossAmount = lines.reduce((a, l) => a.plus(l.gross), new Decimal(0));
    const discountAmount = lines.reduce((a, l) => a.plus(l.discount), new Decimal(0));
    const taxableAmount = lines.reduce((a, l) => a.plus(l.taxable), new Decimal(0));
    const taxAmount = lines.reduce((a, l) => a.plus(l.taxAmount), new Decimal(0));
    const total = roundMoney(taxableAmount.plus(taxAmount));

    // Resumen por (código de impuesto, tarifa) — equivalente a data.taxes v2.
    /** @type {Map<string, {code:string, rate:string, taxableAmount:Decimal, taxAmount:Decimal}>} */
    const breakdown = new Map();
    for (const line of lines) {
        for (const t of line.taxes) {
            if (t.isExcluded) continue;
            const key = `${t.code}|${t.rate.toString()}`;
            const entry = breakdown.get(key) || {
                code: t.code,
                rate: t.rate.toString(),
                taxableAmount: new Decimal(0),
                taxAmount: new Decimal(0),
            };
            entry.taxableAmount = entry.taxableAmount.plus(t.taxable);
            entry.taxAmount = entry.taxAmount.plus(t.amount);
            breakdown.set(key, entry);
        }
    }

    return {
        grossAmount,
        discountAmount,
        taxableAmount,
        taxAmount,
        total,
        taxBreakdown: Array.from(breakdown.values()),
        lines,
    };
}
