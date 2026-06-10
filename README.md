# Quiz App

Aplicação full-stack de formulários e quizzes com autenticação JWT, CRUD completo, dashboard analítico e deploy automatizado no Render.

## Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy 2.0
- **Frontend:** HTML puro + CSS + JavaScript (sem frameworks)
- **Autenticação:** JWT (access + refresh token com rotação)
- **Banco de dados:** SQLite (dev) / PostgreSQL 16 (prod)
- **Migrações:** Alembic
- **Deploy:** Render (Web Service + PostgreSQL)

## Funcionalidades

- Registro e login de usuários (bcrypt)
- Sessões com refresh token rotation e revogação
- CRUD de quizzes com 4 tipos de pergunta: texto, múltipla escolha, escolha única, avaliação (rating)
- Submissão de respostas com validação
- Histórico completo de submissões
- Dashboard com métricas e estatísticas (7 e 30 dias)
- Rate limiting (login: 10/min, registro: 5/h)
- Headers de segurança (HSTS, X-Content-Type-Options, etc.)
- Logs estruturados (texto ou JSON)
- Seed de quizzes padrão na primeira execução

## Estrutura do Projeto

```
quiz-app/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 0d2d4063362d_initial_schema.py
│   │   └── env.py
│   ├── alembic.ini
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_refresh_tokens.py
│   │   ├── test_quizzes.py
│   │   ├── test_submissions.py
│   │   ├── test_dashboard.py
│   │   └── test_health.py
│   ├── main.py          # Rotas da API + lifespan
│   ├── database.py      # Modelos SQLAlchemy + seed
│   ├── models.py        # Schemas Pydantic
│   ├── auth.py          # JWT + refresh + sessions
│   ├── config.py        # Variáveis de ambiente
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Lista de quizzes + formulário
│   ├── dashboard.html   # Métricas e estatísticas
│   ├── history.html     # Histórico de submissões
│   ├── manage.html      # Gerenciamento de quizzes
│   ├── quiz-editor.html # Criar/editar quizzes
│   ├── auth.js          # Central de autenticação
│   ├── script.js        # Lógica do index
│   └── style.css        # Estilos globais
├── Procfile
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

### Quizzes
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/quizzes` | Listar quizzes (públicos + próprios) |
| GET | `/quizzes/{id}` | Detalhes do quiz |
| POST | `/quizzes` | Criar quiz (autenticado) |
| PUT | `/quizzes/{id}` | Atualizar quiz (apenas criador) |
| DELETE | `/quizzes/{id}` | Remover quiz (apenas criador) |
| POST | `/quizzes/{id}/submit` | Submeter respostas |
| GET | `/me/quizzes` | Listar quizzes do usuário |
| GET | `/me/submissions` | Histórico de submissões |

### Dashboard
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/me/dashboard` | Métricas consolidadas |
| GET | `/me/stats` | Estatísticas por período |

### Health Check
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status da aplicação |
| GET | `/health/database` | Conectividade do banco |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SECRET_KEY` | `super-secret-key-mude-em-producao` | Chave JWT access token |
| `REFRESH_SECRET_KEY` | `super-refresh-secret-mude-em-producao` | Chave JWT refresh token |
| `DATABASE_URL` | `sqlite:///./quiz.db` | URL do banco de dados |
| `CORS_ORIGINS` | `*` | Origens permitidas (separadas por vírgula) |
| `ENVIRONMENT` | `development` | `development` ou `production` |
| `LOG_LEVEL` | `INFO` | Nível de log (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Formato do log (`text` ou `json`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Expiração do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Expiração do refresh token |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Máx tentativas de login/minuto |
| `RATE_LIMIT_REGISTER_PER_HOUR` | `5` | Máx registros/hora |
| `PORT` | `8000` | Porta do servidor |

## Desenvolvimento Local

```bash
# 1. Clonar e entrar no diretório
git clone <repo>
cd quiz-app

# 2. Criar virtualenv (opcional mas recomendado)
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# 3. Instalar dependências
pip install -r backend/requirements.txt

# 4. Executar migrações
cd backend
alembic upgrade head

# 5. Iniciar servidor
uvicorn main:app --reload --port 8000

# 6. Acessar
# http://localhost:8000
```

O banco SQLite (`backend/quiz.db`) é criado automaticamente na primeira execução com dados seed.

## Deploy no Render

### 1. Push para o GitHub

```bash
git add .
git commit -m "Sprint 7 — Deploy, Observabilidade e Operação"
git push origin main
```

### 2. Criar Web Service no Render

**Opção A — Usando `render.yaml` (Blueprints):**
- Conecte o repositório no Render
- Vá em **Blueprints** → **New Blueprint Print**
- Selecione o repositório
- O Render lerá `render.yaml` e criará o Web Service + PostgreSQL automaticamente

**Opção B — Manual:**
- **Web Service:**
  - Runtime: **Python**
  - Build Command: `pip install -r backend/requirements.txt`
  - Start Command: `cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
  - Variáveis: conforme tabela acima
- **PostgreSQL:** Adicione um banco PostgreSQL via Render Dashboard
  - A variável `DATABASE_URL` será injetada automaticamente

### 3. Configurar domínio / health check

- Path do health check: `/health`
- O Render usará este endpoint para verificar se a aplicação está no ar

## Migração SQLite → PostgreSQL

A migração é transparente graças ao SQLAlchemy + Alembic:

```bash
# 1. No Render, configure DATABASE_URL com a connection string PostgreSQL

# 2. O startCommand roda automaticamente:
cd backend && alembic upgrade head

# 3. A migration inicial (0d2d4063362d) cria todas as tabelas no PostgreSQL

# 4. O seed de quizzes padrão é executado automaticamente na primeira inicialização
```

**Pontos de atenção:**
- `check_same_thread` é usado apenas com SQLite (detectado automaticamente em `database.py`)
- `psycopg2-binary` está nas requirements para PostgreSQL
- JSON columns (`answers`, `questions`) funcionam nativamente em ambos bancos
- Refresh tokens expirados e quizzes com `user_id=NULL` (seed) são compatíveis com ambos

## Testes

### Pré-requisitos

```bash
pip install -r backend/requirements.txt
```

### Executar todos os testes

```bash
cd backend && python -m pytest tests/ -v
```

### Executar com cobertura

```bash
cd backend && python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

### Meta de cobertura

Mínimo de 80%. O CI falha automaticamente se a cobertura ficar abaixo deste limiar.

## CI/CD

### GitHub Actions

O repositório possui um workflow automatizado em `.github/workflows/tests.yml`:

- **Trigger:** `push` ou `pull_request` para `main`
- **Passos:**
  1. Checkout do código
  2. Setup do Python 3.11
  3. Instalação de dependências
  4. Execução de testes com `pytest --cov --cov-fail-under=80`
- **Falha:** Qualquer teste falho ou cobertura abaixo de 80% interrompe o pipeline

### Deploy (Render)

O deploy no Render é feito via `render.yaml` (Blueprints) ou manualmente. Consulte a seção "Deploy no Render" acima.

## Licença

MIT
