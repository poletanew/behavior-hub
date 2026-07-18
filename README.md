# Behavior Hub

SaaS de gestão clínica multidisciplinar. Ver `docs/Behavior_Hub_PRD_v2_Completo.pdf` para o PRD
completo (fonte única de verdade do produto).

Este repositório está sendo construído **por fases**, seguindo o roadmap da Seção 31 do PRD.

- **Fase 1 — Core (MVP)**: autenticação, contas (clínica e individual), pacientes, atribuições,
  sessões/atendimentos com tentativas individualizadas e uma Training Library básica.
- **Fase 2 — Clínico (V1)**: Planos de Tratamento multidisciplinares, Reports com gráficos e resumo
  editável, Recursos Terapêuticos, Dados Excluídos (visão unificada com restauração), Central de
  Notificações, Templates de Sessão/duplicar atendimento e Modo Offline de coleta (Seção 32.4/32.5/32.6
  — fechando o restante do escopo da Fase 2).
- **Fase 3 (núcleo) — RBAC configurável, Auditoria e Importação de Pacientes**: permissões
  configuráveis por clínica para profissionais/supervisores (Seção 17.1), papel de Supervisor nos
  convites, log de auditoria (visão de administrador, escopada por tenant) e importação em lote de
  pacientes via CSV.
- **Fase 3 — Agenda e Scheduling (Seção 32.2/32.3)**: agendamento de atendimentos futuros (diferente
  de registrar um atendimento já realizado), status agendada/confirmada/realizada/cancelada/não
  compareceu, bloqueio de conflito de horário por profissional, exportação de agenda em .ics,
  faltas/cancelamentos com motivo, alerta por faltas consecutivas e taxa de comparecimento por
  paciente. 2FA e Stripe/planos pagos ficam para as próximas etapas da Fase 3.

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

## Testando localmente

### Fase 1 — Core

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
6. Se for uma conta de clínica, acesse **Profissionais** para gerar um convite e testar o fluxo de
   vinculação de um novo profissional (Seção 7 do PRD).

### Fase 2 — Planos de Tratamento, Reports, Recursos e Dados Excluídos

7. Na página do paciente, abra **Plano de Tratamento** e clique em **+ Novo objetivo**. Cadastre um
   objetivo (ex.: área ABA, "Aguardar por 30 segundos com comportamento seguro"). Tente cadastrar um
   objetivo com título parecido no mesmo paciente: o sistema deve alertar sobre a duplicidade (com
   área e autor do objetivo existente — Seção 13.2/AC-08) antes de permitir "Adicionar mesmo assim".
8. Abra **Reports** no mesmo paciente (com pelo menos um atendimento já registrado): os 6 gráficos
   obrigatórios (linha, barras, barras empilhadas, pizza/rosca, radar, cumulativo — Seção 14.3) devem
   refletir as tentativas reais. Clique em **Gerar resumo do período**: o texto é um rascunho
   determinístico (rotulado "Rascunho automático por regras — revise antes de exportar"), editável,
   aprovável e versionado — **não é gerado por uma API de IA externa nesta fase** (ver observação
   abaixo). Teste **Exportar CSV** e **Exportar PDF**.
9. Em **Recursos**, envie um PDF ou imagem, abra o recurso (visualizador dentro do sistema) e depois
   exclua-o.
10. Como administrador, acesse **Dados Excluídos**: o recurso excluído (e qualquer paciente ou
    objetivo de plano excluído) aparece na lista unificada com contagem regressiva de 60 dias; use
    **Restaurar** para repor o registro.

### Fase 2 (fechamento) — Notificações, Templates de Sessão e Modo Offline

11. No **Plano de Tratamento**, expanda um objetivo e escreva um comentário mencionando (@) outro
    profissional da clínica: ele recebe uma notificação (sino no canto superior direito) que leva
    diretamente ao objetivo de origem (Seção 32.6/32.13).
12. Em um **Atendimento**, clique em **Salvar como modelo** para guardar o conjunto de treinos como
    um "modelo de atendimento" reutilizável, ou em **Duplicar sessão** para criar uma nova sessão com
    os mesmos treinos da anterior em outra data (Seção 32.4). Ao abrir **Novo Atendimento** para o
    mesmo paciente depois, o modelo salvo aparece no seletor "Usar modelo de atendimento".
