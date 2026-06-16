# Guia de Deploy — Quiz App

## Requisitos de Produção

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 vCPU | 2 vCPUs |
| RAM | 1 GB | 2 GB |
| Disco | 10 GB | 20 GB (SSD) |
| Docker | 24+ | 27+ |
| Docker Compose | 2.20+ | 2.29+ |
| Domínio | — | FQDN com registro A |

## Deploy com Docker

### 1. Preparar ambiente

```bash
# Clonar repositório
git clone https://github.com/seuuser/quiz-app.git
cd quiz-app

# Variáveis de ambiente
cp .env.example .env.prod
# Editar .env.prod com valores reais
```

### 2. Configurar variáveis obrigatórias

```bash
# Editar .env.prod:
ENVIRONMENT=production

# Banco de dados
POSTGRES_PASSWORD=<senha-forte-aleatória>

# JWT
SECRET_KEY=<openssl rand -hex 32>
REFRESH_SECRET_KEY=<openssl rand -hex 32>

# Domínio
CORS_ORIGINS=https://quizapp.seudominio.com
ALLOWED_HOSTS=quizapp.seudominio.com,localhost

# Admin
ADMIN_EMAILS=admin@example.com
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<senha-admin>

# SMTP (obrigatório para recuperação de senha)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seuemail@gmail.com
SMTP_PASSWORD=<app-password>
SMTP_FROM=seuemail@gmail.com
```

### 3. Iniciar serviços

```bash
# Primeira vez: emitir certificado HTTPS
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d quizapp.seudominio.com \
  --email admin@example.com \
  --agree-tos

# Iniciar todos os serviços
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Verificar healthcheck
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs app --tail=20

# Verificar logs do Nginx
curl -k https://localhost/health
```

### 4. Verificar deploy

```bash
# Health check
curl https://quizapp.seudominio.com/health

# Métricas
curl https://quizapp.seudominio.com/metrics

# Frontend
curl -I https://quizapp.seudominio.com/static/index.html
```

## Deploy Manual (sem Docker)

### Backend

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Migrações
alembic upgrade head

# Iniciar com Gunicorn + Uvicorn
gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile -
```

### PostgreSQL

```bash
# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Criar banco e usuário
sudo -u postgres psql -c "CREATE USER quizapp WITH PASSWORD '<senha>';"
sudo -u postgres psql -c "CREATE DATABASE quizapp OWNER quizapp;"
```

## Upgrade de Versão

```bash
# 1. Backup
./scripts/backup_postgres.sh

# 2. Atualizar código
git pull origin main

# 3. Rebuild e restart
docker compose -f docker-compose.prod.yml build app
docker compose -f docker-compose.prod.yml up -d --force-recreate app

# 4. Verificar
docker compose -f docker-compose.prod.yml ps
curl https://quizapp.seudominio.com/health
```

## Rollback

```bash
# Reverter para versão anterior
git checkout <tag-anterior>

# Rebuild e restart
docker compose -f docker-compose.prod.yml build app
docker compose -f docker-compose.prod.yml up -d --force-recreate app

# Se houver migração de banco, restaurar backup primeiro
./scripts/restore_postgres.sh ./backups/quizapp_<data>.sql.gz
```

## Manutenção

### Rotina diária

```bash
# Verificar saúde
curl https://quizapp.seudominio.com/health

# Verificar logs de erro
docker compose -f docker-compose.prod.yml logs app --tail=50 --since=5m

# Verificar disco
df -h /var/lib/docker/volumes
```

### Rotina semanal

```bash
# Backup manual
./scripts/backup_postgres.sh

# Verificar certificado
docker compose -f docker-compose.prod.yml run --rm certbot certificates

# Verificar versão
curl -s https://quizapp.seudominio.com/health | python -m json.tool
```

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Container reiniciando | Healthcheck falhando | `docker compose logs app --tail=50` |
| Banco de dados lento | Falta índice | Verificar queries lentas no PostgreSQL |
| Certificado expirado | Certbot parou | `docker compose restart certbot` |
| 502 Bad Gateway | Backend fora do ar | `docker compose restart app` |
| 504 Gateway Timeout | Query lenta | Aumentar `proxy_read_timeout` no nginx.conf |
| SMTP não envia | Config incorreta | Verificar `.env.prod` — `docker compose logs app` |

## Checklist de Produção

- [ ] Domínio configurado com registro A
- [ ] HTTPS funcionando (Let's Encrypt)
- [ ] Variáveis SECRET_KEY fortes (openssl rand -hex 32)
- [ ] SMTP configurado e testado
- [ ] Backup automático configurado (cron)
- [ ] Healthcheck respondendo
- [ ] CORS_ORIGINS restrito ao domínio
- [ ] ALLOWED_HOSTS configurado
- [ ] PostgreSQL password forte
- [ ] Logs rotacionados (Docker json-file max-size)
- [ ] Firewall permitindo apenas 80/443
- [ ] Monitoramento de certificado (renovação automática)

## Preparedness Score

| Categoria | Status |
|-----------|--------|
| Containerização | ✅ Docker multi-stage + healthcheck |
| Revers Proxy | ✅ Nginx com caching e security headers |
| HTTPS | ✅ Let's Encrypt + renovação automática |
| Banco de dados | ✅ PostgreSQL + pg_isready |
| Backup | ✅ Script pg_dump + retenção 30 dias |
| Restore | ✅ Script pg_restore com confirmação |
| Monitoramento | ✅ /health + /metrics |
| Logs | ✅ Rotacionados, json-file driver |
| CI/CD | ✅ Lint + backend tests + frontend tests |
| Documentação | ✅ Deploy, upgrade, rollback, troubleshooting |
