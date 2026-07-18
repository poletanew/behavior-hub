# Behavior Hub — Backend (Fase 1 + Fase 2)

FastAPI + SQLAlchemy + Alembic + PostgreSQL. Ver o [README raiz](../README.md) para como subir o
ambiente completo com Docker Compose.

## Desenvolvimento local sem Docker

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuste DATABASE_URL/REDIS_URL se necessário
alembic upgrade head
uvicorn app.main:app --reload
```

Fase 2 requer a extensão `pg_trgm` do PostgreSQL (usada na detecção de objetivos duplicados —
Seção 13.2); a migração `e52a0826e753_...` já cria a extensão automaticamente (`CREATE EXTENSION IF
NOT EXISTS pg_trgm`), não é necessário nenhum passo manual.

## Testes

```bash
source .venv/bin/activate
export DATABASE_URL="postgresql+psycopg://behavior_hub:behavior_hub@localhost:5432/behavior_hub_test"
pytest -q
```

Os testes usam uma transação com SAVEPOINT por teste (não sujam o banco entre testes) e não dependem
dos dados de seed da Training Library — cada teste cria sua própria categoria/treino quando precisa.

Os testes de Recursos Terapêuticos (`tests/test_resources.py`) usam a biblioteca `moto` para mockar
o S3 (fixture `mock_s3` em `tests/conftest.py`) — não é necessário ter MinIO rodando para testar o
upload/download. Contra o MinIO real do `docker compose`, o mesmo código funciona sem alteração.

## Nota sobre a Training Library (Seção 12.1 do PRD)

O PRD pede ~20 treinos por categoria + 15 adicionais, **clinicamente revisados antes de produção**.
A migração `94f27f468fdb_seed_training_library_starter_data.py` entrega um conjunto inicial (6
categorias × 8 treinos = 48 treinos de sistema) suficiente para exercitar o fluxo de coleta de ponta
a ponta na Fase 1. Este conjunto **não** substitui a curadoria clínica completa exigida pelo PRD —
antes de qualquer uso em produção real, um profissional habilitado deve revisar, expandir e aprovar
o conteúdo de cada treino.

## Nota sobre o resumo de Reports (Seção 14.5 do PRD)

Combinado com o Product Owner: nenhuma chamada a uma API de IA externa foi integrada nesta fase.
`app/services/report_summary_service.py` gera um rascunho **determinístico** (baseado nos dados
agregados, não em um modelo de linguagem), sempre rotulado como tal (`generated_by:
"rule_based_draft"`), com o mesmo fluxo de edição/aprovação/versionamento que uma IA real usaria.
Quando o provedor de IA (Anthropic, OpenAI, etc.) for definido, a única peça a trocar é a função
`_draft_text` — o schema, a API e o frontend já estão prontos para receber texto gerado por IA no
mesmo formato.

## Nota sobre Recursos Terapêuticos (Seção 15/34 do PRD)

O limite de tamanho de arquivo (10MB) e os tipos aceitos (PDF, PNG/JPEG/WEBP, texto simples) em
`app/services/resource_service.py` são um padrão conservador de engenharia. A Seção 34 do PRD lista
"regras de armazenamento e tamanho de arquivos" como pendente de confirmação do Product Owner —
ajuste `MAX_SIZE_BYTES`/`ALLOWED_CONTENT_TYPES` quando essa decisão for confirmada.

## Nota sobre Notificações e Templates de Sessão (Seção 32.4/32.6/32.13)

`app/services/notification_service.py` cobre comentários novos em objetivos e menções (@) diretas —
sempre validando que o usuário mencionado pertence ao mesmo tenant do paciente antes de notificar.
`app/services/session_template_service.py` cobre "salvar como modelo" a partir de uma sessão
existente, iniciar uma sessão a partir de um modelo, e duplicar a sessão anterior do mesmo paciente.
Alertas clínicos (Seção 29.9) e faturas (Seção 8) ainda não existem no produto, então não alimentam
a Central de Notificações nesta fase — apenas comentários e menções, que são as únicas fontes reais
disponíveis hoje.

## Estrutura

- `app/models/` — entidades SQLAlchemy (Seção 18/27 do PRD).
- `app/services/` — regras de negócio (isolamento de tenant, soft delete, cálculos da Seção 14.4,
  detecção de duplicidade da Seção 13.2, upload S3 via `file_service.py`, etc).
- `app/api/v1/` — rotas FastAPI.
- `app/tasks/` — Celery (worker + beat), incluindo a purga diária de Dados Excluídos após 60 dias
  (Seção 16.2) — agora cobrindo pacientes, objetivos de plano de tratamento excluídos isoladamente e
  recursos terapêuticos.
- `alembic/versions/` — migrações versionadas.
- `tests/` — pytest (unitários + integração + isolamento multi-tenant).
