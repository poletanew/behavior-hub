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

## Nota sobre Alertas Clínicos Inteligentes (Fase 4a bloco 1 — Seção 29.1/29.9)

`app/services/clinical_alert_service.py` implementa as quatro regras computáveis da Seção 29.1,
literalmente conforme especificadas (obrigatórias como critério de aceite antes do desenvolvimento —
AC-15/AC-16): `_evaluate_regression` (média móvel de N sessões cai X pontos percentuais — testado
reproduzindo o próprio exemplo do PRD), `_evaluate_stagnation`, `_evaluate_no_collection` e
`_evaluate_fading_candidate`. Os limiares (`no_collection_days`, `regression_drop_pp`, etc.) vivem em
`ClinicPermissionSettings` — mesma tabela do RBAC configurável, já que ambos são "configurações por
clínica" — com valores padrão de fábrica e edição restrita ao plano Enterprise
(`update_thresholds`).

A série histórica por objetivo (`_objective_session_series`) depende de `ObjectiveTraining` (o
vínculo objetivo↔treino já existente desde a Fase 2): sem pelo menos um treino vinculado, um
objetivo nunca gera alertas — não há como derivar tentativas por objetivo sem esse vínculo
estrutural. `ClinicalAlert` usa um índice único parcial (`resolved_at IS NULL`) para garantir que
nunca existam dois alertas ativos do mesmo tipo para o mesmo objetivo — chamadas repetidas de
`recompute_alerts_for_objective` apenas atualizam o `detail` do alerta já ativo, sem duplicar nem
notificar de novo; quando a condição deixa de ser verdadeira, o alerta é marcado como resolvido (não
apagado, preservando histórico).

Regressão/estagnação/fading são recalculados em tempo real a cada tentativa salva
(`session_service.add_trial/update_trial/delete_trial` chamam
`clinical_alert_service.recompute_alerts_for_training` depois de cada commit). O alerta de "sem
coleta" depende só da passagem do tempo — por isso `app/tasks/clinical_alerts.py` roda diariamente
via Celery beat, varrendo todos os pacientes ativos, como rede de segurança complementar (não
substitui o recálculo em tempo real; apenas cobre o caso em que nenhuma tentativa nova é salva).

## Nota sobre Timeline Clínica (Fase 4a bloco 2 — Seção 29.2/AC-18)

`app/services/timeline_service.py` monta a linha do tempo de um paciente agregando de fontes já
existentes em vez de introduzir uma nova tabela de "eventos" dedicada: sessões clínicas diretamente,
`AuditLog` filtrado por `entity_type`/`entity_id` para o ciclo de vida de objetivos
(`objective_created/updated/deleted/restored`) e mudanças de atribuição de profissional, e
`ReportSummary` para relatórios gerados. Essa escolha evita duplicar armazenamento e o risco de os
dois ficarem dessincronizados, já que o `AuditLog` é preenchido por praticamente todo serviço desde a
Fase 1.

`_objective_entries` inspeciona o `before`/`after` de cada evento `objective_updated` do audit log
para distinguir uma atualização genérica de um marco clinicamente relevante: quando
`before.status != "mastered"` e `after.status == "mastered"`, o evento emitido é
`objective_mastered` **no lugar de** (não além de) `objective_updated` — testado explicitamente em
`test_timeline_objective_mastered_is_a_distinct_milestone`, que garante que o evento genérico não
aparece duplicado para essa mesma mudança.

Para satisfazer o AC-18 (ordem cronológica sem duplicatas), a lista final é ordenada por
`(occurred_at, str(id))` — um desempate estável mesmo quando eventos de fontes diferentes caem no
mesmo timestamp. Avaliações formais (Seção 30) e intercorrências/notas livres ainda não têm um
modelo próprio no sistema, então não aparecem na timeline por enquanto; entram quando esses módulos
forem implementados (Fase 4b/5).

## Nota sobre Heatmap de Habilidades (Fase 4a bloco 3 — Seção 29.3/AC-17)

`build_heatmap_data` (em `app/services/report_service.py`) reutiliza o mesmo conceito de "área" já
usado pelo radar (`build_radar_data`): a categoria do treino (`TrainingCategory.name`), não o campo
`area` (enum `TreatmentArea`) do `Objective` — mantendo os dois gráficos de "área" do relatório
consistentes entre si. O PRD (Seção 27.2) propõe uma tabela `SkillHeatmapCache` recalculada de forma
assíncrona via Celery; optamos por calcular ao vivo a cada requisição (mesmo padrão já usado pelos
outros 6 gráficos de Reports) em vez de introduzir cache e uma tarefa assíncrona dedicada — o volume
de tentativas por paciente em 30 dias é pequeno o bastante para isso ser instantâneo, e evita
mais uma fonte de dado potencialmente desatualizada. Se o volume de dados crescer a ponto de a
consulta ficar lenta, a mesma função pode ser adaptada para ler de um cache sem mudar o contrato da
API.

Diferente dos demais gráficos de Reports, a janela do heatmap é sempre "hoje menos 30 dias corridos"
— fixa por definição do AC-17 — e ignora deliberadamente os filtros de `date_from`/`date_to`/
`training_id`/`category_id`/`professional_id` que o usuário aplica ao restante do relatório
(`get_report_data` busca as linhas do heatmap com sua própria chamada a `_fetch_rows`, independente
da consulta filtrada usada pelos outros gráficos).

## Nota sobre Dashboard para Supervisor (Fase 4a bloco 4 — Seção 29.4)

`app/services/supervisor_dashboard_service.py` reaproveita deliberadamente duas peças de
infraestrutura já existentes em vez de introduzir novos conceitos:

- **Percentual de sessões completas por terapeuta** usa exatamente a mesma fórmula de
  `appointment_service.attendance_rate` (completas / (completas + faltas)), só que agrupada por
  `professional_id` em vez de por paciente — mantendo as duas métricas de "taxa de comparecimento"
  consistentes entre si.
- **Adesão ao plano de tratamento** é definida como a fração dos objetivos ativos (não
  iniciado/em andamento, não excluídos) de pacientes atribuídos ao terapeuta que **não** têm um
  alerta de "sem coleta" (`ClinicalAlertType.NO_COLLECTION`) ativo no momento — reaproveitando o
  mecanismo de alertas já construído na Seção 29.1 em vez de duplicar a lógica de "há quanto tempo
  não é registrada uma tentativa". Isso também significa que a adesão só reflete a realidade depois
  que os alertas tiverem sido recalculados (em tempo real a cada tentativa salva, ou pela varredura
  diária) — mesma limitação já documentada para os próprios alertas.
- O alerta de **baixa adesão** dispara quando essa adesão cai abaixo de 70% (`LOW_ADHERENCE_THRESHOLD_PCT`,
  um valor fixo nesta fase — diferente dos limiares de alerta clínico, este não é configurável por
  clínica, já que o PRD não pede isso explicitamente para o dashboard do supervisor).
- O alerta de **ausência de registro** reaproveita o mesmo `no_collection_days` configurável por
  clínica (`ClinicPermissionSettings`) já usado pelos alertas clínicos: dispara quando o terapeuta
  tem pelo menos um paciente atribuído mas nenhum atendimento registrado dentro dessa janela.

O acesso é restrito a `CLINIC_ADMIN` e `SUPERVISOR` de uma clínica (contas individuais não têm uma
"equipe" e recebem 403), mesmo padrão de gate já usado por `rbac_service`/`ClinicPermissionSettings`.

## Nota sobre Dashboard para Gestor (Fase 4a bloco 5 — Seção 29.5, fecha a Fase 4a)

`app/services/manager_dashboard_service.py` é restrito somente a `CLINIC_ADMIN` (nem supervisor, nem
profissional, nem conta individual) — é uma visão de negócio da clínica, distinta do painel de
equipe do bloco anterior. Todos os indicadores são somas/contagens diretas sobre `Patient`,
`User`, `ClinicalSession` e `Appointment` já existentes, filtráveis por período (padrão: do dia 1 do
mês corrente até hoje).

