const AUTH_API = '';

function saveToken(token) {
    localStorage.setItem('quiz_token', token);
}

function getToken() {
    return localStorage.getItem('quiz_token');
}

function removeToken() {
    localStorage.removeItem('quiz_token');
}

function isAuthenticated() {
    return !!getToken();
}

async function authFetch(url, options = {}) {
    const token = getToken();
    const headers = { ...options.headers };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }
    return fetch(url, { ...options, headers });
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
    const body = await res.json();
    if (!res.ok) {
        throw new Error(body.detail || 'Erro na requisição');
    }
    return body;
}

async function apiGet(path) {
    const res = await authFetch(`${AUTH_API}${path}`);
    const body = await res.json();
    if (!res.ok) {
        throw new Error(body.detail || 'Erro na requisição');
    }
    return body;
}

async function loginUser(email, password) {
    const data = await apiPost('/auth/login', { email, password });
    saveToken(data.access_token);
    return data;
}

async function registerUser(name, email, password) {
    const data = await apiPost('/auth/register', { name, email, password });
    saveToken(data.access_token);
    return data;
}

async function fetchMe() {
    return apiGet('/auth/me');
}

function logout() {
    removeToken();
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
