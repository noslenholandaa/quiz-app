# Auditoria Técnica Completa — Quiz App

> **Data:** 18/06/2026  
> **Propósito:** Avaliação de portfólio — candidato a primeira oportunidade  
> **Stack:** Python/FastAPI + SQLAlchemy + SQLite/PostgreSQL + Vanilla JS

---

## 1. Arquitetura

### Organização de pastas — `8/10`

O projeto segue uma estrutura monorepo com separação clara:

```
quiz-app/
├── backend/        # API FastAPI + ORM + migrações
├── frontend/       # HTML/CSS/JS puro
├── deploy/         # Nginx para produção
├── scripts/        # Scripts de banco (backup/restore)
├── docs/           # Documentação de arquitetura
├── .github/        # CI/CD
└── docker-compose*.yml
```

**Positivo:** Separação backend/frontend, presença de `scripts/` e `deploy/`, documentação de arquitetura em `backend/docs/`.

**Negativo:** Não há `Makefile` ou task runner unificado (comandos espalhados entre README, docker-compose e CI). Alguns arquivos de documentação em `backend/docs/` (ex: `json-scalability-analysis.md`, `sprint15-report.md`) sugerem escopo além do necessário para este porte de projeto — podem indicar "documentação por documento" em vez de "documentação por necessidade".

### Separação de responsabilidades — `8/10`

**Positivo:**
- `auth.py` isola autenticação (JWT, bcrypt, refresh tokens) em roteador próprio
- `services/email_service.py` separa lógica de email
- `config.py` centraliza configurações por ambiente
- `models.py` contém apenas Pydantic models (schemas de request/response)
- `database.py` contém as SQLAlchemy models + engine + seed

**Negativo:**
- `main.py` acumula **demasiadas responsabilidades**: logging, rate limiting, health check, metrics, CRUD de quizzes, dashboard, leaderboard, profile público, badges, admin dashboard. Idealmente extrairia-se:
  - `routes/quizzes.py`
  - `routes/admin.py`
  - `routes/dashboard.py`
  - `routes/leaderboard.py`
  - `middleware/` (rate limit, request ID, logging)
- Lógica de negócio (badges, ranking position, cálculo de score) está inline nas rotas, não em serviços separados

### Acoplamento entre módulos — `7/10`

- `main.py` importa diretamente de `database.py`, `auth.py`, `config.py`, `models.py` — acoplamento aceitável para projeto monorepo
- Rate limiting implementado in-memory com dicionário global (`_rate_limit_store`) — inviável em multi-process (gunicorn/uvicorn workers). Não escala
- Lógica de badge está inline em `public_profile()` em vez de um `BadgeService`

### Escalabilidade da arquitetura atual — `5/10`

**Gargalos identificados:**
1. **Rate limit in-memory** — quebra com >1 worker. Sem Redis, não escala horizontalmente
2. **Monolíto sem separação de rotas** — `main.py` com 917 linhas
3. **SQLite em dev, PostgreSQL em prod** — diferenças de dialeto podem gerar surpresas (ex: seed_quizzes usa `setval` específico do PostgreSQL)
4. **Frontend monolithic script** — `auth.js`, `script.js`, `toast.js`, `theme.js` são arquivos soltos, sem módulos ou bundler

---

## 2. Backend

### Qualidade das rotas FastAPI — `8/10`

**Positivo:**
- Uso correto de `Depends()` para injeção de dependências
- Rotas RESTful com verbos HTTP adequados
- Status codes apropriados (201 para create, 204 para delete)
- `response_model` nos endpoints (documentação automática OpenAPI)
- Validação de entrada com Pydantic
- Uso de `selectinload` para eager loading de relacionamentos

**Negativo:**
- `PUT` e `PATCH` mapeados para mesma função em `admin_set_role` — `@app.put` e `@app.patch` no mesmo handler
- `submit_quiz` calcula score como `len(respostas)` sem validação de resposta correta vs. incorreta (apenas conta presença de resposta)
- Rotas administrativas em `main.py` em vez de roteador separado
- Endpoint `/admin/users/{user_id}/role` recebe `body: dict` em vez de Pydantic model
- `GET /quizzes/{quiz_id}` não autentica (qualquer um pode ver qualquer quiz)

### Estrutura dos serviços — `6/10`