**Horas clínicas** soma apenas a duração (`scheduled_end - scheduled_start`) de `Appointment`s com
status `completed` — porque `ClinicalSession` não tem um campo de duração próprio (só
`occurred_at`, um instante). Uma sessão registrada sem vínculo com um compromisso da Agenda conta
para `sessions_count` mas não contribui `clinical_hours`, porque não há como derivar sua duração sem
inventar um valor. **Taxa de ocupação** é `completas / (completas + faltas + canceladas)` dentro do
período — mesmo raciocínio de "outcome conhecido" já usado por `attendance_rate` e pelo dashboard do
supervisor, apenas agregado por clínica em vez de por paciente/terapeuta.

**Indicadores de receita e taxa de faturamento** (pedidos pela Seção 29.5) foram deliberadamente
**não implementados**: o produto não tem um módulo de cobrança por paciente/sessão — a única
integração de pagamento existente é o Stripe da assinatura SaaS que a clínica paga ao Behavior Hub
(Seção 8), que não é "receita operacional da clínica". Sem um dado real de faturamento por sessão
armazenado em algum lugar, qualquer número aqui seria inventado; a decisão foi omitir esses dois
indicadores e documentar a lacuna explicitamente, em vez de preencher com um placeholder.

## Nota sobre Sugestões Clínicas (Fase 4b bloco 1 — Seção 29.1)

`app/services/clinical_suggestion_service.py` implementa 3 das recomendações da Seção 29.1 com
regras determinísticas — **não** chamadas a um provedor de IA real, já que o fornecedor e a política
de tratamento de dados ainda não foram definidos (Seção 34 do PRD lista isso como pendência do
Product Owner). A "sugestão de fading" reaproveita literalmente
`clinical_alert_service._evaluate_fading_candidate` e `_objective_session_series` (mesma série
histórica e limiares dos Alertas Clínicos da Fase 4a) — decisão deliberada de não duplicar a fórmula
de detecção em dois lugares. A "sugestão de objetivo dominado" é uma regra nova
(`_evaluate_mastery_ready`), mas segue exatamente o mesmo padrão: N sessões consecutivas com
percentual de acerto acima de um limiar configurável por clínica (`mastery_suggestion_session_count`/
`mastery_suggestion_accuracy_pct`, reaproveitando `ClinicPermissionSettings` e o mesmo endpoint
`PATCH /clinic/alert-thresholds` já existente).

A "sugestão de novo programa" (`recompute_new_program_suggestions`) parte do mesmo conceito de "área"
já usado pelo radar e pelo heatmap (`TrainingCategory`, não o enum `TreatmentArea` do `Objective`):
compara as categorias de treino já trabalhadas ativamente pelo paciente contra a Training Library
visível a ele, e sugere um treino de uma categoria ainda descoberta. Só gera sugestão quando o
paciente já tem pelo menos uma categoria "trabalhada" — sem isso não há uma "área de referência" para
identificar uma lacuna, e paciente novo receberia sugestões arbitrárias logo no primeiro objetivo.

Diferente do `ClinicalAlert` (que reabre sempre que a condição volta a ser verdadeira),
`ClinicalSuggestion` é gerada no máximo uma vez por (objetivo, tipo) ou (paciente, treino, tipo) —
garantido por dois índices únicos parciais (`objective_id IS NOT NULL` / `training_id IS NOT NULL`).
Uma vez que o profissional aprova ou descarta, essa decisão é definitiva e a sugestão nunca
reaparece, mesmo que a condição subjacente continue verdadeira depois — decisão de produto
deliberada, coerente com a frase da Seção 29.1 ("o profissional aprova, ajusta ou descarta"): não
insistir depois de uma decisão já tomada. Por simetria com esse mesmo princípio, **aprovar uma
sugestão nunca muda dado clínico algum automaticamente** — `approve_suggestion`/`dismiss_suggestion`
apenas gravam a decisão (com auditoria via `audit_service`); marcar o objetivo como dominado, criar
o novo objetivo ou reduzir o nível de ajuda continuam sendo ações do profissional nos fluxos já
existentes (Plano de Tratamento, registro de sessão), agora só informadas pela sugestão.

A "sugestão de troca de reforçador" da Seção 29.1 não foi implementada: o modelo de dados atual não
tem nenhuma entidade de reforçador ou métrica de engajamento — não há dado real para basear essa
regra, e inventá-lo seria fabricar um número. Fica para quando (e se) um módulo de registro de
reforçadores for adicionado ao produto.

## Nota sobre Avaliações Padronizadas (Fase 4b bloco 2 — Seção 30, AC-19)

`app/services/assessment_protocols.py` é o `ProtocolDefinition` da Seção 30.1.1: um dicionário
Python (não uma tabela) mapeando `domain_code` → `domain_label`/`max_value` por protocolo, permitindo
adicionar protocolos novos sem alterar o schema do banco. Só reproduzimos aqui os **nomes** dos
domínios/áreas de cada protocolo — terminologia padrão da análise do comportamento, já citada
literalmente no próprio PRD (ex.: "mando", "tato") — nunca os itens/tarefas de avaliação em si, que
pertencem ao manual oficial de cada instrumento comercial licenciado (Seção 30.3: "protocolos com
exigência de licenciamento formal ficam marcados como 'requer licença' e não são distribuídos pelo
sistema, apenas referenciados para registro de pontuação").

Os `max_value` do **VB-MAPP** (16 domínios somando exatamente 170 pontos) são valores oficialmente
publicados e amplamente documentados na literatura da área — usados aqui só como sugestão no
formulário, sempre editável, já que a responsabilidade pela aplicação/pontuação é do profissional
habilitado. O **ABLLS-R** não tem `max_value` padrão nenhum: o número de tarefas por domínio varia
por edição/adaptação do instrumento, e preencher um valor sem certeza equivaleria a inventar dado —
o profissional informa o `max_value` real do seu manual ao registrar cada avaliação (validado por
`_build_raw_scores` em `assessment_service.py`, que rejeita quando falta e quando `raw_value` excede
o `max_value`).

`Assessment.raw_scores` é uma lista JSON (não colunas fixas), pelo mesmo motivo do `ProtocolDefinition`
— protocolos diferentes têm domínios e escalas diferentes, e um schema rígido não escalaria. Um par
(paciente, protocolo, data) nunca se repete (`uq_assessments_patient_protocol_date`, Seção 27.3).

`compare_assessments` (Seção 30.2/AC-19) usa `normalized_pct` — não `raw_value` — para calcular ganho
absoluto (diferença em pontos percentuais) e ganho relativo (variação percentual sobre a linha de
base) entre a aplicação mais antiga e a mais recente do conjunto selecionado, restrito aos domínios
em comum entre as duas. Isso é necessário porque `max_value` pode mudar entre aplicações (o
profissional pode corrigir um valor, ou o próprio protocolo permitir isso) — comparar `raw_value`
diretamente produziria números sem sentido se o máximo variar. O texto interpretativo é um rascunho
determinístico (`generated_by` equivalente ao `rule_based_draft` de Reports — mesma nota de escopo
das Sugestões Clínicas acima: nenhuma chamada a um provedor de IA real ainda).

Assessment tem soft delete e está integrado a Dados Excluídos e à Timeline Clínica (evento
`assessment_applied`), fechando a lacuna documentada no bloco anterior da Fase 4a.

## Nota sobre Biblioteca Inteligente (Fase 4b bloco 3 — Seção 29.7, fecha a Fase 4b)

`ResourceLink` (`app/models/resource_link.py`) é exatamente a "dependência bloqueante" que a Seção
29.7 do PRD descrevia: "a tabela de associação ResourceLink (resource_id, training_id ou
objective_id, relevance_score)". Um `ResourceLink` aponta para exatamente um alvo — `training_id` OU
`objective_id`, nunca os dois nem nenhum (`ck_resource_links_single_target`, mesmo padrão do XOR já
usado em `Appointment.clinic_id`/`individual_owner_id`) — e nunca se repete para o mesmo par
recurso+alvo (dois índices únicos parciais). Populado manualmente pelo profissional (tagueamento com
uma pontuação de relevância de 1 a 5), nunca inferido automaticamente: o próprio PRD já antecipava
essa limitação ("não há dado histórico suficiente para a IA inferir a relação sozinha no
lançamento").

`resource_link_service.list_links_for_objective` é a peça central da "recomendação": agrega os
vínculos diretos ao objetivo com os vínculos de qualquer treino que o objetivo usa
(`ObjectiveTraining`), deduplicando por recurso (mantendo a maior pontuação de relevância quando o
mesmo recurso aparece nas duas fontes) — realizando literalmente "ao trabalhar um objetivo
específico, a IA recomenda automaticamente atividades... relacionadas ao mesmo objetivo" (Seção
29.7), exceto que a fonte da recomendação é o vínculo manual, não uma IA. A visibilidade de recursos
privados de outros profissionais é reaplicada aqui (`_resource_visible`, mesma regra de
`resource_service.list_resources`) para que um vínculo não vaze um recurso privado de outra pessoa
na lista agregada.

