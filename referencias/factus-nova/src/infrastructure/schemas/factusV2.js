import { z } from 'zod';

/**
 * Esquemas Zod para las respuestas de Factus API v2.
 *
 * Objetivo: validar en runtime cada respuesta de la API. Si Factus cambia la
 * forma de un payload (como pasó de v1 a v2), esto lo convierte en un error
 * manejado y explícito en vez de corrupción silenciosa aguas abajo — el patrón
 * que hubiera detectado el cambio de versión de inmediato.
 *
 * Se usa `.passthrough()` para tolerar campos nuevos que Factus agregue sin
 * romper, validando solo lo que la app consume.
 * Ref: developers.factus.com.co/facturas/descripcion-de-campos
 */

/** Envoltura estándar de toda respuesta v2: { status, message, data }. */
export const apiEnvelope = (dataSchema) =>
    z.object({
        status: z.string().optional(),
        message: z.string().optional(),
        data: dataSchema,
    });

/** Respuesta del token OAuth. */
export const tokenResponse = z.object({
    token_type: z.string(),
    expires_in: z.number(),
    access_token: z.string().min(1),
    refresh_token: z.string().optional(),
});

/** Impuesto totalizado en la respuesta (data.taxes[] / items[].taxes[]). */
export const taxRate = z.object({
    taxable_amount: z.union([z.string(), z.number()]).optional(),
    tax_amount: z.union([z.string(), z.number()]).optional(),
    rate: z.union([z.string(), z.number()]).optional(),
}).passthrough();

/** Un ítem dentro de data.items. */
export const billItem = z.object({
    code_reference: z.string().optional(),
    name: z.string().optional(),
    quantity: z.union([z.string(), z.number()]).optional(),
    price: z.union([z.string(), z.number()]).optional(),
    total: z.union([z.string(), z.number()]).optional(),
    taxes: z.array(z.object({}).passthrough()).optional(),
}).passthrough();

/** Totales de la factura (data.totals). */
export const billTotals = z.object({
    gross_amount: z.union([z.string(), z.number()]).optional(),
    taxable_amount: z.union([z.string(), z.number()]).optional(),
    tax_amount: z.union([z.string(), z.number()]).optional(),
    total: z.union([z.string(), z.number()]),
}).passthrough();

/** Enlaces del documento (data.links). */
export const billLinks = z.object({
    qr: z.string().optional(),
    public_url: z.string().optional(),
}).passthrough();

/** data de una factura validada (POST /v2/bills/validate). */
export const validatedBill = z.object({
    reference_code: z.string().optional(),
    number: z.string().optional(),
    cufe: z.string().optional(),
    is_validated: z.boolean().optional(),
    validated_at: z.string().nullable().optional(),
    errors: z.union([z.object({}).passthrough(), z.array(z.any())]).optional(),
    created_at: z.string().optional(),
    items: z.array(billItem).optional(),
    totals: billTotals.optional(),
    links: billLinks.optional(),
}).passthrough();

/** Respuesta completa de crear/validar factura. */
export const validateBillResponse = apiEnvelope(validatedBill);

/**
 * Valida datos contra un esquema y devuelve un resultado discriminado, para que
 * la capa de repositorio decida cómo surfacer el error sin lanzar en caliente.
 * @template T
 * @param {import('zod').ZodType<T>} schema
 * @param {unknown} data
 * @returns {{ ok: true, data: T } | { ok: false, error: string, issues: unknown }}
 */
export function safeValidate(schema, data) {
    const result = schema.safeParse(data);
    if (result.success) return { ok: true, data: result.data };
    return {
        ok: false,
        error: 'La respuesta de la API no tiene la forma esperada (posible cambio de versión).',
        issues: result.error.issues,
    };
}
