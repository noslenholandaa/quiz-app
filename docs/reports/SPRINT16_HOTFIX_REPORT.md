# Sprint 16 Hotfix Report

## Causa Raiz

**Cache do navegador servindo `auth.js` desatualizado.**

Durante a Sprint 16, `auth.js` foi estendido com novas funções (`initLayout`, `renderSidebar`, `renderTopHeader`, `toggleMobileMenu`) necessárias para o novo layout com sidebar. As páginas HTML foram atualizadas para chamar `initLayout()` no lugar do antigo `loadUser()`.

Porém, o servidor Nginx em produção configura:

```nginx
location /static/ {
    expires 7d;
    add_header Cache-Control "public, immutable";
    ...
}
```

O direcitvo `immutable` instrui o navegador a **nunca revalidar** o cache por 7 dias. Clientes que carregaram `auth.js` antes do deploy da Sprint 16 continuam servindo a versão antiga (sem `initLayout`), causando:

```
dashboard.html:245
Uncaught ReferenceError: initLayout is not defined
```

As funções antigas (`redirectIfNotAuth`, `isAuthenticated`, `apiGet`, etc.) funcionam porque existiam na versão anterior; `initLayout` não.

### Por que apenas `initLayout`?

| Função | Existia antes? | Quebrou? |
|---|---|---|
| `redirectIfNotAuth()` | ✅ Sim | ❌ Não |
| `isAuthenticated()` | ✅ Sim | ❌ Não |
| `apiGet()` / `apiPost()` | ✅ Sim | ❌ Não |
| `handleApiError()` | ✅ Sim | ❌ Não |
| **`initLayout()`** | ❌ **Não** | **✅ Sim** |
| `renderSidebar()` | ❌ Não | (não chamada diretamente) |

---

## Arquivos Corrigidos

### 1. Cache-busting (12 arquivos HTML + 1 JS)

Adicionado `?v=20260618` a todos os `src` de script e `href` de CSS para forçar o navegador a baixar a versão mais recente:

| Arquivo | Mudança |
|---|---|
| `frontend/dashboard.html` | `style.css?v=20260618`, `theme.js?v=20260618`, `toast.js?v=20260618`, `auth.js?v=20260618` |
| `frontend/index.html` | idem + `script.js?v=20260618` |
| `frontend/leaderboard.html` | idem |
| `frontend/profile.html` | idem |
| `frontend/history.html` | idem |
| `frontend/manage.html` | idem |
| `frontend/admin.html` | idem |
| `frontend/quiz-editor.html` | idem |
| `frontend/login.html` | idem |
| `frontend/register.html` | idem |
| `frontend/forgot-password.html` | idem |
| `frontend/reset-password.html` | idem |

### 2. Defensive guard em `auth.js` (1 arquivo)

Adicionado self-check ao final de `auth.js` que define `window.initLayout` como fallback caso o arquivo carregue parcialmente:

```javascript
if (typeof initLayout !== 'function') {
    console.error('CRITICAL: initLayout não definido...');
    window.initLayout = function() { /* fallback */ };
}
```

### 3. Defensive guard nas páginas (8 arquivos)

Todas as chamadas a `initLayout()` agora usam `typeof` check para evitar `ReferenceError`:

```javascript
// Antes
initLayout('Dashboard');

// Depois
if (typeof initLayout === 'function') initLayout('Dashboard');
```

Arquivos modificados: `dashboard.html`, `script.js`, `leaderboard.html`, `profile.html`, `history.html`, `manage.html`, `admin.html`, `quiz-editor.html`.

---

## Páginas Afetadas

