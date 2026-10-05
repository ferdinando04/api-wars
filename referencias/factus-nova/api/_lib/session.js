import crypto from 'node:crypto';

/**
 * Sesión cifrada en cookie httpOnly (patrón token-handler / BFF).
 *
 * Los tokens de Factus (access + refresh) nunca llegan al navegador: viajan
 * cifrados dentro de una cookie httpOnly que solo el BFF puede leer. AES-256-GCM
 * da confidencialidad + integridad (detecta manipulación).
 *
 * Requiere la env var SESSION_SECRET (32+ bytes). Genera una con:
 *   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
 * Ref: IETF draft-ietf-oauth-browser-based-apps §6.1.3.2 (Secure; HttpOnly; SameSite=Strict)
 */

const COOKIE_NAME = 'fn_session';
const ALG = 'aes-256-gcm';

function getKey() {
    const secret = process.env.SESSION_SECRET;
    if (!secret) throw new Error('Falta SESSION_SECRET en el entorno del BFF.');
    // Deriva 32 bytes determinísticos del secreto (acepta base64 o texto).
    return crypto.createHash('sha256').update(secret).digest();
}

/**
 * Cifra un objeto de sesión a un string seguro para cookie.
 * @param {object} session
 * @returns {string} base64url( iv | tag | ciphertext )
 */
export function seal(session) {
    const key = getKey();
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv(ALG, key, iv);
    const plaintext = Buffer.from(JSON.stringify(session), 'utf8');
    const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
    const tag = cipher.getAuthTag();
    return Buffer.concat([iv, tag, ciphertext]).toString('base64url');
}

/**
 * Descifra el string de cookie a su objeto de sesión.
 * @param {string} sealed
 * @returns {object|null} La sesión, o null si es inválida/manipulada.
 */
export function unseal(sealed) {
    if (!sealed) return null;
    try {
        const key = getKey();
        const raw = Buffer.from(sealed, 'base64url');
        const iv = raw.subarray(0, 12);
        const tag = raw.subarray(12, 28);
        const ciphertext = raw.subarray(28);
        const decipher = crypto.createDecipheriv(ALG, key, iv);
        decipher.setAuthTag(tag);
        const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
        return JSON.parse(plaintext.toString('utf8'));
    } catch {
        return null; // firma inválida o cookie corrupta
    }
}

/**
 * Construye el header Set-Cookie con las banderas de seguridad requeridas.
 * @param {string} value
 * @param {object} [opts]
 * @param {number} [opts.maxAge=3600] Segundos de vida.
 * @returns {string}
 */
export function buildSetCookie(value, { maxAge = 3600 } = {}) {
    const parts = [
        `${COOKIE_NAME}=${value}`,
        'Path=/',
        'HttpOnly',
        'Secure',
        'SameSite=Strict',
        `Max-Age=${maxAge}`,
    ];
    return parts.join('; ');
}

/** Header Set-Cookie que borra la sesión. */
export function buildClearCookie() {
    return `${COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;
}

/**
 * Lee y descifra la sesión desde el header Cookie de una request.
 * @param {import('http').IncomingMessage} req
 * @returns {object|null}
 */
export function readSession(req) {
    const cookie = req.headers?.cookie || '';
    const match = cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith(`${COOKIE_NAME}=`));
    if (!match) return null;
    return unseal(match.slice(COOKIE_NAME.length + 1));
}

export { COOKIE_NAME };
