import { axiosClient } from '../http/axiosClient';

/**
 * Repositorio para la gestión de Rangos de Numeración.
 * Obtiene el ID del rango activo para la facturación.
 */
export class NumberingRangeRepository {
    async getActiveRangeId() {
        try {
            const response = await axiosClient.get('/v1/numbering-ranges');

            let ranges = [];
            if (Array.isArray(response)) {
                ranges = response;
            } else if (response?.data?.data && Array.isArray(response.data.data)) {
                ranges = response.data.data;
            } else if (response?.data && Array.isArray(response.data)) {
                ranges = response.data;
            } else if (Array.isArray(response?.data)) {
                ranges = response.data;
            }

            // PRIORIDAD 1: Buscar "Factura de Venta" activa
            const invoiceRange = ranges.find(r =>
                r.document === 'Factura de Venta' &&
                (r.is_active === 1 || r.is_active === true)
            );
            if (invoiceRange) return invoiceRange.id;

            // PRIORIDAD 2: Buscar por prefijo SETP/SETT (sandbox)
            const fallback = ranges.find(r =>
                (r.prefix === 'SETP' || r.prefix === 'SETT') &&
                (r.is_active === 1 || r.is_active === true)
            );
            if (fallback) return fallback.id;

            // PRIORIDAD 3: Cualquier rango activo que no sea Nota/Ajuste
            if (ranges.length > 0) {
                const any = ranges.find(r =>
                    !r.document?.includes('Nota') &&
                    !r.document?.includes('Ajuste') &&
                    (r.is_active === 1 || r.is_active === true)
                );
                if (any) return any.id;
                return ranges[0].id;
            }

            throw new Error('No se encontró ningún rango de numeración activo.');
        } catch (error) {
            throw new Error(`Fallo al obtener rangos: ${error.message}`);
        }
    }
}

export const numberingRangeRepository = new NumberingRangeRepository();
