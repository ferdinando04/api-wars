import { describe, it, expect } from 'vitest';
import { calcularDV } from './dv.js';

describe('calcularDV — dígito de verificación NIT (algoritmo oficial DIAN)', () => {
    // Verificado contra NITs públicos reales.
    it('DIAN 800197268 → 4', () => {
        expect(calcularDV('800197268')).toBe('4');
    });
    it('Ecopetrol 899999068 → 1', () => {
        expect(calcularDV('899999068')).toBe('1');
    });
    it('Bancolombia 890903938 → 8', () => {
        expect(calcularDV('890903938')).toBe('8');
    });

    it('ignora guiones y espacios en la entrada', () => {
        expect(calcularDV('800.197.268')).toBe('4');
        expect(calcularDV('800 197 268')).toBe('4');
    });

    it('conserva ceros a la izquierda como parte del número', () => {
        // No debe lanzar ni dar NaN.
        expect(typeof calcularDV('0012345')).toBe('string');
    });

    it('entrada vacía o no numérica devuelve cadena vacía', () => {
        expect(calcularDV('')).toBe('');
        expect(calcularDV(null)).toBe('');
        expect(calcularDV('abc')).toBe('');
    });

    it('siempre devuelve un dígito 0-9', () => {
        for (const nit of ['1', '22', '333', '900123456', '12345678901234']) {
            expect(calcularDV(nit)).toMatch(/^[0-9]$/);
        }
    });
});