## Nota sobre Portal da Família (Fase 5 bloco 1 — Seção 29.6/17.2)

**Revogação imediata sem tabela de sessões.** A Seção 17.2 exige que "revogação de acesso do Family
Portal seja imediata... com encerramento de sessões ativas do responsável", mas a autenticação do
Behavior Hub é inteiramente stateless (JWT sem registro de sessão no banco). Em vez de reescrever
toda a arquitetura de auth para um modelo de sessão server-side, adicionamos um único contador
`token_version` em `User` (`app/models/user.py`), embutido como claim `"ver"` em todo token emitido
(`auth_service.issue_tokens`) e conferido a cada request (`core/deps.get_current_user`) e a cada
refresh (`auth_service.refresh_access_token`). `family_access_service.revoke_access` incrementa esse
contador do usuário responsável ao revogar — qualquer token (access ou refresh) emitido antes disso
passa a falhar com 401 na próxima requisição, mesmo que ainda não tenha expirado pela data. Isso
invalida **todas** as sessões ativas daquele responsável (não só o acesso a um paciente específico),
o que é a leitura mais literal de "sessões ativas do responsável" na Seção 17.2.

**Whitelist, nunca blacklist.** `FamilyAccess` (`app/models/family_access.py`) tem cinco booleanos
(`can_view_evolution_charts`, `can_view_upcoming_appointments`, `can_view_team_guidance`,
`can_view_home_materials`, `can_use_messaging`), todos `default=False`. O convite de um responsável
(papel novo `UserType.FAMILY`, reaproveitando o fluxo existente de `Invitation`/`accept_invitation`
em vez de um sistema de convite paralelo) cria o `FamilyAccess` já com tudo desligado; cada categoria
só liga com uma ação explícita do administrador (`family_access_service.update_whitelist`). Isso
satisfaz literalmente a Seção 17.2: "o portal só exibe o que foi explicitamente liberado, e qualquer
campo novo... fica oculto ao responsável até ser revisado e autorizado" — qualquer categoria futura
nasce como um novo booleano `False`, nunca como uma exclusão de uma blacklist.

**Consentimento registrado.** `FamilyAccess.consent_given_at` é gravado no momento em que o convite é
aceito — o mesmo `accept_terms=True` que já serve de registro de aceite de termos para qualquer outro
tipo de conta é reaproveitado como o "consentimento explícito e registrado" da Seção 17.2, em vez de
inventar um fluxo de consentimento paralelo.

**Bloqueio de contas `family` num único ponto.** Em vez de auditar e alterar todas as ~30 rotas
escopadas a paciente para excluir explicitamente `UserType.FAMILY`, endurecemos o gate mais
reaproveitado do sistema: `patient_service.get_patient_or_404`/`list_patients` (usado por
praticamente todo endpoint de paciente — Reports, Plano de Tratamento, Avaliações, Agenda, etc.)
agora rejeita `user_type == FAMILY` com 403 logo no início. Isso cobre a esmagadora maioria da
superfície de API com uma mudança cirúrgica. Exposição residual conhecida e aceita: endpoints que
**não** são escopados a paciente (Training Library, listagem de Recursos, listagem de Profissionais)
não têm essa checagem explícita — uma conta `family` que os chamasse via API direta ainda esbarraria
na ausência de `clinic_id`/atribuições compatíveis na prática (o usuário nem pertence à mesma
listagem tenant-scoped de nada relevante), mas isso não tem teste automatizado dedicado nesta rodada.
Todo acesso real do Portal da Família passa por `family_portal_service.py`, que nunca reaproveita os
gates normais de paciente — cada método confere a `FamilyAccess` (existência + não revogado + a flag
da categoria) antes de devolver qualquer dado.

**Reuso de dados já existentes, sem inventar módulos novos.** "Orientações da equipe" mostra apenas
`ReportSummary` com `status == APPROVED` (Seção 14.5) — nunca um rascunho em edição. "Materiais para
casa" reaproveita a mesma agregação direto+via-treino de `resource_link_service.list_links_for_objective`
(Fase 4b, Biblioteca Inteligente), restrita aos objetivos ativos do plano de tratamento do paciente.
"Evolução" reaproveita as funções puras de `report_service` (`_fetch_rows`, `build_line_series`,
`build_radar_data`, `build_cumulative_data`) diretamente, sem passar por `get_report_data` (que
chama `patient_service.get_patient_or_404` com o usuário logado — inadequado aqui, já que quem
acessa é uma conta `family`). `FamilyMessage` é uma lista simples sem threading (nenhuma menção a
conversas aninhadas na Seção 29.6) — profissionais também podem ler/responder pelo mesmo canal via
`GET/POST /patients/{id}/family-messages`.

**Convite de responsável para tenant individual.** `Invitation.clinic_id` passou a ser opcional
(antes obrigatório): um profissional individual (sem clínica) também tem pacientes e precisa poder
convidar um responsável para eles. `Invitation.patient_id` (novo, opcional, obrigatório apenas
quando `role == FAMILY`) reaproveita o mesmo gate de acesso a paciente do convidante
(`patient_service.get_patient_or_404`) como controle de permissão — só quem já enxerga o paciente
pode convidar um responsável para ele, sem precisar de uma nova regra de RBAC dedicada.

## Nota sobre White-label por Clínica (Fase 5 bloco 2 — Seção 32.9)

Três campos novos e nada mais em `Clinic` (`white_label_logo_url`, `white_label_brand_color`,
`white_label_display_name`), todos nulos por padrão. `white_label_service._is_enterprise_and_active`
é o único ponto de decisão sobre "o white-label vale ou não agora": exige
`subscription_plan == ENTERPRISE` **e** `has_paid_access` (status ativo/trialing) — nunca confiar
apenas no rótulo do plano salvo (Seção 8.3), então uma clínica que atrasar/cancelar o Enterprise
perde a marca personalizada na próxima requisição, mesmo com os três campos ainda preenchidos no
banco (útil se ela reativar depois: não precisa reconfigurar nada).

`white_label_service.get_branding_for_clinic` é a função pública (sem exigir permissão de admin)
reaproveitada por duas superfícies diferentes: `report_export_service.export_pdf` (troca o título e
a cor do cabeçalho da tabela) e `family_portal_service.get_branding` (endpoint
`GET /family-portal/patients/{id}/branding`, acessível a qualquer conta `family` com pelo menos um
`FamilyAccess` ativo para aquele paciente — a marca visual não é uma das cinco categorias de dados
clínicos da whitelist da Seção 17.2, então não exige nenhuma flag específica).