Apenas `services/email_service.py` existe como serviço isolado. Todo o restante da lógica de negócio está inline nas rotas.

**Recomendação:** Extrair:
- `services/quiz_service.py`
- `services/submission_service.py`
- `services/dashboard_service.py`
- `services/leaderboard_service.py`
- `services/badge_service.py`

### Reutilização de código — `7/10`

`quiz_to_response()` é reutilizado. `_ranking_position()` é função auxiliar. Mas `quiz_counts` e `sub_counts` são recalculados em `admin_dashboard` e `admin_list_users` — duplicação de lógica.

### Possíveis refatorações

1. Extrair rotas para `routes/` package
2. Extrair lógica de negócio para `services/`
3. Criar `middleware/rate_limit.py` com suporte a Redis
4. Substituir `body: dict` por Pydantic model
5. Unificar tratamento de erros com Exception handlers customizados

---

## 3. Banco de Dados

### Modelagem — `7/10`

**Positivo:**
- Modelos SQLAlchemy bem definidos com `__tablename__`, `relationship`, `ForeignKey`
- Tabela associativa `quiz_tags` para many-to-many
- Índices criados nas colunas mais consultadas (`user_id`, `quiz_id`, `created_at`, `email`, `token_hash`)

**Negativo:**
- `questions` armazenado como `JSON` — sem normalização. Consultas do tipo "quantas perguntas do tipo 'text' existem?" são impossíveis sem scan
- `answers` armazenado como `JSON` — impede consultas analíticas
- Sem `updated_at` em `submissions` e `users`
- `SubmissionDB.quiz_title` é denormalizado (duplicado do `QuizDB.title`) — fragilidade: se o título do quiz mudar, submissions antigas mantêm o título antigo
- Seed data hardcoded em `database.py` — 4 quizzes fixos

### Relacionamentos — `8/10`

Relacionamentos estão corretos: User 1:N Submission, User 1:N Quiz, Quiz M:N Tag, Quiz N:1 Category. Cascade delete configurado.

### Índices necessários

Os índices existentes cobrem bem os casos de uso atuais. Melhorias:
- `ix_submissions_user_id_quiz_id` composto para leaderboards por quiz
- `ix_submissions_created_at_user_id` composto para dashboard temporal

### Consultas potencialmente ineficientes

1. **`/admin/dashboard`** e **`/admin/users`**: Fazem `COUNT` separado e depois buscam todos os usuários sem paginação — conforme dados crescerem, será O(n) com n = total de usuários
2. **`/leaderboard`**: Agrupa por `user_id` sem índice composto — scan completo em `submissions`
3. **`/users/{id}/profile`**: Múltiplas queries (count quizzes, stats, badges, ranking) — N+1 não exatamente, mas múltiplas idas ao banco

### Melhorias para PostgreSQL

- Usar `ARRAY_AGG` e `JSON_AGG` em vez de queries múltiplas
- `tsvector` para busca textual no lugar de `ILIKE %term%`
- `PARTITION BY` para queries de leaderboard temporais
- Connection pooling nativo do PostgreSQL (SQLAlchemy `pool_size` e `max_overflow`)
- Remover `check_same_thread` (específico SQLite)

---

## 4. Segurança

### JWT — `8/10`

- Access token com 15min de expiração (curto, bom)
- Refresh token com rotation (cada refresh invalida o anterior)
- `HS256` com algoritmo definido em config
- Payload inclui `sub` (user_id), `type` ("access"/"refresh"), `role`
- Validação de `type` no `decode_access_token`

Falha: Não há `jti` (JWT ID) para revogação de access tokens. Uma vez emitido, um access token é válido até expirar.

### Refresh Tokens — `9/10`

- Armazenados como hash SHA-256 (não expostos no banco)
- Rotação forçada (token de uso único)
- Revogação via `logout` e `revoke_session`
- Expiração com verificação

### Password Reset — `8/10`

- Token aleatório de 32 bytes hasheado com SHA-256
- Expiração de 1h
- Token de uso único (flag `used`)
- Mensagem consistente (usuário existe ou não — mesma resposta)
- Token não vaza em logs (verificado em teste)
- Não há rate limit no `forgot-password` — possível enumeração de email via timing (atenuado pela dummy hash + mesma mensagem, mas sem rate limit ainda permite bruteforce)

