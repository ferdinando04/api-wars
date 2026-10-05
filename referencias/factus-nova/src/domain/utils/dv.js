/**
 * Calcula el Dígito de Verificación (DV) de un NIT colombiano.
 * Algoritmo oficial DIAN — factores primos aplicados de derecha a izquierda.
 * Ref: https://www.dian.gov.co
 */
const FACTORES = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71];

export function calcularDV(nit) {
    const digits = String(nit || '').replace(/\D/g, '');
    if (!digits) return '';
    let suma = 0;
    const reversed = digits.split('').reverse();
    for (let i = 0; i < reversed.length && i < FACTORES.length; i++) {
        suma += parseInt(reversed[i]) * FACTORES[i];
    }
    const residuo = suma % 11;
    return String(residuo <= 1 ? residuo : 11 - residuo);
}
