import { describe, it, expect } from 'vitest';
import { bogotaDate, addDays, parseFactusDate } from './datetime.js';

describe('bogotaDate — fecha en hora Colombia (UTC-5)', () => {
    it('a las 23:30 UTC del 2 jul, en Colombia sigue siendo el 2 jul (18:30)', () => {
        const nocheUTC = new Date('2026-07-02T23:30:00Z');
        expect(bogotaDate(nocheUTC)).toBe('2026-07-02');
    });

    it('a las 02:00 UTC del 3 jul, en Colombia todavía es el 2 jul (21:00)', () => {
        const madrugadaUTC = new Date('2026-07-03T02:00:00Z');
        expect(bogotaDate(madrugadaUTC)).toBe('2026-07-02');
    });

    it('formato YYYY-MM-DD', () => {
        expect(bogotaDate(new Date('2026-01-05T15:00:00Z'))).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
});

describe('addDays — suma de días sin desfase de zona', () => {
    it('suma 30 días cruzando fin de mes', () => {
        expect(addDays('2026-07-02', 30)).toBe('2026-08-01');
    });
    it('suma cruzando fin de año', () => {
        expect(addDays('2026-12-20', 30)).toBe('2027-01-19');
    });
});

describe('parseFactusDate — timestamps day-first de Factus', () => {
    it('parsea DD-MM-YYYY con día > 12 (que new Date rompería)', () => {
        const d = parseFactusDate('13-02-2025 05:20:09 PM');
        expect(d).not.toBeNull();
        expect(d.getFullYear()).toBe(2025);
        expect(d.getMonth()).toBe(1); // febrero (0-index)
        expect(d.getDate()).toBe(13);
        expect(d.getHours()).toBe(17); // 5 PM
    });

    it('parsea día <= 12 sin intercambiar día y mes', () => {
        const d = parseFactusDate('05-11-2025 09:00:00 AM');
        expect(d.getDate()).toBe(5); // día 5
        expect(d.getMonth()).toBe(10); // noviembre, NO mayo
    });

    it('12 AM se interpreta como medianoche (0h)', () => {
        const d = parseFactusDate('01-01-2026 12:00:00 AM');
        expect(d.getHours()).toBe(0);
    });

    it('entrada inválida devuelve null en vez de Invalid Date', () => {
        expect(parseFactusDate('no es fecha')).toBeNull();
        expect(parseFactusDate('')).toBeNull();
        expect(parseFactusDate(null)).toBeNull();
    });
});
