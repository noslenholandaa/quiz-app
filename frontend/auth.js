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

/* ============================================
   SIDEBAR + LAYOUT
   ============================================ */
function getPageName() {
    const path = window.location.pathname;
    const map = {
        '/static/index.html': 'quizzes',
        '/static/dashboard.html': 'dashboard',
        '/static/leaderboard.html': 'leaderboard',
        '/static/history.html': 'history',
        '/static/manage.html': 'manage',
        '/static/quiz-editor.html': 'editor',
        '/static/admin.html': 'admin',
        '/static/profile.html': 'profile',
    };
    return map[path] || '';
}

function renderSidebar(currentPage, user) {
    const initials = user ? user.name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase() : '?';
    const isAdmin = user && user.role === 'admin';

    const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>', href: '/static/dashboard.html' },
        { id: 'quizzes', label: 'Explorar', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>', href: '/static/index.html' },
        { id: 'leaderboard', label: 'Ranking', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5C7 4 6 9 6 9z"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5C17 4 18 9 18 9z"/><path d="M4 22h16"/><path d="M10 22V2h4v20"/></svg>', href: '/static/leaderboard.html' },
        { id: 'history', label: 'Histórico', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', href: '/static/history.html' },
    ];

    if (isAdmin) {
        navItems.push({ id: 'manage', label: 'Meus Quizzes', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>', href: '/static/manage.html' });
        navItems.push({ id: 'admin', label: 'Admin', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>', href: '/static/admin.html' });
    }

    const navHtml = navItems.map(item =>
        `<a href="${item.href}" class="${currentPage === item.id ? 'active' : ''}">${item.icon}${item.label}</a>`
    ).join('\n          ');

    return `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand-top">
          <div class="sidebar-brand-icon">QA</div>
          <div class="sidebar-brand-text">Quiz App</div>
        </div>
        ${user ? `<div class="sidebar-user-info"><div class="user-avatar">${initials}</div><span class="user-name-display">${user.name}</span></div>` : ''}
      </div>
      <nav class="sidebar-nav">
        ${navHtml}
      </nav>
      <div class="sidebar-footer">
        <button class="nav-item" onclick="Theme.toggle()" aria-label="Alternar tema" title="Alternar tema">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="theme-icon-sun"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="theme-icon-moon" style="display:none"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          Alternar tema
        </button>
        <button class="nav-item" onclick="logout()" aria-label="Sair">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          Sair
        </button>
      </div>
    </aside>`;
}

function renderTopHeader(title) {
    return `
    <header class="top-header">
      <button class="mobile-menu-btn" onclick="toggleMobileMenu()" aria-label="Abrir menu">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <h1 class="top-header-title">${title}</h1>
      <div class="top-header-actions">
        <div class="admin-badge-static hidden" id="header-admin-badge">Admin</div>
      </div>
    </header>`;
}

let cachedUser = null;

async function getCurrentUser() {
    if (cachedUser) return cachedUser;
    try {
        cachedUser = await fetchMe();
        return cachedUser;
    } catch {
        return null;
    }
}

async function initLayout(title) {
    const user = await getCurrentUser();
    if (!user) return;

    const page = getPageName();
    const appLayout = document.querySelector('.app-layout');
    if (!appLayout) return;

    const sidebarHtml = renderSidebar(page, user);
    const temp = document.createElement('div');
    temp.innerHTML = sidebarHtml;
    const sidebar = temp.firstElementChild;

    document.body.insertBefore(sidebar, appLayout);

    const mainArea = appLayout.querySelector('.main-area');
    if (mainArea) {
        const headerHtml = renderTopHeader(title);
        const headerTemp = document.createElement('div');
        headerTemp.innerHTML = headerHtml;
        const header = headerTemp.firstElementChild;
        mainArea.insertBefore(header, mainArea.firstChild);

        if (user.role === 'admin') {
            const badge = document.getElementById('header-admin-badge');
            if (badge) badge.classList.remove('hidden');
        }
    }

    Theme.init();
}

function toggleMobileMenu() {
    document.body.classList.toggle('sidebar-open');
}

document.addEventListener('click', function(e) {
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay && e.target === overlay) {
        document.body.classList.remove('sidebar-open');
    }
});

/* Shared helpers for result/history rendering */
function formatDate(d) {
    return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }) + ' às ' +
           new Date(d).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function getGradeClass(perc) {
    if (perc >= 90) return 'grade-excellent';
    if (perc >= 70) return 'grade-good';
    if (perc >= 50) return 'grade-medium';
    return 'grade-bad';
}

function getGradeLabel(perc) {
    if (perc >= 95) return { icon: '\u{1F3C6}', label: 'Excelente' };
    if (perc >= 80) return { icon: '\u{1F947}', label: 'Muito Bom' };
    if (perc >= 60) return { icon: '\u{1F948}', label: 'Bom' };
    if (perc >= 40) return { icon: '\u{1F949}', label: 'Em Desenvolvimento' };
    return { icon: '\u{1F4DA}', label: 'Continue Praticando' };
}

/* Ensure window.initLayout is always set (guarda contra cache de versão antiga) */
window.initLayout = window.initLayout || function() {};
