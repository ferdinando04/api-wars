import { buildClearCookie } from '../_lib/session.js';

/** POST /api/auth/logout — borra la cookie de sesión del BFF. */
export default function handler(req, res) {
    if (req.method !== 'POST') {
        res.setHeader('Allow', 'POST');
        return res.status(405).json({ error: 'Método no permitido' });
    }
    res.setHeader('Set-Cookie', buildClearCookie());
    return res.status(200).json({ authenticated: false });
}