**Decisão de escopo deliberada: o logo não é embutido no PDF.** Embutir a imagem exigiria o backend
baixar uma URL fornecida pelo cliente no momento da exportação — uma superfície clássica de SSRF
(Server-Side Request Forgery) sem um proxy de imagem dedicado para mitigá-la, o que estava fora do
escopo deste bloco. Nome exibido e cor de destaque não têm esse problema (são só texto/cor) e por
isso aparecem normalmente no PDF. Já no Portal da Família, o logo aparece normalmente via `<img>`
no navegador do próprio responsável — quem busca a URL ali é o navegador dele, não o nosso backend,
então não há esse risco. O rodapé "Powered by Behavior Hub" é adicionado incondicionalmente ao PDF,
com ou sem white-label ativo, conforme a Seção 32.9 exige.

## Nota sobre a remoção do Faturamento por Sessão (Fase 6 bloco 2 — Addendum v2.1, RF-08/RF-16)

A Fase 5 bloco 3 havia introduzido `SessionCharge` (cobrança por sessão dentro da clínica). O
Addendum de Melhorias v2.1 pediu a remoção explícita dessa proposta ("reverte a proposta de
Faturamento por Sessão"), então o modelo, o serviço, as rotas, a migration de reversão e a tela de
Faturamento foram removidos por completo — não é um recurso oculto atrás de feature flag como o
RF-13 pediu para Importar Paciente, é uma reversão de fato. A gestão da assinatura Stripe do
próprio Behavior Hub (Seção 8.3) não foi afetada: ela já vivia dentro da tela "Planos" desde a Fase
3, então o pedido do RF-16 de "mover para dentro de Planos" já estava satisfeito sem nenhuma
mudança adicional.

## Nota sobre Lista de Espera (Fase 5 bloco 4 — Seção 32.11, fecha os itens buildáveis da Fase 5)

`WaitlistEntry` (`app/models/waitlist_entry.py`) segue o mesmo padrão de tenant denormalizado já
usado em `Patient`/`Appointment`/`Assessment`. A única particularidade em relação a esses modelos:
`birth_date` é opcional aqui (nullable), já que a Seção 32.11 descreve a lista de espera como um
"cadastro simplificado... antes da admissão formal" — a data de nascimento pode não estar disponível
ainda na triagem, diferente de `Patient.birth_date`, que é obrigatório desde a Fase 1.

`waitlist_service.convert_entry` é a peça central de "conversão em paciente completo sem
redigitação": reaproveita `patient_service.create_patient` diretamente (mesmo `PatientCreateRequest`
que a Fase 1 já usa), passando `name`/`guardian_name`/`notes` da entrada da lista de espera sem pedir
esses campos de novo — só pede o que ainda falta (`birth_date`, se ainda não capturado; `diagnosis`,
opcional, já que não é um campo típico de triagem pré-admissão). Isso significa que `convert_entry`
herda de graça todas as regras de `create_patient` (limite de paciente do plano Free, permissão RBAC
configurável) sem precisar duplicá-las.

Conversão e descarte são ações terminais: `status` só sai de `WAITING` uma vez (para `CONVERTED` ou
`DISCARDED`), verificado explicitamente antes de qualquer edição/nova conversão (conflito 409) — uma
entrada já processada não deveria mudar de estado retroativamente, já que `converted_patient_id`
passaria a apontar para um histórico inconsistente.

**Decisão de escopo deliberada: sem campos de convênio/plano de saúde.** O modelo de dados do
Behavior Hub não tem nenhum conceito de convênio médico ainda (mesma lacuna já documentada para o
Dashboard do Gestor); a Seção 32.11 pede "campos mínimos", então adicionar
esse campo agora seria inventar um requisito não pedido pelo PRD. A permissão de acesso reaproveita
`rbac_service.can_create_patient` (a mesma regra configurável de "Cadastrar paciente" da Seção
17.1) em vez de criar uma permissão nova — decisão consistente com o fato de que a Lista de Espera é,
na prática, o mesmo tipo de decisão de negócio ("quem pode trazer um paciente novo para o sistema"),
só que em duas etapas.

## Fechamento do roadmap (Seção 31 do PRD)

Com a Lista de Espera (bloco 4), a Fase 5 — e o roadmap detalhado da Seção 31 como um todo — chegou
ao fim do que dá para construir sem inventar requisito ou dado clínico que o PRD não especifica. A
Anotação por Voz (bloco 5, Seção 32.12) fechou a última peça, mas é puramente frontend (Web Speech
API do navegador, sem nenhuma mudança de backend) — ver `README.md` na raiz do repositório para os
detalhes de implementação. Três itens do escopo original ficaram deliberadamente de fora, cada um
com um motivo diferente e documentado (ondas seguintes de protocolos de avaliação — exigem validação
de especialista por instrumento antes da liberação, Seção 30.1; Machine Learning preditivo — a
própria Seção 29.10 descreve isso como "visão de futuro" condicionada a volume de dados que só existe
após meses de uso real em produção; internacionalização — a Seção 20 pede só "interface preparada
para tradução", não o lançamento efetivo de outro idioma, e o frontend não tem hoje nenhuma
biblioteca de i18n para justificar uma extração retroativa sem um segundo idioma real para validar).
O detalhamento completo de cada decisão está na seção "O que não está nesta fase" do `README.md` da
raiz.

## Nota sobre o papel Auxiliar Terapêutico e a aba ABA (Fase 6 bloco 6 — Addendum v2.1, RF-11)

Novo valor `AT` em `UserType` (enum Postgres nativo — `autogenerate` do Alembic não detecta um
valor novo em um enum já existente, só tipos inteiramente novos, então a migration usa
`ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'AT'` explicitamente, mesmo padrão já usado para
adicionar `FAMILY` na Fase 5). `User.supervisor_id` vincula o AT ao supervisor/admin que gerou o
convite (preenchido em `auth_service.accept_invitation`), usado só para agrupar ATs na aba ABA —
não é, hoje, uma trava de visibilidade adicional.

Em vez de retrofitar restrições de campo nas rotas clínicas gerais, o AT ganhou um namespace de API
inteiramente dedicado (`app/api/v1/at_portal.py` + `app/services/at_portal_service.py` +
`app/schemas/at_portal.py`), que só expõe DTOs mínimos e seguros (`ATPatientResponse` não tem
diagnóstico) e reaproveita diretamente a lógica clínica já existente e já seguros — criar
atendimento (`session_service.create_session`) e registrar tentativa (rotas genéricas de
`session-trainings/{id}/trials` e `/progress`) — em vez de duplicá-la. A única regra nova é
`at_portal_service.apply_training`, que garante que o AT só aplica um treino já vinculado a esse
paciente especificamente (RF-10 "Vincular"), não qualquer treino do sistema.

`patient_service.assert_full_clinical_access` é um guard explícito, chamado nas rotas citadas na
tabela de personas do addendum como vedadas ao AT — listagem e detalhe de paciente, plano de
tratamento (`treatment_plans.py`) e relatórios (`reports.py`). **Decisão de escopo deliberada**:
outras rotas clínicas (linha do tempo, alertas, sugestões) não têm o mesmo guard; o frontend do AT
não tem nenhuma tela que as chame, mas isso é diferente de uma trava na própria API — mesmo tipo de
tradeoff documentado já para a "exposição residual" do Portal da Família (bloco 1 desta mesma
fase).

Atribuir um AT a um paciente reaproveita o mecanismo de atribuição já existente
(`assign_professional`/`remove_assignment`), agora liberado também para `SUPERVISOR` (antes,
só `CLINIC_ADMIN`). Isso expôs um gotcha: essas rotas usavam `get_patient_or_404`, que restringe
não-admins aos pacientes **já atribuídos a si mesmos** — mas um supervisor atribuindo um paciente
novo a um AT precisa enxergar pacientes ainda não atribuídos a ninguém. Corrigido com
`_get_patient_for_assignment_management`, uma busca escopada só ao tenant (sem a restrição de
atribuição), usada exclusivamente por essas duas rotas administrativas.

