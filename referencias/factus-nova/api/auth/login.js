import { passwordGrant } from '../_lib/factus.js';
import { seal, buildSetCookie } from '../_lib/session.js';

/**
 * POST /api/auth/login — BFF login.
 *
 * El navegador NO envía credenciales de Factus: el BFF ya las tiene como env
 * vars de servidor. Este endpoint solo dispara el grant, y devuelve una cookie
 * de sesión cifrada (httpOnly). El SPA nunca ve ningún token.
 *
 * En un modelo multi-usuario real, aquí se validaría al usuario de la app
 * (email/password propios) antes de emitir la sesión; el grant de Factus usa las
 * credenciales de la empresa emisora.
 */
export default async function handler(req, res) {
    if (req.method !== 'POST') {
        res.setHeader('Allow', 'POST');
        return res.status(405).json({ error: 'Método no permitido' });
    }
    try {
        const tokens = await passwordGrant();
        const session = {
            access_token: tokens.access_token,
            refresh_token: tokens.refresh_token,
            // expira un poco antes que el token real para refrescar con margen
            expires_at: Date.now() + Math.max(0, (tokens.expires_in - 30) * 1000),
        };
        res.setHeader('Set-Cookie', buildSetCookie(seal(session), { maxAge: 8 * 3600 }));
        return res.status(200).json({ authenticated: true });
    } catch (err) {
        return res.status(err.status || 502).json({ error: 'No se pudo autenticar con Factus' });
    }
}