13. Para testar o **Modo Offline** (Seção 32.5): abra um atendimento, desligue a rede (ou use as
    ferramentas de desenvolvedor do navegador para simular "offline") e registre uma tentativa — ela
    fica marcada como "aguardando sincronização" localmente. Ao reconectar, a tentativa é enviada
    automaticamente e passa a aparecer como uma tentativa normal (numerada), sem precisar recarregar
    manualmente nem duplicar o registro.

### Fase 3 (núcleo) — RBAC configurável, Auditoria e Importação de Pacientes

14. Como administrador, acesse **Configurações**: ative/desative os toggles de permissão (Seção
    17.1 — ex.: "Profissionais podem cadastrar pacientes", "Supervisores podem editar objetivos de
    qualquer área"). Os padrões começam conservadores (desabilitados), exceto onde a própria tabela
    do PRD já é permissiva. Convide um profissional em **Profissionais** e confirme que, sem o toggle
    ligado, ele recebe erro ao tentar cadastrar um paciente — e que passa a conseguir depois de você
    habilitar a opção.
15. Em **Profissionais**, gere um convite escolhendo o papel **Supervisor** (além de Profissional).
    Aceite o convite em outra aba/navegador anônimo e confirme que a conta criada já nasce com o
    papel correto.
16. Acesse **Auditoria** (administrador ou conta individual): veja o histórico de ações relevantes
    da sua clínica (cadastro de paciente, convites, mudança de permissões etc.), com filtro por tipo
    de entidade e período. Confirme que uma segunda clínica/conta não vê nenhuma entrada da primeira.
17. Em **Importar Pacientes**, envie um CSV com colunas em português (`nome`, `data de nascimento`,
    `responsável`, `diagnóstico`) — as colunas são detectadas automaticamente. Use
    **Pré-visualizar** para ver quais linhas são válidas e quais têm erro (nome ou data ausente/
    inválida) antes de **Confirmar importação**; o relatório final mostra quantos pacientes foram
    importados e o motivo de cada linha rejeitada.

### Fase 3 — Agenda e Scheduling

18. Acesse **Agenda** e clique em **+ Agendar**: escolha paciente, profissional (se for clínica) e o
    horário de início/fim. Tente agendar outro compromisso para o mesmo profissional em um horário
    sobreposto — o sistema bloqueia com "já tem um atendimento nesse horário" (Seção 32.2).
19. No compromisso criado, use **Confirmar**, depois **Faltou** ou **Cancelar** (ambos pedem um
    motivo: paciente, clínica, profissional ou força maior — Seção 32.3). Repita duas faltas seguidas
    para o mesmo paciente e confirme que administradores/supervisores recebem uma notificação de
    alerta de faltas consecutivas.
20. Clique em **Realizada** em um compromisso agendado/confirmado: você é levado à tela de Novo
    Atendimento já com paciente, profissional e data/hora preenchidos. Ao salvar o atendimento, o
    compromisso na Agenda passa automaticamente para "Realizada" e fica vinculado à sessão criada.
21. Use **Exportar (.ics)** para baixar a agenda da semana visível e importe o arquivo em um app de
    calendário (Google Calendar/Outlook) para conferir os eventos — a sincronização é hoje somente de
    exportação (unidirecional); importar de volta fica para uma fase futura, conforme o próprio PRD
    já prevê.

### Rodando os testes automatizados do backend

```bash
docker compose exec backend pytest -q
```

(ou localmente, sem Docker — ver `backend/README.md`). 112 testes cobrem, entre outros:

- **AC-01**: conta nova inicia com zero pacientes/sessões/dashboard.
- **AC-02** / **AC-03**: limite de 3 pacientes e bloqueio de foto no plano Free.
- **AC-04** / **AC-05**: tentativas individualizadas (Tentativa 1, 2, 3...) e cálculo de 66,7% de
  acerto reproduzindo o exemplo exato da Seção 11.4/33.1 do PRD.
- **AC-07** / **AC-14**: isolamento de histórico e de tenant (clínica/individual), estendido a Planos
  de Tratamento, Reports, Recursos e Dados Excluídos.
- **AC-08**: objetivo semelhante gera alerta com autor e área (similaridade por trigramas via
  `pg_trgm`), com opção de forçar o cadastro mesmo assim.
- **AC-09**: profissional convidado entra vinculado à clínica e não acessa a criação de convites.
- **AC-10** / **AC-11** / **AC-12**: exclusão (soft delete), restauração e reflexo imediato no
  dashboard.
- Cálculos de percentual de acerto, independência e distribuição de ajuda (Seção 14.4) como testes
  unitários isolados, e reaproveitados nos gráficos de Reports.
- Upload/download de Recursos Terapêuticos (mockando o S3 com `moto` — ver `backend/README.md`).
- Notificações por comentário/menção (incluindo isolamento de tenant — mencionar alguém de outra
  clínica nunca cria notificação cruzada) e Templates de Sessão (incluindo a regra de que um template
  específico de um paciente não pode ser usado para outro).
- Permissões "Configurável" da Seção 17.1 com valores padrão conservadores e liberação explícita por
  toggle, papel de Supervisor nos convites, log de auditoria escopado por tenant e importação de
  pacientes via CSV (linhas válidas x rejeitadas, detecção automática de colunas em português).
- Agenda/Scheduling: bloqueio de conflito de horário por profissional (e liberação do horário ao
  cancelar), transições de status válidas (agendada → confirmada → realizada, e para cancelada/não
  compareceu), motivo obrigatório em cancelamento/falta, alerta de faltas consecutivas restrito ao
  tenant certo, vínculo automático entre sessão criada e compromisso agendado, isolamento de tenant e
  de profissional/paciente atribuído, exportação `.ics` e cálculo de taxa de comparecimento.

## O que **não** está nesta fase

- **Resumo de IA real**: a Seção 14.5 do PRD pede um resumo gerado por IA. Combinamos com você
  adiar a integração com um provedor externo — o resumo hoje é um rascunho determinístico
  (baseado em regras, não em um modelo de linguagem), claramente rotulado como tal, com a mesma
  estrutura de edição/aprovação/versionamento que a IA real usará depois. Quando você definir o
  provedor (Anthropic, OpenAI, etc.) e me passar a chave, trocamos só essa peça.
- Seguindo o roadmap (Seção 31.1 do PRD), dentro da própria Fase 3: Stripe/planos pagos e 2FA ainda
  não foram implementados (próximas etapas, por escolha sua de fazer um bloco por vez). Timeline
  clínica, heatmaps e alertas inteligentes continuam previstos para a **Fase 4**.
- A importação de pacientes usa detecção automática de colunas por alias (cobrindo os cabeçalhos em
  português do próprio exemplo do PRD) em vez de uma UI de remapeamento manual coluna-a-coluna —
  uma simplificação de escopo deliberada, documentada em `csv_import_service.py`.
- **Agenda/Scheduling**: a visão de calendário é semanal (com navegação dia a dia dentro da semana);
  uma grade mensal completa não foi construída nesta etapa — a lista semanal já cobre a necessidade
  operacional descrita no PRD sem o investimento extra de uma grade de mês. A exportação `.ics` é
  unidirecional (só sai do Behavior Hub); sincronização bidirecional com Google Calendar/Outlook é
  citada no próprio PRD como item de fase futura. Lembretes automáticos hoje chegam apenas como
  notificação in-app para o profissional (Celery roda a cada hora, janela de 24h); o envio por e-mail
  para o profissional e o aviso ao responsável dependem de um provedor de e-mail e de um Family
  Portal/conta de responsável, nenhum dos dois ainda existentes no produto — mesma lacuna já
  documentada para convites e 2FA. O limiar de "faltas consecutivas" que dispara o alerta ao
  supervisor foi fixado em 2 (o PRD não especifica um número).

Consulte `backend/README.md` para observações sobre a curadoria da Training Library e o limite de
tamanho de arquivo dos Recursos Terapêuticos (Seção 34 — pendente de confirmação do PO).

## Estrutura do repositório

```
backend/    API FastAPI + SQLAlchemy + Alembic + testes (pytest)
frontend/   React + TypeScript + Tailwind
docs/       PRD (fonte única de verdade)
docker-compose.yml
```
