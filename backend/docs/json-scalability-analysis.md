# Análise de Escalabilidade — Armazenamento JSON de Perguntas

## Contexto

Atualmente, as perguntas de cada quiz são armazenadas em uma coluna `JSON`
(mapeada para `sqlite_JSON` / `JSONB` no PostgreSQL) na tabela `quizzes`:

```python
class QuizDB(Base):
    questions = Column(JSON, nullable=False)
```

## Vantagens do Modelo Atual

1. **Simplicidade de implementação** — não requer tabelas normalizadas para
   perguntas, opções ou tipos de resposta.
2. **Flexibilidade de schema** — cada quiz pode ter estruturas de perguntas
   diferentes (texto, múltipla escolha, rating) sem migrations.
3. **Performance de leitura** — uma única consulta carrega quiz + perguntas.
4. **Facilidade de seed** — dados de seed podem ser definidos como dicionários
   Python inline.

## Limitações

### Busca em perguntas (SQL-level)

Não é possível buscar texto dentro do conteúdo das perguntas usando SQL puro:

```sql
-- NÃO funciona sem funções específicas do dialect
SELECT * FROM quizzes WHERE questions->>'text' ILIKE '%python%';
```

No PostgreSQL seria possível com `jsonb` e operadores `@>`, `?`, mas:
- A query seria complexa
- Não haveria indexação adequada (`GIN` indexes seriam necessários)
- A migração para PostgreSQL exigiria reescrita das queries

### Analytics

Métricas como "quais perguntas são mais ignoradas" ou "taxa de acerto por
pergunta" exigem percorrer o JSON de cada submissão:

```python
# Atual — percorre todas as submissões em Python
for s in submissions:
    for ans in (s.answers or []):
        ...
```

Isso não escala com milhares de submissões.

### Integridade referencial

Não há FK constraints entre perguntas no JSON e respostas nas submissões. Um
bug no frontend poderia enviar `question_id` inexistente.

### Versionamento de perguntas

Se um quiz é editado após receber respostas, as perguntas antigas e novas se
misturam. Não há histórico de versões.

## Estratégia Futura Recomendada (sem alterar implementação atual)

### Fase 1 — Normalização parcial (próximo sprint)
Criar tabelas auxiliares apenas para analytics:

```sql
CREATE TABLE quiz_questions (
    id SERIAL PRIMARY KEY,
    quiz_id INT REFERENCES quizzes(id),
    question_order INT,
    question_text TEXT,
    question_type VARCHAR(20)
);
```

Migrar perguntas existentes via script one-shot.
Manter coluna `questions` JSON para leitura.

### Fase 2 — Normalização completa (quando necessário)
Quando a plataforma atingir escala que justifique:

1. Criar tabelas normalizadas: `questions`, `question_options`, `answers`
2. Migrar dados existentes
3. Remover coluna `questions` JSON
4. Atualizar endpoints para usar JOINs

### Fase 3 — Analytics em tempo real
Com dados normalizados, é possível:

- `COUNT(*)` de respostas por pergunta
- `AVG(rating)` sem percorrer JSON
- Indexar texto de perguntas para busca全文

## Impacto Atual

| Operação | Custo atual | Custo normalizado |
|---|---|---|
| Carregar quiz | 1 query | 1 query + JOINs |
| Listar quizzes | 1 query | 1 query |
| Buscar por título | Indexado (`ix_quizzes_title`) | Indexado |
| Buscar em perguntas | ❌ Não suportado | Indexado via GIN/trgm |
| Analytics de respostas | O(n) em Python | O(1) SQL agregado |
| Views count | Indexado (`ix_quizzes_views`) | Indexado |

## Conclusão

O modelo JSON atual é adequado para o estágio atual do projeto (dezenas de
quizzes, centenas de submissões). Para escala de produção (milhares de quizzes,
dezenas de milhares de submissões), recomenda-se a normalização gradual
descrita acima.

**Nenhuma alteração arquitetural foi feita neste sprint.** Esta análise é
apenas documentação para referência futura.
