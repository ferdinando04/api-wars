import { describe, it, expect } from 'vitest';
import { toDecimal, roundMoney, sumMoney, toApiAmount, formatCOP } from './money.js';

describe('money — aritmética exacta', () => {
    it('evita el error clásico de flotantes 0.1 + 0.2', () => {
        expect(toDecimal('0.1').plus(toDecimal('0.2')).toString()).toBe('0.3');
    });

    it('entrada inválida o vacía se trata como 0 (no NaN)', () => {
        expect(toDecimal(undefined).toString()).toBe('0');
        expect(toDecimal('').toString()).toBe('0');
        expect(toDecimal('abc').toString()).toBe('0');
        expect(toDecimal(null).toString()).toBe('0');
    });

    it('suma exacta de una lista', () => {
        expect(sumMoney(['0.1', '0.2', '0.3']).toString()).toBe('0.6');
        expect(sumMoney([100000, 19000]).toString()).toBe('119000');
    });
});

describe('roundMoney — redondeo bancario (half-even) que exige la DIAN', () => {
    it('redondea al par más cercano en el punto medio, no siempre hacia arriba', () => {
        // half-up daría 2.35→2.4 y 2.45→2.5; half-even da 2.35→2.4 (par) y 2.45→2.4 (par)
        expect(roundMoney('2.345', 2).toString()).toBe('2.34'); // 4 es par
        expect(roundMoney('2.355', 2).toString()).toBe('2.36'); // 6 es par
        expect(roundMoney('0.5', 0).toString()).toBe('0'); // hacia el par (0)
        expect(roundMoney('1.5', 0).toString()).toBe('2'); // hacia el par (2)
        expect(roundMoney('2.5', 0).toString()).toBe('2'); // hacia el par (2)
    });
});

describe('toApiAmount / formatCOP — formato de salida', () => {
    it('toApiAmount da string con 2 decimales fijos', () => {
        expect(toApiAmount(100000)).toBe('100000.00');
        expect(toApiAmount('19000.005')).toBe('19000.00'); // half-even
    });

    it('formatCOP formatea en pesos colombianos', () => {
        expect(formatCOP(1190000)).toBe('$1.190.000');
        expect(formatCOP(1190000, { withSymbol: false })).toBe('1.190.000');
    });
});
