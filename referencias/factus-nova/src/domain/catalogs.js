/**
 * Catálogos de referencia DIAN — Factus API v2.
 *
 * En v2 los campos pasaron de `*_id` (numérico) a `*_code` (string), y Factus
 * publica las tablas completas para que el integrador mapee código→descripción
 * sin llamar endpoints extra. Aquí van los subconjuntos que la app usa.
 * Ref: developers.factus.com.co/tablas-de-referencia
 */

/** Tipos de documento de identidad del cliente (customer.identification_document_code). */
export const IDENTIFICATION_DOCUMENTS = [
    { code: '11', name: 'Registro civil' },
    { code: '12', name: 'Tarjeta de identidad' },
    { code: '13', name: 'Cédula de ciudadanía' },
    { code: '21', name: 'Tarjeta de extranjería' },
    { code: '22', name: 'Cédula de extranjería' },
    { code: '31', name: 'NIT' },
    { code: '41', name: 'Pasaporte' },
    { code: '42', name: 'Documento de identificación extranjero' },
    { code: '50', name: 'NIT de otro país' },
    { code: '91', name: 'NUIP' },
];

/** Tipos de organización (customer.legal_organization_code). */
export const LEGAL_ORGANIZATIONS = [
    { code: '1', name: 'Persona Jurídica' },
    { code: '2', name: 'Persona Natural' },
];

/** Tributos del cliente (customer.tribute_code). ZZ = No aplica (default). */
export const CUSTOMER_TRIBUTES = [
    { code: '18', name: 'IVA' },
    { code: '21', name: 'No responsable de IVA' },
    { code: 'ZZ', name: 'No aplica' },
    { code: 'ZA', name: 'IVA e INC' },
];

/** Códigos de impuestos a nivel de ítem (items[].taxes[].code). */
export const TAX_CODES = [
    { code: '01', name: 'IVA' },
    { code: '02', name: 'IC (Impuesto al consumo)' },
    { code: '03', name: 'ICA' },
    { code: '04', name: 'INC' },
];

/** Tarifas de IVA vigentes en Colombia. */
export const IVA_RATES = [
    { rate: 19, label: 'IVA 19%' },
    { rate: 5, label: 'IVA 5%' },
    { rate: 0, label: 'Exento (0%)' },
    { rate: -1, label: 'Excluido', excluded: true },
];

/** Formas de pago (payment_details[].payment_form). */
export const PAYMENT_FORMS = [
    { code: '1', name: 'Pago de contado' },
    { code: '2', name: 'Pago a crédito' },
];

/** Métodos de pago (payment_details[].payment_method_code) — subconjunto común. */
export const PAYMENT_METHODS = [
    { code: '10', name: 'Efectivo' },
    { code: '42', name: 'Consignación' },
    { code: '47', name: 'Transferencia' },
    { code: '48', name: 'Tarjeta crédito' },
    { code: '49', name: 'Tarjeta débito' },
];

/** Unidades de medida (items[].unit_measure_code) — subconjunto común. */
export const UNIT_MEASURES = [
    { code: '70', name: 'Unidad' },
    { code: '94', name: 'Unidad (bienes)' },
    { code: 'WHR', name: 'Hora de trabajo' },
    { code: 'KGM', name: 'Kilogramo' },
    { code: 'MTR', name: 'Metro' },
];

/** Código de estándar del producto (items[].standard_code). 999 = adopción del contribuyente. */
export const STANDARD_CODES = [
    { code: '999', name: 'Estándar de adopción del contribuyente' },
    { code: '010', name: 'UNSPSC' },
    { code: '020', name: 'GTIN' },
];

// Defaults usados por el mapper cuando la UI aún no captura estos campos.
export const DEFAULTS = Object.freeze({
    identification_document_code: '13', // Cédula de ciudadanía
    legal_organization_code: '2', // Persona Natural
    tribute_code: 'ZZ', // No aplica
    unit_measure_code: '70', // Unidad
    standard_code: '999', // Adopción del contribuyente
    tax_code: '01', // IVA
    iva_rate: 19,
    payment_form: '1', // Contado
    payment_method_code: '10', // Efectivo
});
