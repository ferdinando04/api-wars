import axios from 'axios';

/**
 * Cliente HTTP Base (Axios)
 * Proxy de Vite (dev) y Vercel rewrites (prod) resuelven CORS.
 * Auto-refresh del token: usa refresh_token real, fallback a re-login.
 */
export const axiosClient = axios.create({
    baseURL: '',
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) prom.reject(error);
        else prom.resolve(token);
    });
    failedQueue = [];
};

async function refreshToken() {
    const clientId = import.meta.env.VITE_FACTUS_CLIENT_ID;
    const clientSecret = import.meta.env.VITE_FACTUS_CLIENT_SECRET;

    if (!clientId) throw new Error('No hay credenciales para re-autenticar.');

    // Intentar con refresh_token real primero
    const savedRefreshToken = sessionStorage.getItem('factus_refresh_token');
    if (savedRefreshToken) {
        const response = await axios.post('/oauth/token', {
            grant_type: 'refresh_token',
            client_id: clientId,
            client_secret: clientSecret,
            refresh_token: savedRefreshToken
        }, { headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' } });

        const newToken = response.data?.access_token;
        if (newToken) {
            sessionStorage.setItem('factus_access_token', newToken);
            if (response.data?.refresh_token) {
                sessionStorage.setItem('factus_refresh_token', response.data.refresh_token);
            }
            return newToken;
        }
    }

    throw new Error('Sesión expirada. Inicia sesión de nuevo.');
}

// Request Interceptor — Inyecta Bearer token
axiosClient.interceptors.request.use(
    (config) => {
        const token = sessionStorage.getItem('factus_access_token');
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor — Auto-refresh en 401
axiosClient.interceptors.response.use(
    (response) => response.data,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/oauth/')) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return axiosClient(originalRequest);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const newToken = await refreshToken();
                processQueue(null, newToken);
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return axiosClient(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError, null);
                sessionStorage.removeItem('factus_access_token');
                sessionStorage.removeItem('factus_refresh_token');
                window.location.href = '/';
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);