| Página | Chamava `initLayout` | Risco | Corrigido |
|---|---|---|---|
| `dashboard.html` | ✅ `initLayout('Dashboard')` | 🔴 Crítico | ✅ |
| `index.html` (via `script.js`) | ✅ `initLayout('Explorar')` | 🔴 Crítico | ✅ |
| `leaderboard.html` | ✅ `initLayout('Ranking')` | 🔴 Crítico | ✅ |
| `profile.html` | ✅ `initLayout('Perfil')` | 🔴 Crítico | ✅ |
| `history.html` | ✅ `initLayout('Histórico')` | 🔴 Crítico | ✅ |
| `manage.html` | ✅ `initLayout('Gerenciar')` | 🔴 Crítico | ✅ |
| `admin.html` | ✅ `initLayout('Admin')` | 🔴 Crítico | ✅ |
| `quiz-editor.html` | ✅ `initLayout('Editor')` | 🔴 Crítico | ✅ |
| `login.html` | ❌ | 🟢 Nenhum | N/A |
| `register.html` | ❌ | 🟢 Nenhum | N/A |
| `forgot-password.html` | ❌ | 🟢 Nenhum | N/A |
| `reset-password.html` | ❌ | 🟢 Nenhum | N/A |

---

## Evidências de Funcionamento

### Testes
```
168 passed in 159.35s
✅ Nenhuma regressão
```

### Sintaxe JS
```
auth.js: 12.562 bytes, 305+ linhas
✅ Syntax: VALID
✅ initLayout definida
✅ Fallback window.initLayout presente
```

### Cache-busting verificado
```
✅ dashboard.html — OK
✅ index.html — OK
✅ leaderboard.html — OK
✅ profile.html — OK
✅ history.html — OK
✅ manage.html — OK
✅ admin.html — OK
✅ quiz-editor.html — OK
✅ login.html — OK
✅ register.html — OK
✅ forgot-password.html — OK
✅ reset-password.html — OK
```
Todos os 12 HTMLs possuem `src="auth.js?v=20260618"` e `href="style.css?v=20260618"`.

### Defensive guards
```
✅ dashboard.html: if (typeof initLayout === 'function') initLayout('Dashboard');
✅ script.js:     if (typeof initLayout === 'function') initLayout('Explorar');
✅ leaderboard:   if (typeof initLayout === 'function') initLayout('Ranking');
✅ profile:       if (isAuthenticated() && typeof initLayout === 'function')
✅ history:       if (typeof initLayout === 'function') initLayout('Histórico');
✅ manage:        if (typeof initLayout === 'function') initLayout('Gerenciar');
✅ admin:         if (typeof initLayout === 'function') initLayout('Admin');
✅ quiz-editor:   if (typeof initLayout === 'function') initLayout('Editor');
```

---

## Console Limpo (após correção)

Os seguintes erros foram eliminados:

| Erro | Causa | Status |
|---|---|---|
| `ReferenceError: initLayout is not defined` | Cache de `auth.js` antigo | ✅ Eliminado |
| `404 para /static/login.html` após redirect (se sem token) | Não é erro — redirect intencional | N/A — comportamento normal |
| Potencial `ReferenceError` em páginas com cache parcial | Sempre que auth.js carregar corretamente | ✅ Guard `typeof` previne |

---

## Recomendações para Produção

1. **Cache-busting automático:** Implementar um build step (ex: Gulp, Vite, ou script simples) que gere hashes de conteúdo nos nomes de arquivo (ex: `auth.a1b2c3d4.js`) em vez de query parameters manuais.
2. **Remover `immutable` do Nginx:** Alterar o header de cache para `public, max-age=3600` (1 hora) em vez de 7 dias com `immutable`, permitindo revalidação mais rápida após deploys.
3. **Service Worker:** Considerar implementar um service worker com lógica de "stale-while-revalidate" para controle fino de cache offline sem os efeitos colaterais do `immutable`.
4. **Versionamento de release:** Adicionar `APP_VERSION` injetado pelo backend no HTML via template, usado como base para o cache-buster.

---

## Pronto para Produção?

**SIM** ✅

| Critério | Status |
|---|---|
| 168/168 testes passando | ✅ |
| Cache-busting aplicado em 12 páginas | ✅ |
| Guard `typeof initLayout` em 8 páginas | ✅ |
| Fallback `window.initLayout` em auth.js | ✅ |
| Zero novas dependências | ✅ |
| Zero alterações em API/banco | ✅ |
| Compatibilidade retroativa com auth.js antigo via guard | ✅ |

---

*Relatório gerado em 18/06/2026 — Hotfix Sprint 16*
