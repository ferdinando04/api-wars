import { describe, it, expect, beforeEach } from 'vitest';
import { seal, unseal, buildSetCookie, buildClearCookie, readSession } from './session.js';

beforeEach(() => {
    process.env.SESSION_SECRET = 'test-secret-para-vitest-solamente-32bytes+';
});

describe('seal / unseal — sesión cifrada', () => {
    it('round-trip: descifra lo que cifró', () => {
        const session = { access_token: 'a', refresh_token: 'r', expires_at: 123 };
        expect(unseal(seal(session))).toEqual(session);
    });

    it('detecta manipulación (AES-GCM) y devuelve null', () => {
        const sealed = seal({ access_token: 'a' });
        const tampered = sealed.slice(0, -4) + 'AAAA';
        expect(unseal(tampered)).toBeNull();
    });

    it('un valor basura devuelve null en vez de lanzar', () => {
        expect(unseal('no-es-una-sesion')).toBeNull();
        expect(unseal('')).toBeNull();
    });

    it('una cookie sellada con otro secreto no se puede abrir', () => {
        const sealed = seal({ x: 1 });
        process.env.SESSION_SECRET = 'otro-secreto-completamente-distinto-abc';
        expect(unseal(sealed)).toBeNull();
    });
});

describe('cookies de sesión', () => {
    it('Set-Cookie incluye las banderas de seguridad requeridas', () => {
        const c = buildSetCookie('valor');
        expect(c).toContain('HttpOnly');
        expect(c).toContain('Secure');
        expect(c).toContain('SameSite=Strict');
        expect(c).toContain('Path=/');
    });

    it('buildClearCookie vence la cookie (Max-Age=0)', () => {
        expect(buildClearCookie()).toContain('Max-Age=0');
    });
});

describe('readSession', () => {
    it('lee la sesión desde el header Cookie', () => {
        const sealed = seal({ access_token: 'tok' });
        const req = { headers: { cookie: `other=1; fn_session=${sealed}; more=2` } };
        expect(readSession(req).access_token).toBe('tok');
    });

    it('devuelve null si no hay cookie de sesión', () => {
        expect(readSession({ headers: { cookie: 'other=1' } })).toBeNull();
        expect(readSession({ headers: {} })).toBeNull();
    });
});
