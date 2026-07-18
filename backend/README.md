# Behavior Hub — Backend (Fase 1 + Fase 2 + Fase 3)

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

## Nota sobre RBAC configurável, Auditoria e Importação de Pacientes (Fase 3 núcleo — Seção 17.1/32.7)

`app/services/rbac_service.py` centraliza as checagens de permissão "Configurável" da tabela da
Seção 17.1: cada clínica tem um `ClinicPermissionSettings` (criado sob demanda, com valores padrão
conservadores — desabilitado, exceto nas células em que a própria tabela do PRD já é permissiva por
padrão) e cada serviço (`patient_service`, `session_service`, `treatment_plan_service`,
`deleted_data_service`, `resource_service`, `auth_service`) consulta essa função em vez de checar
`user_type` diretamente. Convites agora carregam um `role` (`professional` ou `supervisor`),
validado contra `INVITABLE_ROLES` e contra a permissão de quem está convidando.

`app/services/audit_log_service.py` expõe o log já registrado pelo `AuditLog`/`audit_service`
existente desde a Fase 1, escopado por tenant via o `clinic_id` do autor da ação — restrito a
administradores de clínica e contas individuais (Seção 17/21). Limitação conhecida: ações de sistema
sem ator (ex.: a purga automática da Seção 16.2) não aparecem nesta consulta, pois não há um usuário
do qual derivar o tenant.

`app/services/csv_import_service.py` faz a importação em lote de pacientes (Seção 32.7) com detecção
automática de colunas por alias comum em português/inglês (`nome`, `data de nascimento`,
`responsável`, `diagnóstico`, etc.) em vez de uma UI de remapeamento manual coluna-a-coluna — uma
simplificação de escopo deliberada, já que os aliases cobrem o próprio exemplo de cabeçalho do PRD.
Linhas com nome ou data de nascimento ausente/inválida são rejeitadas individualmente (o restante do
arquivo é importado normalmente) e reportadas com o motivo da rejeição.

## Nota sobre Agenda e Scheduling (Fase 3 — Seção 32.2/32.3)

`app/models/appointment.py` introduz `Appointment`, deliberadamente separado de `ClinicalSession`
(Seção 32.2 — "diferencia sessão agendada de sessão registrada"). `app/services/appointment_service.py`
concentra: bloqueio de conflito de horário por profissional (`_has_conflict`, ignorando compromissos
cancelados/não-comparecidos, que liberam o horário), transições de status válidas, alerta de faltas
consecutivas (limiar de 2 — escolha de engenharia, o PRD não especifica um número) restrito a
administradores/supervisores do mesmo tenant, cálculo de taxa de comparecimento por paciente e
geração manual de `.ics` (RFC 5545 mínimo, sem biblioteca externa).

O vínculo entre "marcar como realizada" e o Novo Atendimento é feito via `SessionCreateRequest.appointment_id`
opcional: `session_service.create_session` chama `appointment_service.link_session_to_appointment`
quando presente, o que marca o compromisso como `completed` e grava `session_id` na mesma transação —
não existe um endpoint separado para marcar "realizada" manualmente, seguindo a redação literal do
PRD ("ao marcar... abrir diretamente a tela de Novo Atendimento").

Compromissos seguem soft delete (Seção 16) e entram na purga diária e no ciclo de exclusão/restauração
do paciente (`patient_service.soft_delete_patient`/`restore_patient` agora cascateiam para
`Appointment` do mesmo jeito que já faziam para `ClinicalSession`/`Trial`); `app/tasks/purge.py` remove
`Appointment` antes de `ClinicalSession` no purge de paciente para não violar a FK `appointments.session_id`.

Lembretes automáticos (`app/tasks/reminders.py`, Celery beat a cada hora) cobrem apenas a notificação
in-app ao profissional para compromissos nas próximas 24h — envio por e-mail ao profissional e aviso
ao responsável (Seção 32.2: "quando aplicável") dependem de um provedor de e-mail e de uma conta de
responsável/Family Portal que ainda não existem no produto; mesma lacuna já documentada para convites.

## Nota sobre Autenticação de Dois Fatores (Fase 3 — Seção 32.8)

`app/services/two_factor_service.py` usa `pyotp` (TOTP/RFC 6238). `POST /auth/2fa/setup` gera e já
persiste um `totp_secret` no usuário (ainda com `is_2fa_enabled=False`); só `POST /auth/2fa/enable`
com um código válido efetivamente liga o 2FA — isso evita marcar a conta como protegida antes de o
usuário provar posse do segredo. `POST /auth/2fa/disable` exige a senha atual como confirmação.

