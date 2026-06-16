# Architecture

## Visão Geral

O Quiz App é uma aplicação full-stack de formulários e quizzes com autenticação JWT, CRUD completo, dashboard analítico, sistema de badges, leaderboard e deploy automatizado. O backend segue uma arquitetura em camadas com FastAPI, SQLAlchemy 2.0 e suporte a SQLite (dev) / PostgreSQL (prod).

## Fluxo de Autenticação JWT

1. Usuário envia `email` + `password` para `POST /auth/login`
2. Servidor valida credenciais com bcrypt
3. Gera access token (JWT, 15min) + refresh token (opaco, 7 dias)
4. Access token é usado em requisições via header `Authorization: Bearer <token>`
5. Refresh token é armazenado com hash SHA-256 no banco para rotação/revogação

## Refresh Token Flow

- `POST /auth/refresh` recebe o refresh token atual
- Servidor valida hash, verifica expiração e revoga o token antigo
- Gera novo par access + refresh (rotação)
- Tokens revogados ou expirados não podem ser reutilizados
- `POST /auth/logout` revoga o refresh token ativo

## RBAC (Role-Based Access Control)

| Role | Criar Quiz | Editar/Excluir | Admin Dashboard | Gerenciar Usuários |
|------|-----------|---------------|----------------|-------------------|
| user | ❌ | ❌ | ❌ | ❌ |
| admin | ✅ | ✅ (próprios) | ✅ | ✅ |

- Admin pode promover/demover usuários via `PUT /admin/users/{id}/role`
- Admin não pode auto-demover (`400 Bad Request`)
- Registro com email em `ADMIN_EMAILS` ganha role `admin` automaticamente

## Ranking

- `_ranking_position(user_id, db)` calcula a posição global do usuário
- Baseado na soma total de `score` de todas as submissões
- Usa SQL aggregation: `COUNT` de usuários com score maior que o do usuário alvo
- Compatível com SQLite e PostgreSQL
- Retorna 0 se o usuário não tem submissões

## Leaderboard

- `GET /leaderboard` — ranking global com paginação
- `GET /quizzes/{id}/leaderboard` — ranking por quiz específico
- Agregações SQL com `SUM(score)`, `COUNT(submissions)`, `AVG(percentage)`
- Ordenação por score total descendente

## Recuperação de Senha

1. `POST /auth/forgot-password` — gera token de reset (hash SHA-256), válido por 1h
2. Mensagem idêntica para emails existentes ou não (evita enumeração)
3. `POST /auth/reset-password` — valida token, verifica expiração, atualiza senha
4. Token é marcado como `used` após uso (não reutilizável)
5. Token bruto nunca aparece nos logs

## Categorias e Tags

- Categorias: nome único + slug, associadas a quizzes via FK
- Tags: nome único, relação N:N com quizzes via tabela `quiz_tags`
- Endpoints: `GET /categories`, `GET /tags`
- Suporte a busca por tags em `GET /quizzes/search`
- Eager loading com `selectinload` para evitar N+1

## Observabilidade

### Request ID

- UUID único gerado por requisição no middleware
- Adicionado ao header `X-Request-ID` em todas as respostas
- Armazenado em `request.state.request_id` e em `ContextVar`
- Incluído em todos os logs via `RequestIdFilter`

### Métricas

- `GET /metrics` — uptime, total de usuários/quizzes/submissões, versão, tipo de banco

### Health Check

- `GET /health` — status, database, versão, uptime, environment
- `GET /health/database` — conectividade do banco (legado)

### Logging Estruturado

- Suporte a `LOG_FORMAT=text` (default) e `LOG_FORMAT=json`
- Inclui: timestamp, level, request_id, módulo, mensagem
- Rate limiting com GC automático a cada 5 minutos

## Diagrama de Camadas

```
Frontend (HTML/CSS/JS)
       ↓
   FastAPI (Middleware)
       ↓
 Auth Layer (JWT + bcrypt)
       ↓
 Business Layer (CRUD, Dashboard, Ranking)
       ↓
  SQLAlchemy 2.0 ORM
       ↓
 SQLite / PostgreSQL
```
