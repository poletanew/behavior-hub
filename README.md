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
  paciente.
- **Fase 3 — Autenticação de Dois Fatores (Seção 32.8)**: 2FA via aplicativo autenticador (TOTP),
  obrigatória para administradores de clínica no plano Enterprise e opcional para os demais perfis.
- **Fase 3 — Planos, Assinaturas e Stripe (Seção 8)**: tela de comparação de planos, criação de
  Stripe Checkout Session e Portal do Cliente, e processamento de webhooks (assinatura validada,
  idempotência por chave de deduplicação de evento) — **completa o roadmap da Fase 3**. Como você
  ainda não tem uma conta/chaves do Stripe, toda a integração está pronta e testada com o SDK do
  Stripe mockado, mas roda em modo "não configurado" até você cadastrar `STRIPE_SECRET_KEY`,
  `STRIPE_WEBHOOK_SECRET` e os Price IDs de cada plano (ver seção de configuração abaixo).
- **Fase 4a (bloco 1) — Alertas Clínicos Inteligentes (Seção 29.1/29.9, AC-15/AC-16)**: as quatro
  regras computáveis do PRD (sem coleta há 14 dias, regressão de 20 pontos percentuais na média
  móvel de 3 sessões, estagnação por 5 sessões, candidato a fading com independência ≥80%), com
  limiares configuráveis por clínica no plano Enterprise, recálculo em tempo real a cada tentativa
  salva, varredura diária para o alerta de "sem coleta", e notificação ao supervisor/profissional
  vinculado. Início da **Fase 4 — Inteligência Clínica** (Seção 29 do PRD).
- **Fase 4a (bloco 2) — Timeline Clínica (Seção 29.2, AC-18)**: linha do tempo única por paciente,
  consolidando atendimentos, ciclo de vida de objetivos (criado/atualizado/excluído/restaurado, com
  "objetivo dominado" tratado como marco distinto), vínculo/desvínculo de profissional e geração de
  relatórios — ordenada cronologicamente e sem duplicatas, com link de volta para o registro de
  origem quando aplicável.
- **Fase 4a (bloco 3) — Heatmap de Habilidades (Seção 29.3, AC-17)**: novo gráfico em Reports que
  mostra a intensidade de treino por área (Comunicação, Social, Autonomia, Motor, etc.) nos últimos
  30 dias corridos, sempre recalculado ao vivo a partir das tentativas reais — sem cache manual e
  independente dos filtros de período do restante do relatório.

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

### Fase 3 — Autenticação de Dois Fatores (2FA)

22. Acesse **Segurança** no menu lateral e clique em **Ativar autenticação de dois fatores**. Adicione
    a chave exibida em um aplicativo autenticador (Google Authenticator, Authy, 1Password — use
    "inserir chave manualmente", já que não há leitura de QR code nesta etapa) e digite o código de 6
    dígitos gerado para confirmar. Tente confirmar com um código errado primeiro — o sistema rejeita
    antes de aceitar o código correto.
23. Saia da conta e faça login novamente: em vez de entrar direto, você verá uma tela de
    "Verificação em duas etapas" pedindo o código do aplicativo. Um código errado é rejeitado; o
    código correto do momento libera o acesso normalmente.
24. Volte em **Segurança** e use **Desativar 2FA** — a desativação exige confirmar sua senha atual.

### Fase 3 — Planos, Assinaturas e Stripe

25. Acesse **Planos** no menu lateral: veja a tabela comparativa dos 4 planos (Seção 8.1) com o plano
    atual destacado. Sem as chaves do Stripe configuradas (o cenário padrão deste ambiente), clicar em
    **Assinar** ou em **Gerenciar assinatura** mostra uma mensagem clara explicando que o pagamento
    ainda não foi configurado — em vez de travar ou dar um erro genérico.
