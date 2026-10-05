import Decimal from 'decimal.js';

/**
 * Capa de dinero exacta para facturación DIAN.
 *
 * Regla de oro: NUNCA usar `Number` para aritmética monetaria — los flotantes
 * IEEE-754 rompen los totales (0.1 + 0.2 !== 0.3). Todo el cálculo fiscal pasa
 * por Decimal.js.
 *
 * Redondeo: la DIAN exige redondeo bancario (half-even / "round half to even"),
 * alineado a la norma NTC 3711. Es distinto del half-up que aproxima `toFixed`.
 * Ref: Anexo Técnico Factura Electrónica de Venta (DIAN).
 */

// Configuración global e inmutable de Decimal: 20 dígitos de precisión y
// redondeo bancario por defecto, coherente con el validador de la DIAN.
Decimal.set({ precision: 20, rounding: Decimal.ROUND_HALF_EVEN });

/** Decimales estándar de un campo monetario en la factura DIAN. */
export const MONEY_DP = 2;

/**
 * Convierte cualquier entrada (string | number | Decimal) a Decimal de forma
 * segura. Una entrada inválida o vacía se trata como 0 en vez de NaN.
 * @param {string|number|Decimal|null|undefined} value
 * @returns {Decimal}
 */
export function toDecimal(value) {
    if (value instanceof Decimal) return value;
    if (value === null || value === undefined || value === '') return new Decimal(0);
    try {
        const d = new Decimal(value);
        return d.isNaN() ? new Decimal(0) : d;
    } catch {
        return new Decimal(0);
    }
}

/**
 * Redondea un valor a `dp` decimales usando redondeo bancario (half-even),
 * como exige la DIAN.
 * @param {string|number|Decimal} value
 * @param {number} [dp=MONEY_DP]
 * @returns {Decimal}
 */
export function roundMoney(value, dp = MONEY_DP) {
    return toDecimal(value).toDecimalPlaces(dp, Decimal.ROUND_HALF_EVEN);
}

/**
 * Suma exacta de una lista de valores monetarios.
 * @param {Array<string|number|Decimal>} values
 * @returns {Decimal}
 */
export function sumMoney(values) {
    let acc = new Decimal(0);
    for (const v of values || []) acc = acc.plus(toDecimal(v));
    return acc;
}

/**
 * Convierte un Decimal a string con punto decimal fijo (formato que espera la
 * API de Factus para los campos monetarios: máximo dos decimales, sin separador
 * de miles).
 * @param {string|number|Decimal} value
 * @param {number} [dp=MONEY_DP]
 * @returns {string}
 */
export function toApiAmount(value, dp = MONEY_DP) {
    return roundMoney(value, dp).toFixed(dp);
}

/**
 * Formatea un valor para mostrar en la UI en pesos colombianos.
 * @param {string|number|Decimal} value
 * @param {object} [opts]
 * @param {boolean} [opts.withSymbol=true] Incluir el prefijo "$".
 * @param {number} [opts.dp=0] Decimales a mostrar (COP suele mostrarse sin decimales).
 * @returns {string}
 */
export function formatCOP(value, { withSymbol = true, dp = 0 } = {}) {
    const rounded = roundMoney(value, dp);
    const formatted = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: dp,
        maximumFractionDigits: dp,
    }).format(rounded.toNumber());
    return withSymbol ? `$${formatted}` : formatted;
}

export { Decimal };