`app/api/v1/aba.py` + `app/services/aba_service.py` dão ao supervisor/admin a visão de gestão: listar
ATs com contagem de pacientes atribuídos, listar pacientes de um AT específico, e uma tabela
somente-leitura das tentativas mais recentes registradas por qualquer AT do tenant — explicitamente
uma visão de acompanhamento, não uma camada de aprovação (o addendum descreve aprovação como
opcional, "se a clínica optar", e não foi implementada nesta fase).

## Nota sobre Anexos por Área do Plano de Tratamento (Fase 6 bloco 7 — Addendum v2.1, RF-04)

Nova entidade `TreatmentPlanAttachment` (`app/models/treatment_plan.py`), independente de
`Objective` — o addendum pede "anexar um documento àquela área específica do plano" (ex.: uma
avaliação externa ou plano em papel já existente), não um anexo de um objetivo individual, então
criar uma entidade nova em vez de reaproveitar `Objective`/`ObjectiveTraining` evita forçar um
vínculo artificial com um objetivo que talvez nem exista ainda. O upload reaproveita
`file_service` (mesmo MinIO/S3 já usado pelos Recursos Terapêuticos desde a Fase 2) — só PDF é
aceito (`application/pdf`), mesmo limite de 10MB.

O isolamento por área (critério de aceite do RF-04: "importar um PDF em ABA não o torna visível
nem editável nas demais áreas") vem estruturalmente do modelo — `area` é uma coluna obrigatória do
próprio anexo, não uma tag opcional, e a rota de detalhe (`GET /treatment-plan/attachments/{id}`)
devolve uma URL assinada e temporária (`generate_presigned_url`), o mesmo padrão de "visualizador
seguro" já usado por `resources.py` desde a Fase 2 — não há um endpoint de download direto e
público.

Upload exige `can_edit_area` (a mesma checagem já usada por `create_objective` para editar
objetivos daquela área) — quem pode adicionar um objetivo a uma área também pode anexar um PDF a
ela; não foi criada uma permissão nova separada. Leitura segue o gate normal de
`get_patient_or_404`, e a rota de detalhe do anexo chama `assert_full_clinical_access` (RF-11) —
o AT continua sem acesso a esses documentos, consistente com estar bloqueado do Plano de
Tratamento como um todo.

**Gotcha de migration**: `op.create_table` com uma coluna `sa.Enum(..., create_type=False)`
reutilizando um tipo Postgres já existente (`treatmentarea`, criado desde `Objective.area` na Fase
2) ainda tentava recriar o tipo e falhava com `DuplicateObject` — o `sa.Enum` genérico descarta o
kwarg `create_type` silenciosamente; só `sqlalchemy.dialects.postgresql.ENUM(..., create_type=False)`
de fato suprime a recriação. Ver o comentário na própria migration
(`6120d163231c_fase6_bloco7_treatment_plan_attachments.py`) para o diagnóstico completo.

## Nota sobre IA no Plano de Tratamento — "Preencher com IA" (Fase 6 bloco 8 — Addendum v2.1, RF-05)

`Objective` ganha três campos novos — `ai_generated` (bool), `ai_source_document_id` (FK para
`treatment_plan_attachments`) e `ai_reviewed_at`. O addendum é explícito ao pedir que "a partir do
PDF exportado/importado (RF-04)" a IA sugira os 4 campos — por isso a rota nova
(`POST /patients/{id}/treatment-plan/objectives/ai-fill`) reaproveita diretamente os anexos já
criados no Bloco 7, em vez de abrir um upload paralelo dentro do formulário de Novo Objetivo.

**Sem chamada a nenhuma API de IA externa** — mesmo princípio já usado em
`report_summary_service._draft_text` (Fase 2/14.5): o "Ponto técnico de atenção" do próprio
addendum recomenda começar simples ("a IA lê o texto e tenta mapear para os 4 campos"), então
`treatment_plan_service._draft_objective_fields_from_text` extrai o texto do PDF via `pypdf`
(`file_service.download_object` + `PdfReader`) e mapeia por palavras-chave determinísticas
(`critério`/`domínio`/`%` para o critério de domínio; `estratégia`/`intervenção`/`prompt`/`ajuda`
para as estratégias; a primeira linha vira título; o restante vira descrição). Um PDF sem texto
extraível (documento escaneado sem OCR, por exemplo) não falha silenciosamente — retorna campos
vazios com `extraction_note` explicando o motivo, para o profissional preencher manualmente.

**Nunca publica sozinho**: a rota de "Preencher com IA" não persiste nada — devolve só o rascunho
na resposta. O objetivo só grava `ai_generated=true`/`ai_source_document_id`/`ai_reviewed_at` no
exato momento em que `create_objective` é chamado, ou seja, quando o profissional já revisou (ou
optou por não revisar) e clicou em Salvar — o mesmo princípio de "a IA pode gerar rascunhos, mas não
deve publicar automaticamente conteúdo clínico sem revisão" (Seção 12.1) já seguido por
`report_summary_service` e `resource_service`. `ai_reviewed_at` é preenchido nesse instante, não
antes, já que não existe um estado de rascunho persistido intermediário — diferente do
`ai_generated_plan_draft` que o RF-06 (próximo bloco) vai introduzir para Avaliações.

Upload de PDF (RF-04) e "Preencher com IA" (RF-05) compartilham a mesma checagem de permissão
(`can_edit_area`) — quem pode anexar um documento a uma área também pode gerar um rascunho a partir
dele; não foi criada uma permissão nova. Dependência nova: `pypdf` (`requirements.txt`), leitura de
texto de PDF pura em Python, sem binário externo.

## Nota sobre IA em Avaliações Padronizadas (Fase 6 bloco 9 — Addendum v2.1, RF-06)

`Assessment` ganha `ai_generated_plan_draft` (JSON, lista de itens sugeridos) e
`plan_draft_activated_at`. Decisão importante: o modelo de `Assessment` não tem — e nunca teve — um
estado de rascunho/pendente separado de "concluída"; toda aplicação já é registrada com
`raw_scores` completo. Por isso, "ao marcar a avaliação como concluída" (linguagem do addendum) é
tratado como o próprio instante de `create_assessment` — não foi criado um novo status de avaliação
só para satisfazer essa frase.

`assessment_service._generate_plan_draft` decide quais domínios são "de menor desempenho" com uma
regra puramente aritmética: domínios com `normalized_pct` abaixo da média desta mesma avaliação
(se todos empatarem, todos entram no rascunho, garantindo pelo menos um item). Cada item vira um
objetivo sugerido — título, descrição, critério e estratégias em texto-modelo, sempre editável.

**Decisão de escopo deliberada: todo objetivo sugerido vai para a área ABA.** VB-MAPP e ABLLS-R
(Seção 30) são instrumentos de Análise do Comportamento Aplicada; o PRD não define um mapeamento
domínio→área da grade multidisciplinar (Seção 13.1) para os domínios desses protocolos (ex.:
"Leitura", "Motricidade Fina", "Vestir-se"), e inventar esse mapeamento seria decidir um julgamento
clínico que o documento não especifica. Mapear tudo para ABA — a área nativa desses protocolos —
evita esse problema sem perder a funcionalidade pedida.

`ai_generated_plan_draft` **nunca vira `Objective` sozinho.** A nova rota
`POST /assessments/{id}/activate-plan-draft` recebe os itens (possivelmente editados pelo
profissional) e reaproveita `treatment_plan_service.create_objective` diretamente para cada um —
com `force=True`, já que o conteúdo já foi revisado/editado antes do envio, então o alerta de
duplicidade da Seção 13.2 não se aplica aqui da mesma forma que numa digitação manual avulsa.
`plan_draft_activated_at` impede uma segunda ativação (409) — evita duplicar os mesmos objetivos se
o profissional clicar em "Ativar" duas vezes; a avaliação em si e seu rascunho continuam intactos
para consulta, só a ativação é bloqueada. `Objective.ai_source_assessment_id` (nova FK, paralela ao
`ai_source_document_id` do RF-05) mantém a rastreabilidade de qual avaliação originou o objetivo.

Nenhum gráfico novo foi persistido no backend — "(a) gera os gráficos de domínio" já está satisfeito
estruturalmente pelo `raw_scores` (que já tem `domain_label`/`normalized_pct` por domínio desde a
Fase 4b); o gráfico de barras em si é responsabilidade do frontend (`AssessmentsPage.tsx`,
`recharts`), o mesmo padrão já usado em Reports.

## Nota sobre "Criar recurso com IA" (Fase 6 bloco 10 — Addendum v2.1, RF-12)

`Resource` ganha `ai_generated` (bool) e `ai_reviewed_at`, mesmo par de campos já usado em
`Objective` (RF-05/RF-06). O fluxo tem dois passos deliberadamente separados, espelhando
exatamente a frase do addendum ("gera um rascunho... que o profissional revisa, edita e só então
publica"):

1. `POST /resources/ai-draft` (`resource_service.generate_ai_draft`) — recebe `kind` (história
   social/rotina visual/cartão de comunicação), `theme` e `age_range`, devolve um rascunho
   (título/descrição/conteúdo) que **não é persistido**. O texto vem de um template determinístico
   por tipo de recurso (`_ai_draft_content`) — sem chamada a nenhuma API de IA externa, mesmo
   princípio já seguido por `report_summary_service`/`assessment_service`/`treatment_plan_service`.
2. `POST /resources/ai-publish` (`resource_service.publish_ai_resource`) — só aqui o `Resource` é
   de fato criado, com `ai_generated=True` e `ai_reviewed_at=now()`. O conteúdo (possivelmente
   editado pelo profissional) é renderizado em um PDF de verdade via `reportlab`
   (`_render_ai_resource_pdf` — mesmo padrão de `SimpleDocTemplate`/`Paragraph` já usado em
   `report_export_service.export_pdf`) e enviado ao MinIO/S3 pelo `file_service` já existente —
   reaproveita a mesma listagem, visualizador seguro e regra "individual não compartilha com
   clínica" que já valem para upload manual de recursos.

Diferente de RF-05/RF-06, aqui não há uma entidade de origem externa (PDF anexado, avaliação) para
vincular via FK — o rascunho é gerado a partir de texto livre (tema + faixa etária) fornecido no
próprio formulário, então basta os dois campos booleano/timestamp em `Resource`, sem nenhuma FK
adicional.

## Nota sobre Auditoria Agrupada por Paciente (Fase 6 bloco 11 — Addendum v2.1, RF-14)

O addendum descreve o modelo de dados como "`AuditLog` já suporta `patient_id` como entidade
referenciada; adicionar índice `patient_id` + `timestamp`" — mas o `AuditLog` real (Seção 18) nunca
teve uma coluna `patient_id`; cada linha só referencia `entity_type`/`entity_id` (ex.:
`entity_type="objective"`, `entity_id=<uuid do objetivo>`). Adicionar essa coluna de verdade
exigiria retrofitar os ~60 pontos de chamada de `audit_service.record` espalhados por 18 serviços
— a maioria (auth, billing, RBAC, white-label) nem é sobre um paciente. Em vez disso,
`audit_log_service.get_patient_audit_trail` resolve os IDs relevantes por `entity_type` **em tempo
de consulta**, reaproveitando exatamente a mesma cobertura de entidades já usada por
`timeline_service.get_patient_timeline` (Fase 4a/Seção 29.2): `patient`, `session`, `objective`
(via `plan_id`), `treatment_plan_attachment` (via `plan_id` — os "uploads" citados no critério de
aceite), `patient_assignment` e `assessment`. Diferente da Timeline (que foca em eventos clínicos e
por isso ignora registros já excluídos), a auditoria inclui explicitamente entidades com soft
delete já aplicado — "exclusões" e "restaurações" são, ela própria, o dado que a Seção 17 pede para
mostrar.

Um efeito colateral corrigido en passant: `report_summary_service.generate_summary` gravava
`entity_id=None` no seu registro de auditoria (o resumo criado nunca era referenciado de volta).
Passou a gravar `entity_id=summary.id`, permitindo resolver `ReportSummary.patient_id` como as
demais entidades — pequeno bug de rastreabilidade preexistente, não introduzido por este bloco, mas
que impedia esse tipo de ação de aparecer na nova visão agrupada.

**Decisão de escopo deliberada**: tentativas individuais (`trial_created`/`updated`/`deleted`) não
entram na auditoria por paciente — o critério de aceite do addendum fala em "sessões", não em cada
tentativa isolada, e resolver `Trial` → `SessionTraining` → `ClinicalSession` → paciente
adicionaria uma junção a mais sem um pedido explícito correspondente.

## Nota sobre Segurança — Autoatendimento (Fase 6 bloco 12 — Addendum v2.1, RF-15)

Duas rotas novas em `app/api/v1/auth.py`, ambas exigindo `get_current_user` (o próprio usuário só
altera os próprios dados, nunca os de terceiros):

- `POST /auth/change-password` (`ChangePasswordRequest{current_password, new_password}`) — valida a
  senha atual com `verify_password`, grava o novo hash e **incrementa `user.token_version`**. Esse
  campo já existia (Seção 17.2, usado para revogar acesso do Family Portal) e embute um claim `ver`
  em todo JWT emitido; o middleware de autenticação (`app/core/deps.py::get_current_user`) já
  rejeita qualquer token cujo `ver` não bata mais com o valor salvo no banco. Isso satisfaz
  literalmente "trocar a senha deve encerrar as demais sessões ativas do usuário" sem precisar de
  nenhuma tabela de sessões nova. Como o bump de `token_version` também invalidaria o próprio
  access token que fez a requisição, a rota devolve um par de tokens novo (`TokenResponse`) já
  válido — o frontend troca os tokens salvos (`setTokens`) e a sessão que trocou a senha continua
  ativa, exatamente como o texto pede ("as **demais** sessões", não a atual).
- `PATCH /auth/change-name` (`ChangeNameRequest{name}`) — atualiza `User.name`. **Decisão de
  escopo**: o addendum fala em "nome de usuário", mas o cadastro (Seção 6.2) nunca teve um campo de
  username separado — o login é sempre por email. Interpretamos "nome de usuário" como o nome de
  exibição já existente (`User.name`, mostrado em toda a UI e nos registros de auditoria), em vez de
  inventar um novo campo de identificador de login que o restante do sistema não usa em lugar
  nenhum.

Ambas as ações geram entradas em `AuditLog` (`password_changed`, `user_name_updated`), visíveis na
Auditoria por ação (`entity_type=user`) e na Auditoria por paciente onde aplicável.

## Nota sobre Design System — Leveza Visual Transversal (Fase 6 bloco 13 — Addendum v2.1, RF-17)

Este bloco é 100% frontend — nenhum endpoint, schema ou tabela novos. O addendum pede algo
propositalmente amplo ("aplicar em cada tela principal do sistema"), então em vez de retocar
manualmente todas as ~25 telas uma a uma, priorizamos duas mudanças centrais e de baixo risco que
cobrem o requisito de forma sistemática:

1. **Transição de tela automática para o sistema inteiro**: `Layout.tsx`, `ATWorkspaceLayout.tsx` e
   `FamilyPortalLayout.tsx` (os três roteadores de topo — clínica, AT e Família) agora envolvem o
   `<Outlet />` num `<div key={location.pathname} className="animate-fade-in">`. Trocar de rota
   remonta esse wrapper (a `key` muda), disparando um fade-in curto (`index.css`) em **toda** tela
   do sistema sem precisar tocar em cada página individualmente — satisfaz literalmente "transição
   suave ao trocar de aba" do critério de aceite para qualquer tela, presente ou futura.
2. **Componente `EmptyState` reutilizável** (`frontend/src/components/EmptyState.tsx`): ícone
   amigável num círculo com a cor de apoio turquesa, título opcional e mensagem, substituindo o
   antigo bloco `<div className="p-10 text-center text-neutralState">texto cinza</div>` repetido
   (encontrado idêntico em 13 arquivos). Aplicado às telas principais que podem ficar vazias:
   Pacientes, Atendimentos, Recursos, Lista de Espera, Dados Excluídos, Relatórios, Avaliações,
   Timeline, Auditoria, Painel de Supervisão, Espaço do AT (lista de pacientes e treinos
   prescritos) e o card de "Sessões recentes" da Área de Trabalho.

**Decisão de escopo deliberada**: estados vazios *aninhados* dentro de painéis já preenchidos (ex.:
"Nenhum comentário ainda" dentro do card de um objetivo, "Nenhum convite gerado ainda" numa célula
de tabela) foram deixados como texto simples — o critério de aceite fala em "o primeiro contato de
uma clínica nova com o sistema", isto é, a tela cheia vazia, não cada sub-lista aninhada dentro de
uma tela já com conteúdo; usar o `EmptyState` (ícone grande em círculo) nesses contextos pequenos
ficaria desproporcional ao espaço disponível. Uma confirmação animada ao salvar
(`animate-pop-in`) foi adicionada às mensagens de sucesso da aba Segurança (bloco 12, testado nesta
mesma sessão) como exemplo do padrão "microanimação curta"; não foi replicada em todos os ~60
pontos de mensagem de sucesso do sistema pelo mesmo motivo de escopo. Ambas as animações respeitam
`prefers-reduced-motion: reduce` (acessibilidade, também citada no critério de aceite do RF-17).

Cantos arredondados (`rounded-card`, 12px) e espaçamento generoso nos cards já eram usados de forma
consistente desde fases anteriores (Seção 24.8 do PRD já estava implementada) — não foram alterados
para não introduzir uma mudança de densidade em massa sem necessidade.

## Nota sobre Coleta de Dados — Modelo ABC, Reforçadores e Foto/Vídeo (Fase 7 Módulo 3.1 — Addendum v3.0, RF-18 a RF-20)

Primeiro bloco do Addendum v3.0 (RF-18 a RF-38, numeração contínua a partir do v2.1). Três entidades
novas, todas escopadas por paciente (`clinic_id`/`individual_owner_id` denormalizados, mesmo padrão
de `Assessment`):

- **`BehaviorEvent`** (RF-18) — modelo ABC (Antecedente/Comportamento/Consequência) completo, com
  `frequency_count`, `duration_seconds` e `intensity` (enum `baixa/media/alta`), sempre ligado a uma
  `session_id` mas registrável independentemente das tentativas de treino
  (`POST /patients/{id}/behavior-events`). Entra na Timeline Clínica
  (`timeline_service._behavior_event_entries`, Seção 29.2) e na Auditoria por Paciente
  (`audit_log_service._PATIENT_ENTITY_TYPES`, RF-14/Fase 6 bloco 11) pelo mesmo mecanismo já usado
  para as demais entidades clínicas — nenhuma tabela ou view nova precisou ser criada para isso.
- **`Reinforcer`** / **`SessionReinforcer`** (RF-19) — cadastro de reforçador por paciente
  (`POST /patients/{id}/reinforcers`) e vínculo a uma sessão específica com nota rápida de
  efetividade (`POST /sessions/{id}/reinforcers`). `GET /patients/{id}/reinforcers` já devolve
  `usage_count` agregado por reforçador (contagem de `SessionReinforcer`), satisfazendo o critério
  de aceite "ver quais reforçadores foram mais usados no período" nesta própria rota — o gráfico
  dedicado (RF-34, Módulo 3.7) reaproveitará os mesmos dados.
- **`ClinicalSession.media_key`/`media_type`/`media_duration_seconds`** (RF-20) — o campo `photo_url`
  original (Fase 1) era só uma string de URL sem upload real de fato; permanece intocado por
  compatibilidade, mas o addendum pede upload de verdade com limite de duração/tamanho por plano, o
  que exigia a mesma infraestrutura já usada por Resources/TreatmentPlanAttachment
  (`file_service.upload_object`/`generate_presigned_url`). Novo par de rotas
  `POST /sessions/{id}/media` (multipart, aceita foto ou vídeo, detecta o tipo pelo `content_type`) e
  `GET /sessions/{id}/media-url` (URL assinada, mesmo padrão de privacidade da Seção 17.2). Limites
  por plano (`basic`/`premium`/`enterprise`): duração de vídeo 30s/60s/120s, tamanho de arquivo
  20MB/50MB/100MB — Free continua bloqueado por completo, igual já valia para `photo_url`.

**Decisões de escopo**: (1) tanto `BehaviorEvent` quanto o vínculo de `Reinforcer` a uma sessão usam
a mesma permissão "Registrar sessão" (`rbac_service.can_register_session`, Seção 17.1) já usada por
Trial — nenhum RBAC novo. (2) Foto/vídeo ficou no nível de sessão (não por tentativa individual),
espelhando onde `photo_url` já vivia; o texto do RF-20 fala em "tentativa/sessão" de forma ambígua,
e criar um campo de mídia por `Trial` exigiria uma tabela nova sem um critério de aceite que
realmente precisasse desse nível de granularidade. (3) Nem `BehaviorEvent` nem `Reinforcer` têm
rotas de edição/exclusão — os critérios de aceite do RF-18/RF-19 só pedem registrar, vincular e
visualizar; adicionar CRUD completo sem um requisito correspondente seria escopo não pedido.

**Gotcha de migration (mesma classe do Fase 6 bloco 7, documentada por completude)**: `op.add_column`
numa tabela já existente (`sessions`) não cria automaticamente o tipo Postgres de um enum novo — só
`create_table` faz isso implicitamente. A migration cria `sessionmediatype` explicitamente via
`postgresql.ENUM(...).create(bind, checkfirst=True)` antes do `add_column` (com `create_type=False`
no próprio `add_column`). Efeito colateral menos óbvio: `op.drop_table` também **não** derruba
automaticamente o enum que uma `create_table` anterior criou implicitamente (aqui,
`behaviorintensity`) — o `downgrade()` precisa dropar esse tipo explicitamente também, ou uma
tentativa futura de `upgrade` após um `downgrade` falha com "type already exists".

## Nota sobre Avaliação — Anamnese, Checklists Personalizados e Duplicar Avaliação (Fase 7 Módulo 3.2 — Addendum v3.0, RF-21 a RF-23)

- **`Anamnesis`** (RF-21) — um por paciente (`UniqueConstraint("patient_id")`), campos fixos em vez de
  JSON livre: diferente de `Assessment.raw_scores` (cujos domínios variam por protocolo), as seções
  da anamnese são sempre as mesmas (queixa principal, informações de nascimento, histórico/marcos de
  desenvolvimento, histórico familiar), então um schema fixo é mais simples de validar e exibir do
  que o `form_data (JSON)` sugerido pela tabela de impacto no modelo de dados do addendum.
  `PUT /patients/{id}/anamnesis` cria na primeira chamada e edita nas seguintes (é um formulário de
  admissão vivo, preenchido aos poucos — não um evento imutável); só a criação gera a entrada
  "evento fundacional" na Timeline Clínica (`timeline_service._anamnesis_entries`), edições
  posteriores não duplicam a entrada. Gate: `patient_service.assert_full_clinical_access` (mesmo
  usado por prontuário completo/plano de tratamento/reports) — bloqueia o AT, conforme o texto do
  RF-21 ("acessível a quem tem permissão de leitura de dados clínicos completos").
- **`CustomChecklistTemplate` / `ChecklistResponse`** (RF-22) — o profissional monta um template uma
  vez (`POST /checklist-templates`, título + lista de perguntas com `answer_type` sim/não, escala
  1-5 ou texto curto — cada pergunta recebe um `id` gerado no momento da criação) e reaplica em
  quantos pacientes quiser (`POST /patients/{id}/checklist-responses`). O serviço valida que toda
  pergunta do template foi respondida e que o tipo do valor bate com `answer_type` (bool para
  sim/não, 1-5 para escala, string não vazia para texto curto). `GET /patients/{id}/checklist-responses`
  já devolve os itens "achatados" (pergunta + resposta juntas, não dois arrays para cruzar no
  frontend), o que o critério de aceite chama de "resultado tabulado"; o frontend soma um gráfico de
  barras simples só para as perguntas do tipo escala (as de sim/não e texto curto não têm eixo
  numérico para plotar, então ficam só na tabela).
- **RF-23 (duplicar avaliação anterior)** — implementado inteiramente no frontend, sem rota nova:
  `AssessmentsPage.tsx` já carrega todas as aplicações do protocolo selecionado; um botão "Duplicar
  avaliação anterior como ponto de partida" (visível só quando já existe pelo menos uma aplicação
  anterior do mesmo protocolo para o paciente) pré-preenche o estado local do formulário com os
  `raw_scores` da aplicação mais recente. Como o formulário de criação já exige uma nova
  `applied_date` antes de habilitar o envio, e o POST de `/patients/{id}/assessments` sempre cria um
  registro novo (nunca atualiza um existente — `Assessment` não tem endpoint de update de scores),
  "sem sobrescrever a original" é garantido pela própria arquitetura já existente, sem precisar de
  um endpoint de duplicação dedicado no backend.

## Nota sobre Plano Terapêutico — Manutenção/Generalização e Pais Aplicadores (Fase 7 Módulo 3.3 — Addendum v3.0, RF-24 e RF-25)

- **Manutenção/generalização (RF-24)** — estende `Objective` (Seção 18) direto, como o addendum pede
  explicitamente ("sem criar uma tabela paralela"), com dois campos novos: `maintenance_check_date`
  (`Date`) e `generalization_contexts` (`JSON`, lista de `{context, tested_at, result, notes}`).
  `update_objective` ganhou um gatilho: na primeira vez que o `status` vira `MASTERED`, agenda
  `maintenance_check_date = hoje + MAINTENANCE_INTERVAL_DAYS` (constante fixa de 30 dias — o
  addendum fala do intervalo como exemplo, "ex.: a cada 30 dias", não como uma configuração por
  clínica, então não criamos uma nova tela de configurações para isso). `ObjectiveResponse.maintenance_due`
  é calculado na resposta (`maintenance_check_date <= hoje`), não persistido — evita um Celery sweep
  novo só para marcar uma flag. `POST /objectives/{id}/generalization-contexts` só acrescenta ao
  array (nunca substitui) e `POST /objectives/{id}/maintenance-checks` (400 se o objetivo não estiver
  `MASTERED`) reagenda mais 30 dias e loga o resultado (`mantida`/`perdida`) no Audit Log existente.
- **`ObjectiveApplier`** (RF-25) — tabela nova (`objective_id`, `applier_type` `professional`/`parent`,
  `applier_user_id`, `added_by_user_id`, `UniqueConstraint(objective_id, applier_user_id)`), porque
  aqui sim é uma relação N:N (vários aplicadores por objetivo, uma pessoa pode aplicar vários
  objetivos) que não cabe como campo do `Objective`. `add_applier` (gate: `can_edit_area`, mesmo das
  demais edições de objetivo) só aceita `applier_type=parent` se o usuário alvo já tiver um
  `FamilyAccess` ativo (`revoked_at is None`) para o paciente — reaproveita o mesmo consentimento
  explícito do Portal da Família (Seção 29.6) em vez de abrir uma segunda porta de entrada para dados
  do paciente; retorna 400 se não tiver, 409 se a pessoa já for aplicadora do objetivo.
- **Portal da Família — "apliquei hoje" (RF-25)** — `family_portal_service.list_applier_objectives`
  (gate: `_get_active_access`, o mesmo baseline de todo o Portal da Família) junta `ObjectiveApplier`
  → `Objective` → `TreatmentPlan` filtrando por `applier_user_id`, e `record_objective_application`
  audita a ação como `objective_applied` com `actor_user_id` do responsável. Como
  `treatment_plan_service.get_history` já lê o Audit Log filtrando por `entity_type="objective"`, o
  "apliquei hoje" da família aparece automaticamente no histórico do objetivo do lado da equipe
  clínica — zero tabela nova, zero endpoint novo para o profissional consultar isso. No frontend, a
  aba "Meus Programas" do Portal da Família aparece para qualquer responsável com acesso ativo,
  independente da whitelist de categorias (Seção 17.2) — ser marcado como aplicador de um objetivo
  específico já é, em si, a autorização para aquele objetivo puntual.

## Nota sobre Agendamento — Salas e Arrastar-e-soltar (Fase 7 Módulo 3.4 — Addendum v3.0, RF-26 e RF-28)

- **`Room`** (RF-26) — segue o mesmo padrão de tenant dos demais modelos (`clinic_id` OU
  `individual_owner_id`, nunca os dois), consistente com `Appointment` e todos os modelos
  adicionados desde a Fase 4. `Appointment.room_id` é opcional (nem todo atendimento usa uma sala
  física — ex.: telessaúde). `_has_room_conflict` em `appointment_service.py` é uma cópia direta do
  padrão já usado para `_has_conflict` (profissional): mesma janela de tempo, mesmos status ativos
  (`SCHEDULED`/`CONFIRMED`/`COMPLETED`), aplicado tanto em `create_appointment` quanto em
  `update_appointment`. `room_service.delete_room` recusa (409) remover uma sala com atendimentos
  futuros ativos, em vez de silenciosamente deixá-los sem sala. A UI de gestão de salas fica em
  Configurações da Clínica, restrita a quem já vê essa página (admin/supervisor) — contas
  individuais podem criar salas pela API (mesma consistência de tenant), mas RF-26 fala
  explicitamente de "salas" no plural, um cenário de clínica multi-sala, não de profissional
  autônomo, então não foi criada uma tela dedicada para elas.
- **Arrastar e soltar na Agenda (RF-28)** — implementado como reagendamento por dia: arrastar o
  card de um atendimento para outra coluna de dia da semana mantém o mesmo horário e duração,
  mudando só a data (`PATCH /appointments/{id}` com os novos `scheduled_start`/`scheduled_end`,
  reaproveitando toda a validação de conflito que já existia para edição manual). Não foi
  implementado arrastar para mudar o horário dentro do mesmo dia, já que a grade da Agenda é uma
  visão por coluna-de-dia (Seção 32.2), sem uma grade horária granular para soltar em cima.
- **`Objective.display_order` e reordenar por área (RF-28)** — campo inteiro novo em `Objective`,
  populado com a posição na criação (append ao fim da área) e usado como critério de ordenação
  primário (`area, display_order, created_at`) em `get_treatment_plan`. `POST
  /patients/{id}/treatment-plan/objectives/reorder` recebe a lista completa de IDs da área na nova
  ordem e reescreve `display_order` de todos eles; recusa (400) se a lista não bater exatamente com
  os objetivos ativos da área, para não silenciosamente perder algum objetivo de uma reordenação
  parcial. O frontend expõe uma pequena alça de arrastar (⠿⠿⠿) acima de cada card em vez de tornar o
  card inteiro arrastável, para não conflitar com a seleção de texto nos campos de comentário e
  formulários internos do próprio card.
- **RF-27 (confirmação via WhatsApp) — não implementado nesta fase**, por decisão já confirmada
  anteriormente com o usuário: depende de um provedor de API do WhatsApp Business (BSP) contratado,
  e nenhuma credencial desse tipo está disponível neste projeto. Nenhum schema, campo ou tela foi
  criado para isso — a retomada fica condicionada a uma decisão/credencial futura do usuário.

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
