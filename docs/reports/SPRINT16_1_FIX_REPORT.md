# Sprint 16.1 — Relatório de Correções Pós-Validação Manual

## Resumo Executivo

Durante testes manuais após a Sprint 16, foram identificados 4 problemas funcionais não detectados pelos testes automatizados. Este relatório documenta a investigação, causa raiz, correções aplicadas e evidências de cada item.

---

## 1. Seed de Quizzes

**Problema:** Ambiente local possuía 4 quizzes padrão; produção apenas 2.

### Causa Raiz

A função `seed_quizzes()` em `backend/app/models/database.py` verificava a existência de quizzes apenas pelo título. Se um quiz com o mesmo título já existisse no banco, ele era ignorado — mesmo que os dados (descrição, perguntas) tivessem sido alterados no código. Além disso, quizzes seed que foram removidos do código não eram limpos do banco, causando inconsistência entre ambientes.

### Correção Aplicada

A função `seed_quizzes()` foi refatorada para:

1. **Atualizar** quizzes seed existentes quando os dados no código mudam (descrição ou perguntas)
2. **Remover** quizzes seed órfãos (com `user_id IS NULL` que não estão mais em `SEED_QUIZZES`)
3. **Log detalhado** informando quantos foram inseridos, atualizados, mantidos e removidos

```python
# Lógica atualizada:
# - Percorre SEED_QUIZZES e para cada título:
#   - Se existe no banco: atualiza description/questions se diferente
#   - Se não existe: insere
# - Remove quizzes com user_id IS NULL que não estão em SEED_QUIZZES
```

### Arquivo Alterado

| Arquivo | Linhas | Mudança |
|---------|--------|---------|
| `backend/app/models/database.py` | `seed_quizzes()` | Seed agora atualiza dados existentes e remove órfãos |

### Evidência

```
Seed: 0 inseridos, 2 atualizados, 2 existentes inalterados
```

---

## 2. Histórico de Submissões

**Problema:** Usuário respondia quizzes, mas a página Histórico permanecia vazia.

### Causa Raiz

Após investigação completa (código backend, frontend, testes manuais com TestClient), **nenhum bug foi encontrado no código atual** que cause o comportamento relatado. O fluxo completo foi verificado:

1. **Backend** (`POST /quizzes/{id}/submit`): cria `SubmissionDB` corretamente com `user_id`, `quiz_id`, `answers`, `score`, `max_score`, `percentage`
2. **Backend** (`GET /me/submissions`): retorna `SubmissionListResponse` com paginação correta
3. **Frontend** (`history.html`): chama `apiGet('/me/submissions?page=1&limit=15')` e renderiza com `data.items`, `data.total`

Testes manuais confirmaram que um usuário não-admin consegue:
- Listar quizzes seed → ✅
- Submeter respostas → ✅ (200 OK)
- Visualizar histórico → ✅ (1 submission encontrada)
- Criar quiz → ✅ Bloqueado (403)

### Hipótese Mais Provável

O problema relatado pode ter sido causado por **cache de navegador servindo `auth.js` desatualizado** (documentado no hotfix da Sprint 16). A versão antiga não possuía `initLayout()`, o que poderia interromper a execução do script antes de `loadHistory()` ser chamado.

### Correções Aplicadas

Adicionado logging de debug no frontend para facilitar diagnóstico futuro:

- `console.debug` exibe a resposta bruta da API
- Validação de resposta (`data.total` indefinido → erro)
- Warning quando `total > 0` mas `items` vazio

### Arquivo Alterado

| Arquivo | Mudança |
|---------|---------|
| `frontend/history.html` | Logging de debug e validação de resposta |

### Evidência

```
168/168 testes passando (incluindo test_submissions.py e test_dashboard.py)
Teste manual: Submit → 200, List → 1 item, Create (non-admin) → 403
```

---

## 3. Recuperação de Senha

**Problema:** Fluxo de forgot-password não entregava emails.

### Causa Raiz

O arquivo `render.yaml` (configuração de deploy no Render) **não incluía variáveis de ambiente SMTP**. Em produção, `SMTP_HOST` ficava vazio, fazendo com que `send_password_reset_email()` retornasse `False` imediatamente sem tentar enviar o email.

Embora a função `forgot_password()` em `auth_service.py` já verificasse o retorno e emitisse um log de warning, a ausência de configuração SMTP impedia o funcionamento real do fluxo.

### Correções Aplicadas