26. **Quando você tiver uma conta Stripe (modo teste)**, configure estas variáveis de ambiente no
    backend (`.env` ou `docker-compose.yml`) e reinicie:
    ```
    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_WEBHOOK_SECRET=whsec_...
    STRIPE_PRICE_ID_BASIC=price_...
    STRIPE_PRICE_ID_PREMIUM=price_...
    STRIPE_PRICE_ID_ENTERPRISE=price_...
    FRONTEND_URL=http://localhost:5173
    ```
    Crie os 3 Price IDs (um por plano pago) no Dashboard do Stripe em modo teste, e configure um
    endpoint de webhook apontando para `https://<seu-domínio>/v1/webhooks/stripe` (ou use o
    `stripe listen --forward-to localhost:8000/v1/webhooks/stripe` da Stripe CLI para testar
    localmente) escutando os eventos `checkout.session.completed`, `customer.subscription.updated`,
    `customer.subscription.deleted`, `invoice.payment_succeeded` e `invoice.payment_failed`. Depois
    disso, clicar em **Assinar** leva de fato ao Stripe Checkout, e completar o pagamento de teste
    atualiza automaticamente o plano/status aqui via webhook — nenhuma mudança de código é
    necessária, só a configuração.

### Fase 4a (bloco 1) — Alertas Clínicos Inteligentes

27. Na página de um paciente, cadastre um objetivo no **Plano de Tratamento** vinculado a um treino da
    Training Library. Registre pelo menos 3 atendimentos com bom desempenho (a maioria das tentativas
    corretas) e depois mais 3 atendimentos com desempenho bem pior (a maioria incorreta) para o mesmo
    treino — ao salvar a última tentativa, um alerta de **Regressão** aparece na página do paciente
    (queda ≥20 pontos percentuais na média móvel de 3 sessões — Seção 29.1/AC-16).
28. Registre 5 atendimentos seguidos com percentual de acerto praticamente igual (variação de até 5
    pontos percentuais) para gerar um alerta de **Estagnação**; ou 3 atendimentos com tentativas
    sempre marcadas como "Independente" (percentual de independência ≥80%) para gerar um alerta de
    **Candidato a fading**.
29. Como administrador, acesse **Configurações** e role até "Alertas Clínicos Inteligentes": os
    limiares aparecem, mas só ficam editáveis no plano Enterprise (nos demais planos, mostram o padrão
    de fábrica com uma mensagem explicando a restrição).
30. Um alerta novo gera uma notificação (sino no cabeçalho) para o administrador, supervisores e
    profissionais atribuídos ao paciente. Um alerta permanece "ativo" até a condição deixar de ser
    verdadeira (por exemplo, um atendimento novo resolve o alerta de "sem coleta") — não é preciso
    apagar ou dispensar manualmente.

### Fase 4a (bloco 2) — Timeline Clínica

31. Na página de um paciente, clique em **Timeline** (ao lado de "Plano de Tratamento" e "Reports").
    A tela mostra, da mais recente para a mais antiga, todos os eventos já registrados: atendimentos,
    criação/atualização/exclusão/restauração de objetivos, vínculo e desvínculo de profissional, e
    geração de relatórios.
32. Quando um objetivo muda de status para **Dominado**, a timeline mostra um "Marco de evolução"
    (badge amarelo) em vez do evento genérico de atualização — destacando visualmente o marco clínico
    em meio às demais edições do plano de tratamento.
33. Cada evento com um registro de origem correspondente (atendimento, plano de tratamento, relatório)
    é clicável e leva direto para a tela de origem.

### Fase 4a (bloco 3) — Heatmap de Habilidades

34. Na página de Reports de um paciente, o novo card **Heatmap de habilidades** aparece logo acima
    dos demais gráficos, mostrando a intensidade de treino por área (categoria do treino) nos
    últimos 30 dias corridos — sempre esse período fixo, mesmo que você mude os filtros de "De/Até"
    do restante do relatório.