### RBAC — `7/10`

- Roles `admin` e `user`
- `require_admin()` como dependência
- Admin não pode se auto-rebaixar
- Admin promotion automática via `ADMIN_EMAILS`

Fragilidade: Autopromoção via `ADMIN_EMAILS` no login/register é frágil — qualquer um que crie conta com email na lista vira admin. Melhor: endpoint específico.

### Rate Limiting — `6/10`

- Login: 10/min, Registro: 5/h
- Implementação in-memory — **não funciona com múltiplos workers**
- Sem rate limit em `forgot-password`, `reset-password`, `/auth/refresh`
- Garbage collection manual com intervalo de 5 minutos — possível memory leak

### Headers de Segurança — `9/10`

- `X-Content-Type-Options: nosniff` ✓
- `X-Frame-Options: DENY` ✓
- `X-XSS-Protection: 1; mode=block` ✓
- `Strict-Transport-Security` em produção ✓
- Nginx adiciona `Referrer-Policy`, `Permissions-Policy` ✓

### Possíveis vulnerabilidades

1. **`/dev/reset-url`**: Endpoint de debug que expõe reset URL — protegido por `ENVIRONMENT != production`, mas ainda existe
2. **CORS com allow_origins=["*"] bloqueia em produção** — OK, mas o bloqueio é silencioso para o usuário
3. **`get_quiz()` não requer autenticação** — qualquer quiz público é visível. Desejado? Depende do requisito
4. **`/users/{id}/profile` não requer autenticação** — expõe badges, scores e quizzes de qualquer usuário sem login
5. **`body: dict` em admin_set_role** — sem validação Pydantic, aceita qualquer corpo

---

## 5. Testes

### Cobertura real — `9/10`

Backend: ~85-90% (cobertura configurada para 80% no CI).  
Frontend: ~60-70% (apenas Toast, Theme, handleApiError e empty state).

**Testes backend quantitativos:**
- `test_auth.py`: 13 testes (register, login, me, password verify)
- `test_quizzes.py`: 13 testes (CRUD completo)
- `test_rbac.py`: 9 testes (admin perms, promote, demote)
- `test_submissions.py`: 6 testes (submit, list, isolation)
- `test_refresh_tokens.py`: 8 testes (refresh, logout, sessions, expiry)
- `test_password_reset.py`: 12 testes (forgot, reset, expiry, leak, env)
- `test_leaderboard.py`: 12 testes (ranking, badges, score)
- `test_dashboard.py`: 6 testes (dashboard, stats)
- `test_search.py`: 7 testes (search, pagination, profile)
- `test_categories.py`: 5 testes
- `test_health.py`: 2 testes
- `test_email_service.py`: testes unitários com mock
- `test_sprint13.py`: testes de regressão
- `test_sprint141.py`: testes de paginação
- `test_sprint142.py`: testes de agregação
- `test_sprint145.py`: testes de observabilidade

Total aproximado: **~100+ testes backend**

### Qualidade dos testes — `8/10`

**Positivo:**
- Testes isolados (DB recriado a cada fixture)
- Cobertura de bordas (campos vazios, whitespace, duplicatas)
- Testes de segurança (token leak, timing attack, env-specific behavior)
- CI exige 80% de cobertura mínima
- Testes de refresh token rotation e revogação

**Negativo:**
- Testes usam SQLite — diferenças de dialeto com PostgreSQL podem esconder bugs
- `conftest.py` modifica `sys.path` e `environ` globalmente — efeitos colaterais entre testes
- Testes do `test_sprint13.py` em diante têm nomes pouco descritivos ("sprint" em vez da funcionalidade)
- Frontend tests testam funções isoladas, não comportamento integrado (ex: não testam submitForm, renderForm, loadQuizList)

### Casos não cobertos

- Concorrência (dois usuários submitando ao mesmo tempo)
- Upload de arquivos (não existe, mas OK)
- Testes de stress/performance
- Testes de migração (alembic upgrade/downgrade)
- Testes de rollback em caso de falha
- Testes de CORS e TrustedHost (headers)

### Testes frágeis