O login em duas etapas usa um terceiro `TokenType.TWO_FACTOR` (`app/core/security.py`), de vida curta
(5 minutos): `POST /auth/login` retorna esse token em vez de access/refresh quando
`user.is_2fa_enabled` é verdadeiro; `POST /auth/2fa/verify-login` troca o token + código TOTP pelos
tokens reais. `LoginResponse` (schema único para as duas formas de resposta) mantém o cliente HTTP
simples sem precisar de dois endpoints de login diferentes.

`two_factor_service.requires_2fa_setup` implementa a regra "obrigatória para administradores de
clínica no plano Enterprise, opcional para os demais" — hoje testável diretamente (setando
`clinic.subscription_plan` em teste), mas só reflete um cenário real de produção quando a integração
Stripe (próxima etapa da Fase 3) permitir que uma clínica esteja de fato no plano Enterprise. O
fallback por e-mail citado na Seção 32.8 não foi implementado (mesma lacuna do provedor de e-mail já
documentada para convites e lembretes de agenda); a tela de configuração mostra a chave em texto para
entrada manual no aplicativo autenticador, sem gerar uma imagem de QR code.

## Nota sobre Planos, Assinaturas e Stripe (Fase 3 — Seção 8)

`app/services/billing_service.py` usa o SDK oficial `stripe`. `Clinic` e `User` ganharam
`StripeBillingMixin` (`app/db/base.py`) com `stripe_customer_id`, `stripe_subscription_id` e
`subscription_current_period_end`; `subscription_status` (`SubscriptionStatus`, espelhando os status
do Stripe) é declarado em cada modelo individualmente — não no mixin — porque `app.db.base` é
importado por `app.models.appointment` antes de `app.models.__init__` terminar de rodar, e importar
`app.models.enums` a partir de `app.db.base` reintroduziria o pacote `app.models` no meio da própria
inicialização (import circular). `has_paid_access` (em cada modelo) é a fonte única de verdade de
"a assinatura paga está de fato valendo agora" — `plan_service.current_plan` sempre cai para `"free"`
quando `has_paid_access` é falso, mesmo que `subscription_plan` ainda esteja com o rótulo antigo
(ex.: José antes do próximo webhook confirmar um cancelamento). Isso implementa literalmente a
Seção 8.3: "nunca confiar apenas no frontend para liberar funcionalidades".

Sem `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET`/Price IDs configurados (o padrão neste ambiente, já
que essas chaves não existem ainda), `/stripe/checkout`, `/stripe/portal` e `/webhooks/stripe`
retornam `503` com uma mensagem clara em vez de tentar chamar a API do Stripe com uma chave inválida
ou travar. `StripeWebhookEvent` (tabela `stripe_webhook_events`, `stripe_event_id` único) implementa
a deduplicação de eventos da Seção 28.4: toda reentrega do mesmo evento é ignorada antes de qualquer
processamento.

**Decisão de escopo**: o PRD (Seção 28.4) pede que todo webhook seja "processado de forma assíncrona
via fila, com reprocessamento automático em caso de falha temporária". Implementei a validação de
assinatura e a deduplicação de forma síncrona (como pede a seção — são operações locais, sem chamada
de rede) mas o processamento do evento em si (`billing_service.process_stripe_event`) roda dentro da
própria requisição, na mesma sessão de banco do FastAPI `Depends(get_db)`, em vez de ser despachado
para uma task Celery separada. Motivo: uma task Celery usaria `SessionLocal()` — uma conexão nova,
fora da transação por teste que `tests/conftest.py` usa (savepoint por teste) — o que tornaria
impossível testar de ponta a ponta que o webhook realmente atualizou `Clinic`/`User` sem reestruturar
o harness de testes. Como o próprio Stripe já reentrega automaticamente webhooks que não respondem
`2xx`, e a deduplicação garante que uma reentrega nunca reaplica o efeito duas vezes, o processamento
síncrono já oferece uma resiliência razoável para uma implantação de instância única — revisitar isso
com uma fila verdadeiramente assíncrona é um item razoável para quando o produto precisar de
desacoplamento real (múltiplas instâncias, picos de carga de webhook, etc.).

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
