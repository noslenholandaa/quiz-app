const AUTH_API = '';

function saveToken(accessToken, refreshToken) {
    localStorage.setItem('quiz_token', accessToken);
    if (refreshToken) localStorage.setItem('quiz_refresh', refreshToken);
}

function getToken() {
    return localStorage.getItem('quiz_token');
}

function getRefreshToken() {
    return localStorage.getItem('quiz_refresh');
}

function removeTokens() {
    localStorage.removeItem('quiz_token');
    localStorage.removeItem('quiz_refresh');
}

function isAuthenticated() {
    return !!getToken();
}

async function tryRefreshToken() {
    const rt = getRefreshToken();
    if (!rt) return false;
    try {
        const res = await fetch(`${AUTH_API}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: rt }),
        });
        if (!res.ok) { removeTokens(); return false; }
        const data = await res.json();
        saveToken(data.access_token, data.refresh_token);
        return true;
    } catch {
        removeTokens();
        return false;
    }
}

async function authFetch(url, options = {}) {
    let token = getToken();
    const headers = { ...options.headers };
    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }
    const doFetch = (t) => {
        const h = { ...headers };
        if (t) h['Authorization'] = `Bearer ${t}`;
        return fetch(url, { ...options, headers: h });
    };
    let res = await doFetch(token);
    if (res.status === 401 && getRefreshToken()) {
        const ok = await tryRefreshToken();
        if (ok) {
            token = getToken();
            res = await doFetch(token);
        }
    }
    return res;
}

function getAuthHeaders() {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiPost(path, data) {
    const res = await authFetch(`${AUTH_API}${path}`, {
        method: 'POST',
        body: JSON.stringify(data),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || 'Erro na requisição');
    return body;
}

async function apiGet(path) {
    const res = await authFetch(`${AUTH_API}${path}`);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || 'Erro na requisição');
    return body;
}

async function apiPut(path, data) {
    const res = await authFetch(`${AUTH_API}${path}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || 'Erro na requisição');
    return body;
}

async function apiDelete(path) {
    const res = await authFetch(`${AUTH_API}${path}`, { method: 'DELETE' });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Erro na requisição');
    }
}

function handleApiError(err) {
    const messages = {
        400: 'Dados inválidos. Verifique as informações e tente novamente.',
        401: 'Sessão expirada. Faça login novamente.',
        403: 'Acesso negado. Você não tem permissão para esta ação.',
        404: 'Recurso não encontrado.',
        422: 'Dados inválidos. Verifique os campos e tente novamente.',
        429: 'Muitas requisições. Aguarde alguns segundos e tente novamente.',
        500: 'Erro interno do servidor. Tente novamente mais tarde.',
        502: 'Servidor temporariamente indisponível. Tente novamente mais tarde.',
        503: 'Serviço indisponível no momento. Tente novamente mais tarde.',
    };
    if (err.status && messages[err.status]) {
        return messages[err.status];
    }
    if (err.message === 'Failed to fetch' || err.message === 'NetworkError') {
        return 'Erro de conexão. Verifique sua internet e tente novamente.';
    }
    if (err.message?.includes('timeout') || err.message?.includes('timed out')) {
        return 'A requisição excedeu o tempo limite. Tente novamente.';
    }
    return err.message || 'Erro desconhecido. Tente novamente.';
}

async function loginUser(email, password) {
    const data = await apiPost('/auth/login', { email, password });
    saveToken(data.access_token, data.refresh_token);
    return data;
}

async function registerUser(name, email, password) {
    const data = await apiPost('/auth/register', { name, email, password });
    saveToken(data.access_token, data.refresh_token);
    return data;
}

async function fetchMe() {
    return apiGet('/auth/me');
}

async function logout() {
    const rt = getRefreshToken();
    try {
        if (rt) {
            await fetch(`${AUTH_API}/auth/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: rt }),
            });
        }
    } catch {
    }
    removeTokens();
    window.location.href = '/static/login.html';
}

function redirectIfNotAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/static/login.html';
    }
}

function redirectIfAuth() {
    if (isAuthenticated()) {
        window.location.href = '/static/index.html';
    }
}
