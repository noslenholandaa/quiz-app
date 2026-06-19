# Sprint 16.2.3 — Correções Finais de UX e Fluxo

## 1. Histórico não atualiza após submissão

### Causa Raiz

Cache HTTP na resposta de `GET /me/submissions`. Embora `fetch()` por padrão não cacheie requisições GET, proxies reversos (Nginx, CDNs) e o cache do navegador (bfcache) podem servir respostas obsoletas sem contatar o servidor. Como o histórico é carregado via `apiGet()` sem nenhum parâmetro variável, a URL é sempre idêntica — permitindo cache em qualquer nível intermediário.

### Evidências

- Backend: `GET /me/submissions` retorna dados corretos e atualizados após nova submissão (verificado via TestClient na Sprint 16.2).
- Frontend: `loadHistory()` é chamado no `load` da página. Se a resposta estiver em cache, o navegador nunca consulta o servidor.
- Comportamento: usuário vê dados antigos mesmo após recarregar a página manualmente (típico de cache de CDN/proxy com `Cache-Control` ausente).

### Correção

Adicionado parâmetro `_=${Date.now()}` às URLs de chamada da API de histórico:

| Arquivo | Linha | Onde |
|---------|-------|------|
| `frontend/history.html` | 138 | `loadHistory()` |
| `frontend/history.html` | 113 | `goPage()` |

```diff
- const data = await apiGet(`/me/submissions?page=${currentPage}&limit=${PAGE_SIZE}`);
+ const data = await apiGet(`/me/submissions?page=${currentPage}&limit=${PAGE_SIZE}&_=${Date.now()}`);
```

Isso garante que cada requisição tenha URL única, forçando o navegador/proxy a consultar o servidor a cada carregamento da página.

---

## 2. Dashboard — Espaçamento Visual

### Causa Raiz

A classe `.dash-row` não possuía `margin-bottom`, ao contrário de `.dash-grid` (`margin-bottom: 24px`) e `.dash-charts-row` (`margin-bottom: 16px`). Isso fazia com que as linhas de seções (.dash-row) ficassem coladas ao próximo bloco.

| Container | margin-bottom |
|-----------|---------------|
| `.dash-grid` | `24px` |
| `.dash-row` | **`0`** ❌ |
| `.dash-charts-row` | `16px` |
| `.dash-section` (dentro de `.dash-row`) | `16px` |

### Correção

```diff
 .dash-row {
   display: grid;
   grid-template-columns: 1fr 1fr;
   gap: 16px;
+  margin-bottom: 16px;
 }
```

Arquivo: `frontend/style.css`, linha 1490.

### Layout final com espaçamento uniforme

```
 ┌────┐ ┌────┐ ┌────┐ ┌────┐     ← dash-grid (margin-bottom: 24px)
 │ Qz │ │ Rsp│ │ Sub│ │ %  │
 └────┘ └────┘ └────┘ └────┘
 ┌──────────┐ ┌──────────┐     ← dash-row (margin-bottom: 16px ✅)
 │  Qz mais  │ │Engajamento│
 │  visto    │ │           │
 └──────────┘ └──────────┘
 ┌──────────┐ ┌──────────┐     ← dash-charts-row (margin-bottom: 16px)
 │Atividade  │ │Estatísticas│
 │período    │ │por período │
 └──────────┘ └──────────┘
 ┌──────────┐ ┌──────────┐     ← dash-row (margin-bottom: 16px ✅)
 │Últimos   │ │Últimas   │
 │quizzes   │ │submissões│
 └──────────┘ └──────────┘
```

---

## Arquivos Modificados

| Arquivo | Mudança | Issue |
|---------|---------|-------|
| `frontend/history.html` | Cache-busting `_=${Date.now()}` em `loadHistory()` e `goPage()` | #1 |
| `frontend/style.css` | `margin-bottom: 16px` adicionado a `.dash-row` | #2 |

## Validação Final

| Critério | Status |
|----------|--------|
| Histórico — cache-busting implementado | ✅ |
| Histórico — sem alteração de rota/API | ✅ |
| Dashboard — espaçamento uniforme entre todos os blocos | ✅ |
| Dashboard — sem alteração de conteúdo/lógica | ✅ |
| 168/168 testes passando | ✅ |
| Linting sem impedimentos | ✅ (E402 intencionais) |

---

**Status Final: OK** ✅

*Relatório gerado em 18/06/2026 — Sprint 16.2.3*