- `test_forgot_password_development_logs_url` depende de `logger.info` ser chamado com formato específico — quebra se o log for refatorado
- `test_badges_first_quiz` comparando `initial_badges` com `len(resp2["badges"])` — frágil se badges forem adicionados no seed

---

## 6. Observabilidade

### Logging — `8/10`

- Logger configurado com `request_id` via `ContextVar`
- Formato estruturado JSON ou texto (configurável)
- `RequestIdFilter` injeta request_id em todos os registros
- Logs em endpoints críticos (login, register, quiz CRUD, admin actions)

**Falta:** Logs estruturados seguindo padrão (ex: OpenTelemetry), sem correlação entre serviços (ok, é monolito).

### Request Tracking — `9/10`

- UUID v4 por request via middleware
- Header `X-Request-ID` em todas as respostas (inclusive erros)
- Testado (test_sprint145)

### Health Checks — `8/10`

- `GET /health`: status, db health, db type, versão, uptime, ambiente
- `GET /health/database`: conexão com o banco (com redação de senha na URL)
- Docker HEALTHCHECK usando `/health`

### Métricas — `6/10`

- `GET /metrics`: uptime, total_users, total_quizzes, total_submissions, db type, versão
- **Não há métricas de performance** (latência p50/p95/p99, taxa de erro, throughput)
- **Não há métricas de negócio** (quizzes criados/hora, taxa de conversão)
- Não expõe métricas no formato Prometheus

### Monitoramento futuro

- Adicionar `prometheus-fastapi-instrumentator` para métricas automáticas
- Exportar métricas no formato Prometheus (`/metrics` compatível)
- Adicionar tracing com OpenTelemetry
- Logs centralizados (ex: Grafana Loki)

---

## 7. DevOps

### Docker — `8/10`

- Dockerfile multi-stage (builder + runtime) — **excelente**
- Usuário não-root (`quizapp`) — segurança
- `HEALTHCHECK` configurado
- `--proxy-headers --forwarded-allow-ips='*'` no uvicorn

**Melhorias:** Usar `gunicorn + uvicorn workers` em vez de `uvicorn` direto para produção.

### Docker Compose — `8/10`

- `docker-compose.yml` para dev com PostgreSQL + app
- `docker-compose.prod.yml` com nginx + certbot + postgres
- Healthchecks entre serviços
- Logging configurado (json-file, max-size)

**Negativo:** `SECRET_KEY=change-me` e `REFRESH_SECRET_KEY=change-me-too` em dev — fraco mas aceitável para dev local.

### CI/CD — `9/10`

- GitHub Actions com 3 jobs paralelos: lint, test-backend, test-frontend
- Ruff para lint
- Cobertura mínima de 80%
- Node.js 20 para frontend tests

### Deploy — `8/10`

- `render.yaml` configura deploy no Render com PostgreSQL
- Secrets gerados automaticamente (SECRET_KEY, REFRESH_SECRET_KEY)
- `Procfile` presente
- `init-db.sh` no entrypoint do PostgreSQL

### Configuração para produção

