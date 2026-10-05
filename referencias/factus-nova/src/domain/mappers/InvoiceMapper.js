/**
 * Mapper de Facturas (Paso C - Preparación del Payload)
 * Centraliza la lógica de transformación: de Formulario React -> al esquema estricto de Factus API v1.
 */
export class InvoiceMapper {
    /**
     * Transforma los datos crudos en el payload oficial.
     * @param {Object} formData Datos estructurados en la UI (React Hook Form)
     * @param {number|string} numberingRangeId El ID del rango obtenido de Factus (Paso B)
     * @returns {Object} JSON estricto que espera la API
     */
    static toFactusPayload(formData, numberingRangeId) {
        const today = new Date();
        const startDate = today.toISOString().split('T')[0];

        // end_date DEBE ser posterior a start_date (Factus requiere mínimo 1 día después)
        const endDate = new Date(today);
        endDate.setDate(endDate.getDate() + 30); // 30 días de vigencia
        const endDateStr = endDate.toISOString().split('T')[0];

        return {
            numbering_range_id: numberingRangeId,
            reference_code: formData.reference_code || `FAC_${Date.now()}`,
            observation: formData.observation || "Factura generada desde Factus Nova",
            payment_form: formData.payment_form || "1", // 1 = Contado
            payment_due_date: endDateStr,
            payment_method_code: formData.payment_method_code || "10", // 10 = Efectivo
            billing_period: {
                start_date: startDate,
                start_time: "00:00:00",
                end_date: endDateStr,
                end_time: "23:59:59"
            },
            customer: {
                identification: String(formData.customer_identification),
                dv: formData.customer_dv || "0",
                company: formData.customer_company || formData.customer_names || "",
                trade_name: formData.customer_trade_name || "",
                names: formData.customer_names || "",
                address: formData.customer_address || "Sin dirección",
                email: formData.customer_email || "sin@email.com",
                phone: String(formData.customer_phone || "0000000000"),
                legal_organization_id: formData.customer_legal_organization_id || "2", // 2=Natural
                tribute_id: formData.customer_tribute_id || "21",
                identification_document_id: formData.customer_identification_document_id || "3", // 3=C.C.
                municipality_id: formData.customer_municipality_id || 169
            },
            items: formData.items.map(item => ({
                code_reference: item.code_reference || `REF${Date.now()}`,
                name: item.name || "Producto",
                quantity: Number(item.quantity) || 1,
                discount_rate: Number(item.discount_rate) || 0,
                price: Number(item.price) || 0,
                tax_rate: item.tax_rate || "19.00",
                unit_measure_id: item.unit_measure_id || 70, // 70 = Unidad
                standard_code_id: item.standard_code_id || 1,
                is_excluded: item.is_excluded || 0,
                tribute_id: item.tribute_id || 1, // 1 = IVA
                withholding_taxes: []
            }))
        };
    }
}
