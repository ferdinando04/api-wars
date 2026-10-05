/**
 * Helpers server-side para hablar con la API de Factus v2.
 *
 * Estos corren SOLO en el BFF (Vercel Function). Aquí es donde vive el
 * `client_secret` — como env var de servidor, nunca con prefijo VITE_.
 * Ref: developers.factus.com.co/autenticacion
 */

const FACTUS_BASE = {
    sandbox: 'https://api-sandbox.factus.com.co',
    production: 'https://api.factus.com.co',
};

/** URL base según el ambiente configurado (FACTUS_ENV). */
export function factusBaseUrl() {
    const env = process.env.FACTUS_ENV === 'production' ? 'production' : 'sandbox';
    return FACTUS_BASE[env];
}

function requireEnv(name) {
    const v = process.env[name];
    if (!v) throw new Error(`Falta ${name} en el entorno del BFF.`);
    return v;
}

/**
 * Obtiene tokens con el grant `password` (form-data, como exige Factus v2).
 * @returns {Promise<{access_token:string, refresh_token:string, expires_in:number}>}
 */
export async function passwordGrant() {
    const body = new URLSearchParams({
        grant_type: 'password',
        client_id: requireEnv('FACTUS_CLIENT_ID'),
        client_secret: requireEnv('FACTUS_CLIENT_SECRET'),
        username: requireEnv('FACTUS_USERNAME'),
        password: requireEnv('FACTUS_PASSWORD'),
    });
    return tokenRequest(body);
}

/**
 * Renueva el access token con el refresh token.
 * Factus v2 exige el header Authorization: Bearer <access_token_actual>.
 * @param {string} refreshToken
 * @param {string} currentAccessToken
 */
export async function refreshGrant(refreshToken, currentAccessToken) {
    const body = new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: requireEnv('FACTUS_CLIENT_ID'),
        client_secret: requireEnv('FACTUS_CLIENT_SECRET'),
        refresh_token: refreshToken,
    });
    return tokenRequest(body, currentAccessToken);
}

async function tokenRequest(body, bearer) {
    const headers = { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' };
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    const res = await fetch(`${factusBaseUrl()}/oauth/token`, { method: 'POST', headers, body });
    if (!res.ok) {
        const err = new Error(`OAuth Factus falló: ${res.status}`);
        err.status = res.status;
        throw err;
    }
    return res.json();
}

/**
 * Proxya una llamada autenticada a la API v2 de Factus.
 * @param {object} params
 * @param {string} params.path Ruta (p.ej. '/v2/bills/validate').
 * @param {string} params.method
 * @param {string} params.accessToken
 * @param {object} [params.body]
 * @returns {Promise<{status:number, json:any, headers:Headers}>}
 */
export async function factusApi({ path, method, accessToken, body }) {
    const headers = { Accept: 'application/json', Authorization: `Bearer ${accessToken}` };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const res = await fetch(`${factusBaseUrl()}${path}`, {
        method,
        headers,
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    let json = null;
    try {
        json = await res.json();
    } catch {
        json = null;
    }
    return { status: res.status, json, headers: res.headers };
}