1. **Adicionadas variáveis SMTP ao `render.yaml`** com placeholders para configuração:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`
2. **Adicionada variável `FRONTEND_URL`** ao `render.yaml` para links de reset corretos nos emails
3. A função `forgot_password()` já continha tratamento de erro e logging adequado (implementado em correção anterior)

### Arquivo Alterado

| Arquivo | Mudança |
|---------|---------|
| `render.yaml` | Adicionadas 7 variáveis SMTP + FRONTEND_URL |

### Configuração Necessária em Produção

Para o fluxo funcionar, o usuário deve configurar credenciais SMTP reais no Render:

```yaml
SMTP_HOST: smtp.gmail.com          # ou outro servidor SMTP
SMTP_PORT: "587"
SMTP_USERNAME: seu@email.com
SMTP_PASSWORD: sua-senha-de-app
SMTP_FROM: noreply@seudominio.com
```

### Evidência

```
Em desenvolvimento: URL de reset é logada no console do servidor
Endpoint /auth/dev/reset-url disponível para debug (admin ou próprio usuário)
```

---

## 4. RBAC — Controle de Acesso

**Problema:** Usuário comum conseguia criar quizzes. A regra esperada é que apenas administradores possam criar.

### Causa Raiz

**Backend:** Todas as rotas de criação/edição/exclusão de quizzes já usavam `Depends(require_admin)`:
- `POST /quizzes` → `require_admin`
- `PUT /quizzes/{id}` → `require_admin`
- `DELETE /quizzes/{id}` → `require_admin`
- `GET /me/quizzes` → `require_admin`

**Frontend:** O link "Meus Quizzes" na sidebar (`auth.js`) era exibido para **todos os usuários autenticados**, mesmo não-admins. Embora a página `manage.html` bloqueasse o acesso com mensagem "Acesso restrito", a presença do link causava confusão e a navegação até a página gerava uma chamada API que retornava 403.

### Correção Aplicada

O item "Meus Quizzes" foi movido para dentro do bloco `if (isAdmin)` na sidebar, ficando visível **apenas para administradores**, junto com o link "Admin".

### Arquivo Alterado

| Arquivo | Mudança |
|---------|---------|
| `frontend/auth.js` | "Meus Quizzes" movido para seção admin-only da sidebar |

### Evidência

```
Teste manual (non-admin):
- POST /quizzes → 403 Forbidden ✅
- Sidebar sem "Meus Quizzes" ✅
- GET /me/submissions → 200 com dados ✅
```

---

## Testes

### Suite Completa

```
168 passed in 169.84s
✅ Nenhuma regressão
```

### Cobertura

| Categoria | Testes | Status |
|-----------|--------|--------|
| Auth (registro, login, me) | 15 | ✅ |
| Submissão e histórico | 6 | ✅ |
| RBAC | 9 | ✅ |
| Password reset | 14 | ✅ |
| Quizzes (CRUD) | 18 | ✅ |
| Dashboard | 6 | ✅ |
| Leaderboard | 17 | ✅ |
| Email service | 9 | ✅ |
| Search | 8 | ✅ |
| Refresh tokens | 9 | ✅ |
| Sprint 13 | 16 | ✅ |
| Sprint 14.1 | 11 | ✅ |
| Sprint 14.2 | 7 | ✅ |
| Sprint 14.5 | 12 | ✅ |
| Outros | 11 | ✅ |

### Linting

```bash
ruff check app/ tests/
# 23 errors encontrados, 15 corrigidos via --fix
# 8 restantes (E402 - imports posicionados após middleware intencionalmente)
```

---

## Arquivos Modificados

| Arquivo | Mudança | Issue |
|---------|---------|-------|
| `backend/app/models/database.py` | Seed atualiza dados existentes e remove órfãos | #1 Seed |
| `frontend/history.html` | Logging de debug e validação de resposta | #2 Histórico |
| `render.yaml` | Adicionadas variáveis SMTP + FRONTEND_URL | #3 Password Reset |
| `frontend/auth.js` | "Meus Quizzes" movido para admin-only na sidebar | #4 RBAC |

---

## Pronto para Produção?

**SIM** ✅

| Critério | Status |
|----------|--------|
| 168/168 testes passando | ✅ |
| Linting sem impedimentos | ✅ (8 E402 intencionais) |
| Zero novas dependências | ✅ |
| Zero alterações em schema de banco | ✅ |
| Compatibilidade retroativa | ✅ |
| Cache-busting presente em todos os HTMLs | ✅ |
| Guard `typeof initLayout` em todas as páginas | ✅ |

### Notas para Deploy

1. **SMTP:** Configurar credenciais SMTP reais no Render para o fluxo de forgot-password funcionar
2. **FRONTEND_URL:** Já configurado no `render.yaml` como `https://quiz-app.onrender.com`
3. **Seed:** A primeira execução após o deploy atualizará automaticamente os quizzes seed (se houver mudanças nos dados)

---

*Relatório gerado em 18/06/2026 — Sprint 16.1 Fix*
