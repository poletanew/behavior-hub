# Behavior Hub

SaaS de gestão clínica multidisciplinar. Ver `docs/Behavior_Hub_PRD_v2_Completo.pdf` para o PRD
completo (fonte única de verdade do produto).

Este repositório está sendo construído **por fases**, seguindo o roadmap da Seção 31 do PRD. O estado
atual implementa a **Fase 1 — Core (MVP)**: autenticação, contas (clínica e individual), pacientes,
atribuições, sessões/atendimentos com tentativas individualizadas e uma Training Library básica.

## Stack (Seção 4 do PRD)

- Backend: Python + FastAPI, SQLAlchemy + Alembic, PostgreSQL
- Frontend: React + TypeScript + Tailwind CSS
- Fila/cache: Redis + Celery
- Arquivos: MinIO (S3 compatível) localmente
- Orquestração local: Docker Compose

## Subindo o ambiente local

Pré-requisito: Docker e Docker Compose instalados.

```bash
docker compose up --build
```

Isso sobe, com um único comando:

- **postgres** (porta 5432) — banco de dados.
- **redis** (porta 6379) — fila/cache.
- **minio** (portas 9000 API / 9001 console) — storage S3 compatível. Console em
  http://localhost:9001 (usuário/senha: `minioadmin` / `minioadmin`).
- **minio-init** — cria automaticamente o bucket `behavior-hub` e finaliza.
- **backend** (porta 8000) — API FastAPI. O container roda `alembic upgrade head` automaticamente
  antes de subir o servidor (ver `backend/entrypoint.sh`), então o banco já fica com o schema e a
  Training Library semeados na primeira subida.
- **celery-worker** / **celery-beat** — processam a purga diária de Dados Excluídos após 60 dias
  (Seção 16.2 do PRD) e demais tarefas assíncronas.
- **frontend** (porta 5173) — aplicação React.

Depois de subir:

- Frontend: http://localhost:5173
- API: http://localhost:8000 (documentação interativa em http://localhost:8000/docs)

Para derrubar o ambiente: `docker compose down` (adicione `-v` para também apagar os volumes de
dados).

## Testando localmente (Fase 1)

1. Acesse http://localhost:5173/register e crie uma conta de **Clínica** (ou **Profissional
   individual**).
2. Faça login. Confirme que o Dashboard, Pacientes e Atendimentos começam **completamente vazios**
   (Seção 6.1 do PRD — nenhuma conta nova tem dado fictício).
3. Em **Pacientes**, clique em **+ Adicionar paciente** e cadastre um paciente.
4. Abra o paciente e clique em **Novo Atendimento**: escolha data/hora e pelo menos um treino da
   Training Library (já vem com um conjunto inicial de treinos semeado — ver observação abaixo).
5. Na tela do atendimento, use **+ Adicionar tentativa** para registrar Tentativa 1, Tentativa 2,
   Tentativa 3... cada uma com seu próprio resultado (correta/incorreta/parcial/não respondida) e
   nível de ajuda. O percentual de acerto e de independência são recalculados automaticamente a cada
   tentativa, usando exatamente as fórmulas da Seção 14.4 do PRD.
6. Volte para **Pacientes** e exclua o paciente cadastrado: ele deve sumir das listas ativas
   imediatamente (soft delete — Seção 16). Um administrador pode restaurá-lo depois via API
   (`POST /v1/patients/{id}/restore`); a tela dedicada de "Dados Excluídos" está prevista para a
   Fase 3 do roadmap.
7. Se for uma conta de clínica, acesse **Profissionais** para gerar um convite e testar o fluxo de
   vinculação de um novo profissional (Seção 7 do PRD).

### Rodando os testes automatizados do backend

```bash
docker compose exec backend pytest -q
```

(ou localmente, sem Docker — ver `backend/README.md`). A suíte cobre, entre outros:

- **AC-01**: conta nova inicia com zero pacientes/sessões/dashboard.
- **AC-02** / **AC-03**: limite de 3 pacientes e bloqueio de foto no plano Free.
- **AC-04** / **AC-05**: tentativas individualizadas (Tentativa 1, 2, 3...) e cálculo de 66,7% de
  acerto reproduzindo o exemplo exato da Seção 11.4/33.1 do PRD.
- **AC-07** / **AC-14**: isolamento de histórico por paciente e por tenant (clínica/individual).
- **AC-09**: profissional convidado entra vinculado à clínica e não acessa a criação de convites.
- **AC-10** / **AC-11** / **AC-12**: exclusão (soft delete), restauração e reflexo imediato no
  dashboard.
- Cálculos de percentual de acerto, independência e distribuição de ajuda (Seção 14.4) como testes
  unitários isolados.

## O que **não** está nesta fase

Seguindo o roadmap (Seção 31.1 do PRD), ficam para as próximas fases: Planos de Tratamento e Reports
com gráficos/IA (Fase 2); RBAC completo, Stripe/planos pagos, tela dedicada de Dados Excluídos e
Agenda (Fase 3); Timeline clínica, heatmaps e alertas inteligentes (Fase 4). Consulte
`backend/README.md` para a observação sobre a curadoria da Training Library.

## Estrutura do repositório

```
backend/    API FastAPI + SQLAlchemy + Alembic + testes (pytest)
frontend/   React + TypeScript + Tailwind
docs/       PRD (fonte única de verdade)
docker-compose.yml
```
