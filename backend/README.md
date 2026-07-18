# Behavior Hub — Backend (Fase 1 / MVP)

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

## Testes

```bash
source .venv/bin/activate
export DATABASE_URL="postgresql+psycopg://behavior_hub:behavior_hub@localhost:5432/behavior_hub_test"
pytest -q
```

Os testes usam uma transação com SAVEPOINT por teste (não sujam o banco entre testes) e não dependem
dos dados de seed da Training Library — cada teste cria sua própria categoria/treino quando precisa.

## Nota sobre a Training Library (Seção 12.1 do PRD)

O PRD pede ~20 treinos por categoria + 15 adicionais, **clinicamente revisados antes de produção**.
A migração `94f27f468fdb_seed_training_library_starter_data.py` entrega um conjunto inicial (6
categorias × 8 treinos = 48 treinos de sistema) suficiente para exercitar o fluxo de coleta de ponta
a ponta na Fase 1. Este conjunto **não** substitui a curadoria clínica completa exigida pelo PRD —
antes de qualquer uso em produção real, um profissional habilitado deve revisar, expandir e aprovar
o conteúdo de cada treino.

## Estrutura

- `app/models/` — entidades SQLAlchemy (Seção 18 do PRD).
- `app/services/` — regras de negócio (isolamento de tenant, soft delete, cálculos da Seção 14.4 etc).
- `app/api/v1/` — rotas FastAPI.
- `app/tasks/` — Celery (worker + beat), incluindo a purga diária de Dados Excluídos após 60 dias
  (Seção 16.2).
- `alembic/versions/` — migrações versionadas.
- `tests/` — pytest (unitários + integração + isolamento multi-tenant).