35. Registre tentativas em treinos de áreas diferentes (por exemplo, mais tentativas em
    "Comunicação" do que em "Motor"); a barra de cada área é dimensionada proporcionalmente à área
    com mais tentativas, com um rótulo relativo (Baixa/Média/Alta/Muito alta) e a contagem exata ao
    lado.
36. Ao salvar uma nova tentativa, o heatmap reflete a mudança imediatamente na próxima vez que a
    página de Reports é carregada — não existe um valor em cache desatualizado.

### Rodando os testes automatizados do backend

```bash
docker compose exec backend pytest -q
```

(ou localmente, sem Docker — ver `backend/README.md`). 162 testes cobrem, entre outros:

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
- 2FA: fluxo completo de setup/ativação/desativação, rejeição de código inválido em cada etapa,
  desafio de segunda etapa no login apenas quando habilitado, e a flag de exigência para
  administrador de clínica Enterprise.
- Stripe/Planos: checkout e portal do cliente com o SDK do Stripe mockado (criação de customer,
  Checkout Session, Billing Portal Session), erro claro quando não configurado, os 5 tipos de evento
  de webhook processados (`checkout.session.completed`, `customer.subscription.updated/deleted`,
  `invoice.payment_succeeded/failed`), idempotência (reentrega do mesmo evento é ignorada), rejeição
  de assinatura inválida, e a regra "nunca confiar apenas no frontend" (plano pago só concede acesso
  quando a assinatura está de fato ativa/em trial — uma assinatura em atraso ou cancelada volta a
  valer como Free mesmo que o rótulo do plano ainda não tenha sido atualizado).
- Alertas Clínicos Inteligentes: as 4 regras da Seção 29.1 (AC-15/AC-16 reproduzindo o exemplo exato
  de queda de 20 pontos percentuais), objetivo dominado nunca gera estagnação, objetivo descontinuado
  resolve todos os alertas ativos, deduplicação (nunca dois alertas ativos do mesmo tipo para o mesmo
  objetivo), resolução automática quando a condição deixa de ser verdadeira, notificação ao
  administrador/supervisor/profissional atribuído, isolamento de tenant, e a exigência de plano
  Enterprise para configurar os limiares.
- Timeline Clínica: paciente novo começa com timeline vazia, atendimento e ciclo de vida completo de
  objetivo (criado/atualizado/excluído/restaurado) aparecem como eventos, "objetivo dominado" é um
  marco distinto do evento genérico de atualização (o evento genérico correspondente não aparece
  duplicado), vínculo/desvínculo de profissional e geração de relatório aparecem com o rótulo
  correto, ordenação cronológica sem duplicatas mesmo com eventos de fontes diferentes na mesma
  janela de tempo (AC-18), e isolamento de tenant.
- Heatmap de Habilidades: distribuição real de tentativas por área nos últimos 30 dias (AC-17),
  rótulo de intensidade relativa correto para cada faixa (baixa/média/alta/muito alta), exclusão de
  tentativas com mais de 30 dias, recálculo imediato ao salvar uma nova tentativa, e independência
  total dos filtros de período do restante do relatório (o heatmap nunca muda quando o usuário altera
  "De/Até", "Treino" ou "Área" dos outros gráficos).

## O que **não** está nesta fase

- **Resumo de IA real**: a Seção 14.5 do PRD pede um resumo gerado por IA. Combinamos com você
  adiar a integração com um provedor externo — o resumo hoje é um rascunho determinístico
  (baseado em regras, não em um modelo de linguagem), claramente rotulado como tal, com a mesma
  estrutura de edição/aprovação/versionamento que a IA real usará depois. Quando você definir o
  provedor (Anthropic, OpenAI, etc.) e me passar a chave, trocamos só essa peça.
- Seguindo o roadmap (Seção 31.1 do PRD): a Fase 3 está completa. Os dashboards de Supervisor e de
  Gestor ainda não foram implementados — próximos blocos da Fase 4a. A Fase 4b (sugestões geradas por
  IA, módulo de avaliações VB-MAPP/ABLLS-R, Biblioteca Inteligente) e a Fase 5 (Family Portal, ML
  preditivo) continuam para depois.
