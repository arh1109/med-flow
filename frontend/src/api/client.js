import axios from 'axios';


const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    'http://127.0.0.1:8000';


const apiClient = axios.create({
    baseURL: API_BASE_URL,
});


// Use a separate Axios instance for refresh requests so a failed refresh
// cannot recursively trigger this client's own response interceptor.
const refreshClient = axios.create({
    baseURL: API_BASE_URL,
});


let refreshPromise = null;
let authFailureHandler = null;


export function setAuthFailureHandler(handler) {
    authFailureHandler = handler;
}


function clearTokens() {
    localStorage.removeItem('medFlowToken');
    localStorage.removeItem('medFlowRefreshToken');
}


// Attach the current access token to every normal API request.
apiClient.interceptors.request.use((config) => {
    const accessToken = localStorage.getItem('medFlowToken');

    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
});


async function refreshTokens() {
    const refreshToken = localStorage.getItem('medFlowRefreshToken');

    if (!refreshToken) {
        throw new Error('No refresh token available');
    }

    const response = await refreshClient.post(
        '/auth/refresh',
        {
            refresh_token: refreshToken,
        }
    );

    const {
        access_token,
        refresh_token,
    } = response.data;

    localStorage.setItem(
        'medFlowToken',
        access_token
    );

    localStorage.setItem(
        'medFlowRefreshToken',
        refresh_token
    );

    return access_token;
}


apiClient.interceptors.response.use(
    (response) => response,

    async (error) => {
        const originalRequest = error.config;

        if (
            error.response?.status !== 401 ||
            !originalRequest ||
            originalRequest._retry
        ) {
            return Promise.reject(error);
        }

        // Authentication endpoints must not trigger another refresh attempt.
        if (
            originalRequest.url === '/auth/token' ||
            originalRequest.url === '/auth/refresh' ||
            originalRequest.url === '/auth/logout'
        ) {
            return Promise.reject(error);
        }

        originalRequest._retry = true;

        try {
            // Several requests may fail with 401 at nearly the same time.
            // They all await the same refresh operation rather than each
            // rotating the refresh token independently.
            if (!refreshPromise) {
                refreshPromise = refreshTokens()
                    .finally(() => {
                        refreshPromise = null;
                    });
            }

            const newAccessToken = await refreshPromise;

            originalRequest.headers =
                originalRequest.headers || {};

            originalRequest.headers.Authorization =
                `Bearer ${newAccessToken}`;

            return apiClient(originalRequest);

        } catch (refreshError) {
            clearTokens();

            if (authFailureHandler) {
                authFailureHandler();
            }

            return Promise.reject(refreshError);
        }
    }
);


export default apiClient;
