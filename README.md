# Quiz App

Aplicação full-stack de formulários e quizzes com autenticação JWT, CRUD completo, dashboard analítico com métricas, sistema de badges, leaderboard, busca, categorias/tags, recuperação de senha em modo demonstração (sem SMTP), controle de acesso por papéis (RBAC), rate limiting, logging estruturado, request ID tracking, endpoint de métricas, health check expandido e deploy automatizado no Render.

> O sistema foi simplificado para um modelo de portfólio totalmente funcional, removendo dependências externas críticas como SMTP.

## Funcionalidades

- Registro e login de usuários com bcrypt
- Sessões com refresh token rotation e revogação
- CRUD de quizzes com 4 tipos de pergunta: texto, múltipla escolha, escolha única, avaliação (rating)
- Submissão de respostas com validação e scoring automático
- Histórico completo de submissões com paginação
- Dashboard com métricas e estatísticas (7 e 30 dias)
- Sistema de badges (Primeiro Quiz, Perfeccionista, Criador, Quizzeiro, Veterano)
- Leaderboard global e por quiz
- Perfil público com quizzes criados, badges e ranking
- Busca textual em quizzes com paginação
- Categorias e tags para organização de quizzes
- Recuperação de senha em modo demonstração
- RBAC (admin/user) com endpoints administrativos
- Rate limiting (login: 10/min, registro: 5/h)
- Headers de segurança (HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- Request ID tracking (UUID + header X-Request-ID)
- Logs estruturados (texto ou JSON) com request_id
- Endpoint de métricas (`GET /metrics`)
- Health check expandido (`GET /health`)
- Seed de quizzes padrão na primeira execução
- SQL aggregation refactor (performance: de O(N) para O(1) em agregações)
- Testes automatizados com cobertura mínima de 90%
- CI/CD com GitHub Actions
- Deploy automatizado no Render via Blueprints

## Stack

| Componente | Tecnologia |
|------------|-----------|
| **Backend** | Python 3.9+ / FastAPI |
| **Frontend** | HTML5 + CSS3 + JavaScript (vanilla) |
| **Autenticação** | JWT (access token 15min + refresh token 7 dias com rotação) |
| **ORM** | SQLAlchemy 2.0 |
| **Migrações** | Alembic |
| **Banco (dev)** | SQLite |
| **Banco (prod)** | PostgreSQL 16 |
| **Hashing** | bcrypt (senhas) / SHA-256 (tokens) |
| **Testes** | pytest + pytest-cov |
| **CI/CD** | GitHub Actions |
| **Deploy** | Render (Web Service + PostgreSQL) |
| **Container** | Docker + Docker Compose |

## Arquitetura

```
Frontend (HTML/CSS/JS)
       ↓
   FastAPI (Middleware: Request ID, Timing, CORS, Rate Limit)
       ↓
 Auth Layer (JWT + bcrypt + Refresh Token Rotation)
       ↓
 Business Layer (CRUD, Dashboard, Ranking, Leaderboard, Badges)
       ↓
  SQLAlchemy 2.0 ORM (selectinload, aggregation)
       ↓
 SQLite (dev) / PostgreSQL 16 (prod)
```

[Diagrama de arquitetura detalhado](backend/docs/architecture-diagram.md) | [Documentação de arquitetura](backend/docs/architecture.md)

## Estrutura do Projeto

```
quiz-app/
├── backend/
│   ├── Dockerfile
│   ├── alembic/
│   │   ├── versions/        # Migrações (8 arquivos)
│   │   └── env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py          # FastAPI app + middleware + lifespan
│   │   ├── core/
│   │   │   ├── config.py    # Variáveis de ambiente
│   │   │   ├── dependencies.py  # Auth + RBAC deps
│   │   │   └── security.py  # JWT + bcrypt + refresh tokens
│   │   ├── models/
│   │   │   └── database.py  # SQLAlchemy models + seed data
│   │   ├── schemas/
│   │   │   └── models.py    # Pydantic schemas
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── quiz_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── leaderboard_service.py
│   │   │   ├── admin_service.py
│   │   │   └── email_service.py  # LEGACY (não utilizado — modo demo)
│   │   ├── routers/
│   │   │   ├── auth.py, quizzes.py, dashboard.py, leaderboard.py
│   │   │   ├── admin.py, profile.py, categories.py, health.py
│   │   ├── middleware/
│   │   │   └── rate_limit.py
│   │   └── utils/
│   │       └── logging.py
│   ├── docs/                # Documentação de arquitetura
│   │   ├── architecture.md
│   │   ├── architecture-diagram.md
│   │   └── json-scalability-analysis.md
│   ├── tests/               # 168 testes automatizados
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_quizzes.py
│   │   ├── test_submissions.py
│   │   ├── test_dashboard.py
│   │   ├── test_leaderboard.py
│   │   ├── test_rbac.py
│   │   ├── test_search.py
│   │   ├── test_categories.py
│   │   ├── test_password_reset.py
│   │   ├── test_refresh_tokens.py
│   │   ├── test_health.py
│   │   ├── test_sprint13.py
│   │   ├── test_sprint141.py
│   │   ├── test_sprint142.py
│   │   ├── test_sprint145.py
│   │   └── test_email_service.py
│   ├── templates/
│   │   ├── password_reset.html
│   │   └── password_reset.txt  # LEGACY (não utilizados — modo demo)
│   ├── main.py              # Wrapper (importa app.main)
│   ├── database.py          # Re-export (app.models.database)
│   ├── config.py            # Re-export (app.core.config)
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Lista de quizzes + formulário
│   ├── dashboard.html       # Métricas e estatísticas
│   ├── history.html         # Histórico de submissões
│   ├── manage.html          # Gerenciamento de quizzes
│   ├── quiz-editor.html     # Criar/editar quizzes
│   ├── admin.html           # Painel administrativo
│   ├── leaderboard.html     # Leaderboard
│   ├── profile.html         # Perfil público
│   ├── login.html           # Login
│   ├── register.html        # Registro
│   ├── forgot-password.html # Recuperação de senha (modo demo)
│   ├── reset-password.html  # Redefinição de senha
│   ├── auth.js              # Central de autenticação
│   ├── script.js            # Lógica do index
│   └── style.css            # Estilos globais
├── docker-compose.yml         # Desenvolvimento
├── deploy/
│   └── nginx/
│       └── nginx.conf         # Reverse proxy + SSL + gzip
├── scripts/
│   ├── backup_postgres.sh     # Backup PostgreSQL com rotação
│   └── restore_postgres.sh    # Restore com confirmação
├── docs/
│   ├── deployment.md          # Guia completo de deploy
│   ├── monitoring.md          # Healthcheck + métricas + alertas
│   └── https.md               # Let's Encrypt + Certbot
├── .env.example
├── Procfile
├── pyproject.toml
├── render.yaml
└── README.md
```

## Endpoints da API

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/register` | Registrar novo usuário |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Renovar access token |
| POST | `/auth/logout` | Revogar refresh token |
| GET | `/auth/sessions` | Listar sessões ativas |
| DELETE | `/auth/sessions/{id}` | Revogar sessão |
| GET | `/auth/me` | Dados do usuário logado |
| POST | `/auth/forgot-password` | Solicitar reset de senha |
| POST | `/auth/reset-password` | Redefinir senha |

### Quizzes
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/quizzes` | Listar quizzes (públicos + próprios) |
| GET | `/quizzes/search?q=` | Buscar quizzes |
| GET | `/quizzes/{id}` | Detalhes do quiz |
| POST | `/quizzes` | Criar quiz (admin) |
| PUT | `/quizzes/{id}` | Atualizar quiz (criador) |
| DELETE | `/quizzes/{id}` | Remover quiz (criador) |
| POST | `/quizzes/{id}/submit` | Submeter respostas |
| GET | `/me/quizzes` | Listar quizzes do usuário |
| GET | `/me/submissions` | Histórico de submissões |

### Dashboard
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/me/dashboard` | Métricas consolidadas |
| GET | `/me/stats` | Estatísticas por período (7/30 dias) |

### Leaderboard
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/leaderboard` | Ranking global |
| GET | `/quizzes/{id}/leaderboard` | Ranking por quiz |

### Perfil
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/users/{id}/profile` | Perfil público com badges |

### Categorias e Tags
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/categories` | Listar categorias |
| GET | `/tags` | Listar tags |

### Admin
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/dashboard` | Painel admin (usuários, quizzes, submissões) |
| GET | `/admin/users` | Listar todos os usuários |
| PUT/PATCH | `/admin/users/{id}/role` | Alterar papel do usuário |

### Observabilidade
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status da aplicação (expandido) |
| GET | `/health/database` | Conectividade do banco |
| GET | `/metrics` | Métricas (uptime, versão, totais) |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SECRET_KEY` | `super-secret-key-mude-em-producao` | Chave JWT access token |
| `REFRESH_SECRET_KEY` | `super-refresh-secret-mude-em-producao` | Chave JWT refresh token |
| `DATABASE_URL` | `sqlite:///./quiz.db` | URL do banco de dados |
| `CORS_ORIGINS` | `*` | Origens permitidas (separadas por vírgula) |
| `ALLOWED_HOSTS` | `*` | Hosts permitidos (obrigatório em produção) |
| `ENVIRONMENT` | `development` | `development` ou `production` |
| `LOG_LEVEL` | `INFO` | Nível de log (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Formato do log (`text` ou `json`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Expiração do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Expiração do refresh token |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Máx tentativas de login/minuto |
| `RATE_LIMIT_REGISTER_PER_HOUR` | `5` | Máx registros/hora |
| `ADMIN_EMAILS` | `admin@example.com` | Emails que viram admin no registro |
| `ADMIN_EMAIL` | `` | Email para criação automática de admin |
| `ADMIN_PASSWORD` | `` | Senha para criação automática de admin |
| `PORT` | `8000` | Porta do servidor |
| `SMTP_HOST` | `` | LEGACY — não utilizado (modo demo) |
| `SMTP_PORT` | `587` | LEGACY — não utilizado (modo demo) |
| `SMTP_USERNAME` | `` | LEGACY — não utilizado (modo demo) |
| `SMTP_PASSWORD` | `` | LEGACY — não utilizado (modo demo) |
| `SMTP_FROM` | `noreply@quizapp.com` | LEGACY — não utilizado (modo demo) |
| `SMTP_USE_TLS` | `true` | LEGACY — não utilizado (modo demo) |
| `SMTP_TIMEOUT` | `30` | LEGACY — não utilizado (modo demo) |

## Desenvolvimento Local

```bash
# 1. Clonar e entrar no diretório
git clone <repo>
cd quiz-app

# 2. Criar virtualenv
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# 3. Instalar dependências
pip install -r backend/requirements.txt

# 4. Executar migrações
cd backend
alembic upgrade head

# 5. Iniciar servidor (com reload)
uvicorn main:app --reload --port 8000

# 6. Acessar
# http://localhost:8000
```

O banco SQLite (`backend/quiz.db`) é criado automaticamente na primeira execução com dados seed (4 quizzes + 1 quiz de tecnologia).

## Password Reset (Modo Demonstração)

O sistema opera em **modo demonstração** para recuperação de senha. O sistema não envia e-mails em nenhuma condição (produção ou desenvolvimento) — não depende de SMTP ou qualquer serviço externo de e-mail.

### Fluxo

1. Usuário solicita redefinição → `POST /auth/forgot-password`
2. Token SHA-256 gerado com validade de **1 hora** e armazenado no banco
3. A API retorna o campo `reset_url` diretamente na resposta
4. O frontend exibe o link de reset para o usuário na tela
5. Usuário acessa link → `POST /auth/reset-password` com nova senha
6. Token marcado como `used` — reutilização bloqueada

### Exemplo de requisição

```bash
# Solicitar reset (usuário existente → reset_url preenchido)
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com"}'

# Resposta:
# {
#   "message": "Se o email existir, instruções foram enviadas.",
#   "reset_url": "/static/reset-password.html?token=1c85967f2048..."
# }

# Usuário inexistente → reset_url é null (proteção contra enumeração)
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "inexistente@example.com"}'

# Resposta:
# {
#   "message": "Se o email existir, instruções foram enviadas.",
#   "reset_url": null
# }

# Redefinir senha com o token recebido
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token": "1c85967f2048...", "new_password": "NovaSenha@123"}'

# Resposta:
# { "message": "Senha redefinida com sucesso." }
```

### Observações

- O token também é logado no servidor para facilitar testes locais (`logger.info`)
- A mensagem de resposta é idêntica para usuário existente e inexistente (proteção contra enumeração de e-mail)
- O fluxo é **100% funcional** sem dependência de SMTP, serviços de e-mail ou configuração externa
- Em produção (Render), o `reset_url` usará o domínio configurado via `FRONTEND_URL`

## Docker

```bash
# 1. Copiar arquivo de ambiente
cp .env.example .env

# 2. Build e iniciar
docker compose up --build

# 3. Parar
docker compose down

# 4. Logs
docker compose logs -f

# 5. Remover containers + volume (apaga dados)
docker compose down -v
```

### Estrutura de inicialização

```
Docker Compose
│
├── PostgreSQL 16 (porta 5432)
│   ├── healthcheck: pg_isready
│   └── volume: postgres_data (persistência)
│
└── App FastAPI (porta 8000)
    ├── healthcheck: GET /health
    ├── depende de: postgres saudável
    ├── CMD: alembic upgrade head → uvicorn
    └── variáveis via .env / environment
```

## Executar Testes

```bash
# Todos os testes
cd backend && python -m pytest tests/ -v

# Com cobertura
cd backend && python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Cobertura mínima: 90% (falha automática abaixo)
```

## Executar Migrações

```bash
cd backend

# Criar nova migração
alembic revision --autogenerate -m "descricao"

# Aplicar migrações
alembic upgrade head

# Rollback (última)
alembic downgrade -1
```

## Deploy no Render

### Opção A — Blueprints (automático)

O arquivo `render.yaml` define o Web Service + PostgreSQL automaticamente:
1. Conecte o repositório no Render
2. Vá em **Blueprints** → **New Blueprint Print**
3. Selecione o repositório

### Opção B — Manual

- **Runtime:** Python
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

## Migração SQLite → PostgreSQL

A migração é transparente graças ao SQLAlchemy + Alembic:

```bash
# Configure DATABASE_URL com a connection string PostgreSQL
cd backend && alembic upgrade head
```

O seed de quizzes padrão é executado automaticamente na primeira inicialização.

## CI/CD

O workflow do GitHub Actions (`.github/workflows/tests.yml`):
- **Trigger:** push ou pull request para `main`
- **Passos:** Python 3.11 → instalar dependências → pytest com cobertura ≥ 90%
- **Falha:** qualquer teste falho ou cobertura < 90% interrompe o pipeline

## Cobertura de Testes

**Meta:** ≥ 90%
**Atual:** 90%+ (168 testes automatizados)

| Categoria | Testes | Status |
|-----------|--------|--------|
| Autenticação | `test_auth.py`, `test_refresh_tokens.py` | 99% |
| Quizzes | `test_quizzes.py`, `test_submissions.py`, `test_search.py` | 90% |
| Dashboard | `test_dashboard.py` | 100% |
| Leaderboard | `test_leaderboard.py` | 100% |
| RBAC | `test_rbac.py` | 100% |
| Password Reset | `test_password_reset.py` | 100% |
| Categories/Tags | `test_categories.py` | 100% |
| Health/Metrics | `test_health.py` | 100% |
| Performance | `test_sprint13.py`, `test_sprint141.py`, `test_sprint142.py`, `test_sprint145.py` | 100% |

## Roadmap

- [x] Autenticação JWT com refresh token rotation
- [x] CRUD de quizzes com 4 tipos de pergunta
- [x] Dashboard com métricas e estatísticas
- [x] Admin panel com RBAC
- [x] CI/CD com GitHub Actions
- [x] Deploy no Render
- [x] Categorias e tags
- [x] Busca textual em quizzes
- [x] Leaderboard global e por quiz
- [x] Perfil público com badges e ranking
- [x] Recuperação de senha (modo demo, sem SMTP)
- [x] Performance: SQL aggregation refactor
- [x] Observabilidade: request ID, metrics, structured logging
- [ ] Cache com Redis (próximo sprint)
- [ ] Modo escuro no frontend
- [ ] WebSockets para quizzes ao vivo

## Licença

MIT