- **Timeline Clínica**: a linha do tempo é montada a partir de fontes já existentes (atendimentos,
  log de auditoria de objetivos/atribuições, resumos de relatório) em vez de um novo modelo dedicado
  de "evento" — evita duplicar armazenamento e manter tudo sincronizado. Como consequência,
  avaliações formais (Seção 30, ainda não implementada) e intercorrências/notas livres não aparecem
  na timeline ainda; entram quando esses módulos existirem.
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
- **2FA**: implementado apenas via aplicativo autenticador (TOTP), que é a "primeira opção" pedida
  pela Seção 32.8. O fallback por e-mail citado no PRD não foi implementado — depende da mesma
  decisão de provedor de e-mail já registrada para convites e lembretes de agenda. A tela de
  configuração mostra a chave em texto para entrada manual no aplicativo (sem gerar uma imagem de QR
  code), uma simplificação de UI razoável já que todo aplicativo autenticador comum aceita entrada
  manual da chave. A exigência de 2FA para administradores Enterprise já está implementada e
  testável (inclusive com um banner de aviso no app), e agora passa a valer na prática assim que uma
  clínica migrar de fato para o plano Enterprise via Stripe.
- **Alertas Clínicos Inteligentes**: só disparam para objetivos com pelo menos um treino vinculado
  (`ObjectiveTraining`) — sem esse vínculo estrutural não há como derivar uma série histórica de
  tentativas por objetivo. A interpretação adotada para "estagnação dentro de uma faixa de ±5 pontos
  percentuais" foi variação (máximo − mínimo) ≤ 5pp entre as sessões, já que o PRD formaliza a fórmula
  exata apenas para regressão (Seção 29.1); a fórmula de regressão em si segue literalmente o texto e
  o exemplo do PRD (AC-16). O recálculo em tempo real cobre
  regressão/estagnação/fading a cada tentativa salva; o alerta de "sem coleta" depende
  necessariamente da varredura diária via Celery, já que não há evento de tentativa para dispará-lo.
- **Stripe/Planos**: como você ainda não tem uma conta Stripe, não há chaves reais configuradas neste
  ambiente — `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` e os Price IDs de cada plano continuam
  vazios até você criá-los (veja a seção de configuração acima). Toda a integração (customer,
  Checkout, Portal do Cliente, processamento dos 5 eventos de webhook) está implementada e coberta
  por testes com o SDK do Stripe mockado — falta apenas a configuração real para funcionar de ponta a
  ponta. O processamento de webhook acontece de forma síncrona dentro da própria requisição (usando a
  mesma sessão de banco do request), em vez de ser despachado para uma fila Celery separada como o
  PRD descreve na Seção 28.4 — uma simplificação deliberada, já que o Stripe já reentrega
  automaticamente webhooks que não retornam 2xx (e a tabela de deduplicação de eventos garante que
  uma reentrega nunca reaplica o efeito duas vezes), e uma fila assíncrona verdadeira adicionaria uma
  segunda conexão de banco fora da transação da requisição, o que conflitaria com o isolamento de
  transação por teste usado na suíte automatizada. Faturamento por sessão (Seção 32.10, cobrança que
  a clínica emite a seus próprios pacientes/convênios) é um recurso diferente, fora de escopo aqui.

Consulte `backend/README.md` para observações sobre a curadoria da Training Library e o limite de
tamanho de arquivo dos Recursos Terapêuticos (Seção 34 — pendente de confirmação do PO).

## Estrutura do repositório

```
backend/    API FastAPI + SQLAlchemy + Alembic + testes (pytest)
frontend/   React + TypeScript + Tailwind
docs/       PRD (fonte única de verdade)
docker-compose.yml
```
