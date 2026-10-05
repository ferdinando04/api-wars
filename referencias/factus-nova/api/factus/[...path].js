import { factusApi, refreshGrant } from '../_lib/factus.js';
import { readSession, seal, buildSetCookie, buildClearCookie } from '../_lib/session.js';

/**
 * /api/factus/* — proxy autenticado a Factus API v2.
 *
 * Flujo por request:
 *  1. Lee la sesión cifrada de la cookie httpOnly (el SPA nunca vio el token).
 *  2. Si el access token está por vencer, lo refresca con el refresh token
 *     (que vive solo aquí) y re-sella la cookie.
 *  3. Adjunta el Bearer y reenvía la llamada a Factus, devolviendo la respuesta.
 *
 * Defensa CSRF: solo se aceptan métodos con estado si traen el header custom
 * `X-Requested-With` (además de SameSite=Strict en la cookie).
 * Ref: IETF draft-ietf-oauth-browser-based-apps §6.1.3.3
 */
export default async function handler(req, res) {
    let session = readSession(req);
    if (!session?.access_token) {
        return res.status(401).json({ error: 'No autenticado' });
    }

    const isStateChanging = req.method !== 'GET' && req.method !== 'HEAD';
    if (isStateChanging && req.headers['x-requested-with'] !== 'fetch') {
        return res.status(403).json({ error: 'CSRF: falta X-Requested-With' });
    }

    // Refresco proactivo si el token está por vencer.
    if (session.expires_at && session.expires_at <= Date.now()) {
        try {
            const t = await refreshGrant(session.refresh_token, session.access_token);
            session = {
                access_token: t.access_token,
                refresh_token: t.refresh_token || session.refresh_token,
                expires_at: Date.now() + Math.max(0, (t.expires_in - 30) * 1000),
            };
            res.setHeader('Set-Cookie', buildSetCookie(seal(session), { maxAge: 8 * 3600 }));
        } catch {
            // Solo un fallo real de auth cierra sesión; un blip de red se propaga como 502.
            res.setHeader('Set-Cookie', buildClearCookie());
            return res.status(401).json({ error: 'Sesión expirada' });
        }
    }

    // Reconstruye la ruta de Factus a partir del catch-all [...path].
    const segments = Array.isArray(req.query.path) ? req.query.path : [req.query.path].filter(Boolean);
    const search = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    const path = `/${segments.join('/')}${search}`;

    try {
        const { status, json, headers } = await factusApi({
            path,
            method: req.method,
            accessToken: session.access_token,
            body: isStateChanging ? req.body : undefined,
        });
        // Propaga los headers de rate-limit para que el cliente pueda auto-throttle.
        for (const h of ['x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'retry-after']) {
            const v = headers.get?.(h);
            if (v) res.setHeader(h, v);
        }
        return res.status(status).json(json);
    } catch (err) {
        return res.status(err.status || 502).json({ error: 'Error al contactar Factus' });
    }
}
