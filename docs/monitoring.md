# Monitoramento

## Endpoints de Health Check

### `GET /health`

Verifica a saúde geral da aplicação.

**Resposta (200):**
```json
{
  "status": "healthy",
  "database": "healthy",
  "database_type": "postgresql",
  "version": "1.2.0",
  "uptime_seconds": 86400,
  "environment": "production",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**Uso:** Health check do Docker, load balancer, Render.

### `GET /health/database`

Verifica conexão com o banco de dados.

**Resposta (200):**
```json
{
  "status": "healthy",
  "database": "postgresql://<redacted>@postgres:5432/quizapp"
}
```

**Resposta (503):** Se a conexão falhar.

### `GET /metrics`

Métricas operacionais para monitoramento.

**Resposta (200):**
```json
{
  "uptime_seconds": 86400,
  "total_users": 150,
  "total_quizzes": 25,
  "total_submissions": 1200,
  "database": "postgresql",
  "version": "1.2.0"
}
```

## Alertas recomendados

| Métrica | Limite | Ação |
|---------|--------|------|
| Uptime < 60s | Critical | Container reiniciou — verificar logs |
| Database unhealthy | Critical | Verificar conexão PostgreSQL |
| Total de erros 5xx > 1% | Warning | Verificar logs do backend |
| Uso de disco > 80% | Warning | Limpar backups antigos, verificar volume |
| Certificado expira em < 7 dias | Warning | Verificar renovação Let's Encrypt |

## Logs

```bash
# Backend
docker compose -f docker-compose.prod.yml logs -f app

# Nginx (acessos e erros)
docker compose -f docker-compose.prod.yml logs -f nginx

# Todos os serviços
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

## Backup monitorado

Adicione ao crontab para backup automático diário:

```cron
0 3 * * * cd /opt/quiz-app && ./scripts/backup_postgres.sh >> /var/log/quizapp-backup.log 2>&1
```

Verificar status do último backup:

```bash
tail -5 /var/log/quizapp-backup.log
```