- Nginx com SSL (Let's Encrypt via certbot), HSTS, gzip, cache de estáticos
- Headers de segurança no nginx
- `ALLOWED_HOSTS` validado em produção
- `CORS_ORIGINS` validado em produção

---

## 8. Frontend

### Organização do JavaScript — `6/10`

Arquivos soltos carregados via `<script>` tags:
- `auth.js` — autenticação, API helpers
- `script.js` — página principal
- `toast.js` — notificações
- `theme.js` — tema dark/light

**Positivo:** Separação por responsabilidade, `Toast` e `Theme` como objetos namespaced.  
**Negativo:** Sem módulos ES6 (pacote.json tem `"type": "module"` mas JS não usa `import`/`export` — exceto nos testes). Variáveis globais vazando entre scripts (`currentQuiz`, `currentUser`).

### Reutilização de componentes — `4/10`

Não há componentes reutilizáveis. Cada página (`dashboard.html`, `admin.html`, `manage.html`, `quiz-editor.html`) tem seu próprio JS inline ou scripts dedicados. Não há framework (React, Vue, Svelte).

### Escalabilidade da estrutura atual — `3/10`

- HTML estático para cada página (dashboard, admin, leaderboard, etc.)
- Sem roteamento SPA — cada página é carregamento completo
- JS não modularizado — difícil testar e manter
- Crescimento levaria a duplicação massiva

### Melhorias recomendadas

1. Adotar bundler (Vite) com suporte a módulos ES6
2. Refatorar para estrutura de componentes (pode ser vanilla com `web-components` ou adotar framework leve)
3. Usar `import`/`export` nos JS (já que `package.json` define `"type": "module"`)
4. Consistência: `auth.js` usa `const AUTH_API = ''` (hardcoded), deveria vir de configuração

---

## 9. Performance

### Consultas ao banco — `6/10`

Principais problemas:
1. **`/admin/dashboard`**: Query separada por usuário para quiz_counts e sub_counts — O(n) para n usuários
2. **`/leaderboard`**: `GROUP BY` sem índice composto
3. **`/search`**: `ILIKE %term%` — full scan, não usa índice
4. **`/public_profile`**: ~6-8 queries independentes

### Paginação — `8/10`

Implementada em `/quizzes/search`, `/me/submissions`, `/leaderboard` com `page` e `limit` (capped a 100). Boa.

### Possíveis N+1 Queries

- `admin_dashboard`: "Busca todos usuários → para cada um, busca counts" — **N+1 clássico** (embora resolvido com `dict()` das agregações)
- `public_profile`: Múltiplas queries contando quizzes, submissions, ranking — não exatamente N+1, mas múltiplas idas ao banco

### Oportunidades de cache

1. **Leaderboard**: Cache com TTL de 30s (dificilmente muda em tempo real)
2. **Dashboard**: Cache de métricas por usuário
3. **Categories/Tags**: Cache praticamente estático
4. **Seed quizzes**: Cache em memória (nunca mudam)
5. **Adicionar `Cache-Control` headers** nos endpoints apropriados

---

## 10. Qualidade de Engenharia

### Boas práticas aplicadas ✅

- Type hints (Python)
- Pydantic models para validação
- SQLAlchemy 2.0 style (selectinload, declarative models)
- Testes automatizados com cobertura
- Refresh token rotation
- Password hashing com bcrypt
- Rate limiting
- Security headers
- Health checks
- Docker multi-stage
- CI/CD com lint + tests
- Estrutura de projeto profissional (scripts, deploy, docs)
- Uso de `__future__` annotations
- Alembic migrations

### Débito técnico existente

1. `main.py` com 917 linhas — **urgente refatorar**
2. Lógica de negócio inline nas rotas
3. Rate limit in-memory
4. Frontend monolithic sem bundler
5. `body: dict` em admin route
6. Nomes de testes "sprint" sem significado semântico
7. Seed data hardcoded
8. `REFRESH_SECRET_KEY` definido mas não usado (apenas SECRET_KEY é usada para JWT)

---

## 11. Avaliação Profissional

### Pontos que chamariam atenção positivamente ✨

1. **Refresh token rotation** — raro ver em projetos de portfólio, demonstra maturidade em segurança
2. **Logging estruturado com request_id** — excelente para observabilidade
3. **Docker multi-stage** — preocupação com tamanho de imagem e segurança
4. **CI/CD com cobertura mínima** — profissionalismo
5. **Testes de segurança** (token leak, timing attack, env-specific) — vai além do CRUD básico
6. **Health checks + métricas** — prontidão para produção
7. **Documentação de arquitetura** — mostra capacidade de comunicação técnica
8. **Alembic migrations** — evolução do schema controlada

### Pontos que demonstram maturidade 🧠

- Uso de `ContextVar` para request_id (assíncrono-safe)
- Uso de `selectinload` vs `joinedload` (consciente de performance)
- Validação de ambiente em produção (CORS, SECRET_KEY, ALLOWED_HOSTS)
- Const-time password comparison (dummy hash no login)
- Mesma mensagem para email existente/inexistente (anti-enumeration)

### Pontos que denunciam falta de experiência 🚩

1. **`main.py` monolítico (917 linhas)** — típico de quem ainda não aprendeu a separar responsabilidades
2. **`body: dict` em vez de Pydantic** — inconsistência no próprio código
3. **Nomes de testes não semânticos** (`test_sprint13`, `test_sprint141`) — indica que o candidato nomeia por "sprint" em vez de funcionalidade
4. **Frontend sem modularização** — JS global, sem bundler, HTML para cada página
5. **Rate limit in-memory** — não escala, não funciona com workers múltiplos
6. **Seed quizzes hardcoded e extensos** — deveriam vir de fixture separada
7. **`REFRESH_SECRET_KEY` definido mas não usado** — configuração "morta" indica falta de revisão

### Nível estimado do projeto

**Júnior avançado / Pleno inicial**

O projeto demonstra conhecimento sólido de Python, FastAPI, SQLAlchemy e segurança, mas peca na organização arquitetural (monolito) e no frontend. É claramente superior ao "CRUD com autenticação" típico de projetos iniciantes, mas ainda não atinge o nível de um pleno consolidado que estruturaria em camadas desde o início.

### Comparação com média

**ACIMA DA MÉDIA** para alguém buscando primeira oportunidade.

A maioria dos candidatos apresenta projetos com:
- CRUD sem autenticação ou com JWT básico
- Zero testes
- Zero Docker
- Zero CI/CD
- Zero headers de segurança
- Zero refresh token

Este projeto entrega **todos esses diferenciais**, além de features avançadas como refresh token rotation, rate limiting, logging estruturado, health checks, métricas, RBAC, badges e leaderboard.

---

## 12. Roadmap Priorizado

### 🔴 ALTA PRIORIDADE

| Item | Benefício | Complexidade | Aprendizado | Impacto Profissional |
|------|-----------|-------------|-------------|---------------------|
| **Separar `main.py` em `routes/`** | Código organizado, manutenível, testável | Média | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Extrair services layer** | Lógica de negócio testável isoladamente | Média | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Rate limit com Redis** | Escalabilidade real, múltiplos workers | Alta | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Adicionar rate limit no forgot-password** | Segurança contra bruteforce | Baixa | ⭐⭐ | ⭐⭐⭐⭐ |
| **Substituir `body: dict` por Pydantic** | Consistência, validação automática | Baixa | ⭐⭐⭐ | ⭐⭐⭐ |

### 🟡 MÉDIA PRIORIDADE

| Item | Benefício | Complexidade | Aprendizado | Impacto Profissional |
|------|-----------|-------------|-------------|---------------------|
| **Adicionar tests de integração com PostgreSQL em CI** | Detectar diferenças de dialeto | Média | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Adicionar Prometheus metrics** | Métricas de performance, monitoramento real | Média | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Cache de leaderboard** | Performance, escala | Média | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Refatorar testes "sprint" para nomes semânticos** | Clareza, manutenção | Baixa | ⭐⭐ | ⭐⭐⭐ |
| **Adoptar frontend bundler (Vite)** | Modularização, build, HMR | Média | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Criar endpoints admin como router separado** | Organização, segurança | Baixa | ⭐⭐⭐ | ⭐⭐⭐ |

### 🟢 BAIXA PRIORIDADE

| Item | Benefício | Complexidade | Aprendizado | Impacto Profissional |
|------|-----------|-------------|-------------|---------------------|
| **Adicionar `jti` nos access tokens** | Revogação de tokens específicos | Alta | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Migrar frontend para componentes web** | Reutilização, manutenção | Alta | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Implementar scoring real** (resposta correta/incorreta) | Valor do produto | Média | ⭐⭐⭐ | ⭐⭐⭐ |
| **Adicionar testes de concorrência** | Robustez | Alta | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Armazenar perguntas normalizadas** | Consultas analíticas | Alta | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Configurar gunicorn + uvicorn workers** | Performance em produção | Baixa | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Notas Finais

| Categoria | Nota (0-10) |
|-----------|:-----------:|
| **Arquitetura** | 7.0 |
| **Segurança** | 8.0 |
| **Testes** | 8.5 |
| **DevOps** | 8.5 |
| **Qualidade Geral** | 7.5 |

**Nível estimado do projeto:** Júnior avançado — **acima da média** para primeira oportunidade.

> **Resumo para recrutador:** Candidato demonstra domínio de Python/FastAPI, práticas de segurança (refresh token rotation, bcrypt, rate limiting), testes automatizados com cobertura, Docker, CI/CD e preocupação com produção (health checks, métricas, logging estruturado). Principais pontos de melhoria: organização arquitetural (monolito de 917 linhas) e frontend não modularizado. Projeto sólido para primeiro emprego.
