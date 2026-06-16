# HTTPS com Let's Encrypt

## Primeira emissão

Execute o container certbot para emitir o certificado inicial:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d quizapp.seudominio.com \
  --email seuemail@exemplo.com \
  --agree-tos \
  --no-eff-email
```

Após a emissão, o Nginx carrega automaticamente o certificado no próximo restart:

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

## Renovação automática

O container `certbot` no `docker-compose.prod.yml` já executa renovação automática
a cada 12 horas. Para forçar renovação manual:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
```

## Verificação

```bash
# Verificar expiração do certificado
docker compose -f docker-compose.prod.yml run --rm certbot certificates

# Testar renovação (dry-run)
docker compose -f docker-compose.prod.yml run --rm certbot renew --dry-run
```

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| `Domain not found` | DNS não propagado | Verificar registro A no DNS |
| `Connection refused` | Porta 80 bloqueada | Verificar firewall / security group |
| `Rate limit exceeded` | Muitas tentativas | Aguardar 1 hora entre tentativas |
| Certificado expirou | Renovação falhou | Executar `certbot renew` manualmente |

## Certbot standalone (sem Docker)

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d quizapp.seudominio.com

# Testar renovação automática
sudo certbot renew --dry-run
```
