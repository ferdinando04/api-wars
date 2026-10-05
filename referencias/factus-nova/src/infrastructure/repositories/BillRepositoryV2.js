import { FactusClientV2 } from '../http/factusClientV2.js';
import { validateBillResponse } from '../schemas/factusV2.js';
import { toFactusV2Payload } from '../../domain/mappers/InvoiceMapperV2.js';
import { newIdempotencyKey, referenceCodeFromKey } from '../../domain/idempotency.js';
import { logger } from '../observability/logger.js';

/**
 * Repositorio de Facturas — Factus API v2, vía BFF.
 *
 * Sustituye a InvoiceRepository (v1). Orquesta el caso de uso de emisión:
 *  1. Deriva un reference_code estable de una Idempotency-Key (evita doble
 *     facturación en reintentos).
 *  2. Construye el payload v2 con el mapper (que valida cantidades).
 *  3. Llama al cliente v2 (que habla solo con el BFF y valida la respuesta con Zod).
 *
 * El cliente es inyectable para tests.
 */
export class BillRepositoryV2 {
    /** @param {FactusClientV2} [client] */
    constructor(client) {
        this._client = client || new FactusClientV2();
    }

    /**
     * Emite y valida una factura ante la DIAN.
     * @param {object} formData Modelo del formulario de la UI.
     * @param {object} [options]
     * @param {string} [options.idempotencyKey] Reusar en reintentos del mismo submit.
     * @param {number|string} [options.numberingRangeId]
     * @returns {Promise<{data: object, totals: object, idempotencyKey: string}>}
     */
    async emitir(formData, options = {}) {
        const idempotencyKey = options.idempotencyKey || newIdempotencyKey();
        const referenceCode = referenceCodeFromKey(idempotencyKey);

        const { payload, totals } = toFactusV2Payload(
            { ...formData, reference_code: formData.reference_code || referenceCode },
            { numberingRangeId: options.numberingRangeId }
        );

        try {
            const response = await this._client.validateBill(payload, {
                idempotencyKey,
                schema: validateBillResponse,
            });
            return { data: response.data, totals, idempotencyKey };
        } catch (error) {
            logger.captureException(error, { where: 'BillRepositoryV2.emitir', referenceCode });
            throw error;
        }
    }

    /**
     * Lista facturas paginadas.
     * @param {number} [page=1]
     * @param {number} [perPage=10]
     */
    async listar(page = 1, perPage = 10) {
        const response = await this._client.listBills({ page, perPage });
        // La respuesta paginada de Factus: { data: { data: [...], pagination } } o similar.
        const data = response?.data ?? response;
        return {
            bills: Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : [],
            pagination: data?.pagination ?? response?.pagination ?? null,
        };
    }
}

/** Instancia por defecto (usa el BFF en /api/factus). */
export const billRepositoryV2 = new BillRepositoryV2();
