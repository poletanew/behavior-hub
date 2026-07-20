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
- **Fase 4a (bloco 4) — Dashboard para Supervisor (Seção 29.4)**: painel consolidado por equipe
  (visível apenas a administradores de clínica e supervisores) com percentual de sessões completas
  por terapeuta, adesão ao plano de tratamento (reaproveitando os alertas de "sem coleta" já
  existentes) e alertas automáticos de baixa adesão ou ausência de registro recente.
- **Fase 4a (bloco 5) — Dashboard para Gestor (Seção 29.5)**: visão de negócio da clínica (visível
  apenas ao administrador da clínica) com pacientes ativos, profissionais ativos, sessões realizadas,
  horas clínicas registradas e taxa de ocupação, filtráveis por período (mês corrente por padrão) —
  **fecha o roadmap da Fase 4a — Inteligência Clínica básica**. Indicadores de receita/faturamento
  não estão incluídos por não haver um módulo de cobrança por paciente (ver nota de escopo abaixo).
- **Fase 4b (bloco 1) — Sugestões Clínicas (Seção 29.1)**: início da **Fase 4b — Inteligência
  avançada**. Três recomendações geradas por regra (não por um provedor de IA real — ver nota de
  escopo abaixo): sugestão de **fading** (reduzir o nível de ajuda) quando a independência já
  atingiu o limiar de candidato a fading; sugestão de **"objetivo pode ser considerado dominado"**
  (Seção 29.9) quando o percentual de acerto se mantém acima de um limiar configurável por N
  sessões; e sugestão de **novo programa** quando o paciente tem uma área de habilidade ainda não
  trabalhada em nenhum objetivo ativo, mas com treinos disponíveis na Training Library. Toda
  sugestão é uma recomendação editável — aprovar ou descartar apenas registra a decisão do
  profissional (com auditoria), nunca aplica a mudança automaticamente nos dados clínicos.
- **Fase 4b (bloco 2) — Módulo de Avaliações Padronizadas (Seção 30, AC-19)**: registro de
  aplicações dos protocolos-piloto **VB-MAPP** e **ABLLS-R** (pontuação bruta por domínio,
  `normalized_pct` calculado automaticamente), comparação entre duas ou mais aplicações do mesmo
  protocolo com ganho absoluto/percentual por domínio, avaliações agora aparecem na Timeline Clínica
  e em Dados Excluídos (soft delete/restauração), texto interpretativo da comparação gerado por
  regra (não IA real — mesma nota de escopo do bloco anterior).
- **Fase 4b (bloco 3) — Biblioteca Inteligente (Seção 29.7)**: `ResourceLink`, o vínculo estruturado
  recurso↔treino e recurso↔objetivo que a Seção 29.7 marcava como dependência bloqueante — agora
  implementado. Populado manualmente (tagueamento) pelo profissional, com uma pontuação de
  relevância (1–5), a partir da Training Library (vincular a um treino) ou do Plano de Tratamento
  (vincular a um objetivo). Ao abrir um objetivo, os recursos recomendados agregam os vínculos
  diretos do objetivo com os vínculos dos treinos que ele usa — **fecha o roadmap da Fase 4b —
  Inteligência Clínica avançada**.
- **Fase 5 (bloco 1) — Portal da Família (Seção 29.6/17.2)**: novo tipo de conta `family`, com acesso
  restrito por paciente via whitelist explícita (evolução, agendamentos, orientações, materiais,
  mensagens — tudo começando desligado). Revogação imediata via contador `token_version` embutido no
  JWT, sem precisar de uma tabela de sessões.
- **Fase 5 (bloco 2) — White-label por Clínica (Seção 32.9)**: nome exibido, cor de destaque e logo
  personalizáveis por clínicas Enterprise ativas, aplicados nos relatórios exportados e no Portal da
  Família, sem alterar a marca dentro do próprio produto.
- **Fase 5 (bloco 3) — Faturamento por Sessão (Seção 32.10)**: registro de controle interno do que a
  clínica cobra por sessão realizada (valor, vencimento, status pendente/pago/em atraso), totalmente
  independente da assinatura SaaS via Stripe, disponível nos planos Premium/Enterprise.
- **Fase 5 (bloco 4) — Lista de Espera (Seção 32.11)**: cadastro simplificado de pacientes em
  triagem antes da admissão formal, com conversão em paciente completo sem redigitação.
- **Fase 5 (bloco 5) — Anotação por Voz (Seção 32.12)**: ditado por voz da observação da tentativa
  via Web Speech API nativa do navegador, sempre editável antes de salvar — **fecha os itens da Fase
  5 e do roadmap detalhado da Seção 31 que dá para construir sem inventar requisito ou dado clínico
  que o PRD não especifica** (ver "O que não está nesta fase" para o detalhamento dos três itens
  conscientemente deixados de fora: ondas seguintes de protocolos de avaliação, ML preditivo e
  internacionalização).
- **Fase 6 (bloco 1) — Addendum de Melhorias v2.1, RF-01 e RF-02** (ver
  `docs/Behavior_Hub_Addendum_v2.1.pdf`): favicon com o símbolo reduzido da marca (rede de nós
  formando a letra "B", Seção 23.7) em todas as páginas, logotipo vertical centralizado na tela de
  login/2FA acima dos campos de formulário (Seção 23.8), e renomeação de "Dashboard" para "Área de
  Trabalho" em todo texto visível ao usuário (rótulo do menu e título da página) — sem alterar
  comportamento ou a rota `/dashboard` internamente.

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

### Fase 4a (bloco 4) — Dashboard para Supervisor

37. Como administrador de clínica ou supervisor, acesse **Painel de Supervisão** no menu lateral
    (não aparece para profissionais comuns nem para contas individuais, que não têm uma "equipe").
    A tabela lista cada terapeuta ativo da clínica com: pacientes atribuídos, sessões completas,
    faltas, percentual de sessões completas, objetivos ativos, percentual de adesão ao plano de
    tratamento e os alertas de **Baixa adesão** / **Sem registro recente**, quando aplicável.
38. A adesão ao plano de tratamento reaproveita o mesmo alerta de "sem coleta" da Seção 29.1: um
    objetivo ativo com um alerta de sem-coleta ativo conta contra a adesão do terapeuta responsável
    pelo paciente. Quando a adesão cai abaixo de 70%, o terapeuta é marcado com "Baixa adesão".
39. "Sem registro recente" aparece quando o terapeuta tem pacientes atribuídos mas nenhum
    atendimento registrado dentro da janela configurável de "sem coleta" da clínica (14 dias por
    padrão, mesma configuração da Seção 29.1) — permitindo intervenção proativa da coordenação
    clínica antes que o problema apareça só no relatório do paciente.

### Fase 4a (bloco 5) — Dashboard para Gestor

40. Como administrador de clínica, acesse **Painel de Gestão** no menu lateral (não aparece para
    supervisores, profissionais nem contas individuais — é uma visão de negócio, não clínica). Por
    padrão mostra o mês corrente; ajuste "De/Até" e clique em Aplicar para outro período.
41. Os cinco indicadores — pacientes ativos, profissionais ativos, sessões realizadas, horas
    clínicas e taxa de ocupação — são somas/contagens diretas dos mesmos dados operacionais já
    usados no resto do sistema (pacientes, atendimentos, agenda), sem nenhuma planilha ou tabela
    paralela.
42. Horas clínicas soma apenas a duração de atendimentos vinculados a um compromisso da Agenda com
    status "realizada" (a duração vem do horário agendado); um atendimento registrado sem
    compromisso associado conta para "sessões realizadas" mas não tem duração conhecida, então não
    entra na soma de horas.

### Fase 4b (bloco 1) — Sugestões Clínicas

43. Na página de um paciente, cadastre um objetivo vinculado a um treino da Training Library e
    registre 3 atendimentos consecutivos com tentativas sempre "Independente" — além do alerta de
    candidato a fading já existente (Fase 4a), agora também aparece uma **sugestão de Fading** no
    novo card "Sugestões clínicas", com os botões Aprovar/Descartar.
44. Registre 3 atendimentos consecutivos com pelo menos 80% de acerto para o mesmo objetivo (ainda
    não marcado como dominado): uma sugestão de **"Objetivo dominado"** aparece, com o texto exato
    do exemplo da Seção 29.9 do PRD ("Objetivo pode ser considerado dominado com base no critério
    configurado").
45. Se o paciente já tem um objetivo ativo em uma área (por exemplo, Comunicação) mas nunca teve
    nenhum objetivo em outra área com treinos cadastrados na Training Library (por exemplo, Motor),
    uma sugestão de **Novo programa** aparece recomendando um treino dessa área ainda não trabalhada.
46. Clicar em **Aprovar** ou **Descartar** apenas registra a decisão (com data e autor, auditável) —
    nenhuma sugestão altera automaticamente o plano de tratamento, o status do objetivo ou os níveis
    de ajuda; a ação real (marcar como dominado, criar o novo objetivo, reduzir a ajuda na próxima
    sessão) continua sendo feita pelo profissional nos fluxos já existentes. Uma vez decidida, a
    mesma sugestão nunca reaparece.
47. Como administrador, em **Configurações**, role até "Alertas Clínicos Inteligentes": os dois
    novos limiares (sessões e percentual de acerto para a sugestão de domínio) aparecem junto aos
    limiares de alerta já existentes, com a mesma regra de edição restrita ao plano Enterprise.

### Fase 4b (bloco 2) — Módulo de Avaliações Padronizadas

48. Na página de um paciente, acesse **Avaliações** (ao lado de Plano de Tratamento/Reports/
    Timeline). Escolha VB-MAPP ou ABLLS-R, clique em **Nova avaliação**, informe a data de aplicação
    e as pontuações por domínio — o VB-MAPP já vem com o máximo de cada domínio pré-preenchido
    (16 domínios somando 170 pontos); o ABLLS-R exige que você informe o máximo de cada domínio, já
    que a contagem de tarefas varia por edição do instrumento.
49. Tentar registrar duas aplicações do mesmo protocolo na mesma data para o mesmo paciente é
    bloqueado (Seção 27.3 — nunca há duplicidade de aplicação no mesmo dia).
50. Com pelo menos duas aplicações do mesmo protocolo registradas, marque-as na lista e clique em
    **Comparar selecionadas**: a tabela mostra o percentual inicial/final, o ganho absoluto (em
    pontos percentuais) e o ganho relativo por domínio em comum entre a mais antiga e a mais recente,
    junto com um texto interpretativo (rascunho por regras, claramente rotulado, nunca diagnóstico).
51. Cada avaliação registrada passa a aparecer na **Timeline Clínica** do paciente ("Avaliação
    VB-MAPP aplicada") e pode ser excluída/restaurada por **Dados Excluídos**, como qualquer outro
    dado clínico do produto.

### Fase 4b (bloco 3) — Biblioteca Inteligente

52. Na **Training Library**, selecione um treino: um novo card "Recursos vinculados" aparece no
    painel de detalhes, com um seletor para vincular qualquer Recurso Terapêutico já cadastrado a
    esse treino, com uma nota de relevância de 1 a 5.
53. No **Plano de Tratamento**, abra "Ver detalhes" em um objetivo: o card "Recursos recomendados"
    mostra os recursos vinculados diretamente a esse objetivo **e** os recursos vinculados a
    qualquer treino que o objetivo usa — por exemplo, um recurso vinculado ao treino "Tolerância à
    espera" aparece automaticamente recomendado em qualquer objetivo que use esse treino, marcado
    como "(via treino)".
54. A pontuação de relevância é sempre definida manualmente pelo profissional ao vincular — não há
    inferência automática por IA (a Seção 29.7 do PRD já previa isso: "não há dado histórico
    suficiente para a IA inferir a relação sozinha no lançamento"). Clicar em **Remover** desfaz o
    vínculo a qualquer momento.

### Fase 5 (bloco 1) — Portal da Família

55. Na página de um paciente, acesse **Portal da Família** (ao lado de Avaliações). Convide um
    responsável informando o e-mail: um link de convite é gerado (mesmo fluxo de convite de
    profissionais, agora com um novo papel `family` e obrigatoriamente vinculado a este paciente).
56. Ao aceitar o convite, a conta nasce **sem nenhuma categoria liberada** — cinco caixas de
    seleção (Evolução, Próximos agendamentos, Orientações da equipe, Materiais para casa, Mensagens)
    controlam exatamente o que aparece para o responsável, sempre por whitelist explícita (Seção
    17.2: "o portal só exibe o que foi explicitamente liberado"). Marque as categorias desejadas.
57. Faça login com a conta do responsável: você é levado a uma área totalmente separada
    (`/family-portal`, sem a barra lateral clínica) com abas apenas para as categorias liberadas.
    Evolução mostra os mesmos dados de Reports (mas resumidos); Agenda mostra só compromissos
    futuros; Orientações mostra apenas resumos de relatório já **aprovados** pela equipe (nunca um
    rascunho); Materiais mostra os recursos recomendados dos objetivos ativos do paciente
    (reaproveitando a Biblioteca Inteligente); Mensagens é um canal simples de texto entre a família
    e a equipe.
58. Volte como administrador/profissional em **Portal da Família** e clique em **Revogar acesso**: a
    sessão do responsável é invalidada imediatamente (não apenas na próxima expiração de token) — ao
    recarregar a página, ele é deslogado na hora, mesmo com um token de acesso ainda "válido" pela
    data de expiração.

### Fase 5 (bloco 2) — White-label por Clínica (Enterprise)

59. Acesse **White-label** no menu lateral (administrador de clínica). Em qualquer plano abaixo do
    Enterprise ativo, o formulário aparece desabilitado com um aviso explicando o requisito e um link
    para **Planos**.
60. Depois que a clínica estiver no plano Enterprise com assinatura ativa, defina um **nome exibido**
    e uma **cor de destaque** e salve — eles passam a aparecer no PDF exportado de Reports (título e
    cor do cabeçalho da tabela) e, se a clínica tiver responsáveis com Portal da Família, na faixa de
    identidade visual do topo do portal deles.
61. A **URL do logo** só é exibida no Portal da Família (via `<img>` no navegador do responsável) —
    o PDF exportado no backend nunca busca essa URL, para não abrir uma superfície de SSRF ao
    servidor. O rodapé "Powered by Behavior Hub" nunca desaparece, com ou sem white-label ativo.
62. Se a clínica perder o status Enterprise ativo (downgrade, assinatura em atraso/cancelada), o
    white-label para de valer imediatamente nas próximas requisições — mesmo que os campos continuem
    salvos no banco, prontos para reativar sem reconfigurar tudo se a clínica voltar ao Enterprise.

### Fase 5 (bloco 3) — Faturamento por Sessão (Premium/Enterprise)

63. Abra um **Atendimento** já registrado: o card **Faturamento** (visível só para administrador de
    clínica ou conta individual) mostra um formulário para lançar o valor cobrado por aquela sessão,
    com vencimento e observações opcionais.
64. Em qualquer plano abaixo de Premium, ao tentar salvar aparece o aviso "disponível apenas nos
    planos Premium ou Enterprise" com um link para **Planos** — a tela de cobrança sempre aparece
    (só o salvamento é bloqueado no backend), já que ver o formulário não expõe nenhum dado sensível.
65. Depois de lançada, a cobrança mostra o status (Pendente/Pago/Em atraso) com um seletor para
    trocar diretamente ali — marcar como Pago registra a data/hora automaticamente; voltar para
    Pendente ou Em atraso limpa essa data.
66. Acesse **Faturamento** no menu lateral para ver todas as cobranças de um paciente e trocar o
    status em lote, e use **Exportar CSV** para baixar o "financeiro da clínica" inteiro (todos os
    pacientes do tenant, com filtro opcional de período via querystring) — pedido explícito da Seção
    32.10.
67. Este faturamento é inteiramente independente da assinatura SaaS via Stripe (Seção 8): é só um
    registro de controle interno da clínica para o que ela cobra dos próprios pacientes/convênios,
    nunca processado por um gateway de pagamento real.

### Fase 5 (bloco 4) — Lista de Espera (Waitlist)

68. Acesse **Lista de Espera** no menu lateral e clique em **+ Adicionar à lista**: cadastre um nome
    e, opcionalmente, data de nascimento, responsável, telefone/e-mail de contato e observações — os
    únicos campos realmente mínimos para uma triagem antes da admissão formal (Seção 32.11).
69. Em uma entrada com status **Aguardando**, use **Converter em paciente**: se a data de nascimento
    já tiver sido capturada na triagem, ela é reaproveitada automaticamente; senão, o formulário pede
    só o que falta. Ao confirmar, um paciente completo é criado (nome, responsável e observações
    reaproveitados sem redigitar) e você é levado direto à página dele.
70. **Descartar** marca a entrada como encerrada sem criar paciente (por exemplo, quando a família
    desiste da triagem) — tanto conversão quanto descarte são ações finais: uma entrada já
    convertida/descartada não pode ser editada nem convertida de novo.

### Fase 5 (bloco 5) — Anotação por Voz (Voice-to-Text), fecha os itens buildáveis da Fase 5 e do roadmap

71. Em um **Atendimento**, ao lado do campo "Observação (opcional)" de qualquer treino, um botão
    **Ditar** aparece nos navegadores que suportam a Web Speech API nativa (Chrome/Edge; não aparece
    no Firefox, que ainda não suporta essa API — o restante do formulário continua funcionando
    normalmente sem o botão).
72. Clique em **Ditar**, fale a observação da tentativa e o texto transcrito é adicionado ao campo —
    **sempre editável antes de salvar**, exatamente como a Seção 32.12 pede: nada é enviado
    automaticamente, você pode corrigir a transcrição e só então clicar em "+ Adicionar tentativa".
73. A transcrição roda inteiramente no navegador do profissional (nenhum áudio é enviado ao backend
    do Behavior Hub nem a nenhum provedor cuja chave você precisaria configurar) — útil justamente
    quando as mãos estão ocupadas conduzindo a sessão.

### Rodando os testes automatizados do backend

```bash
docker compose exec backend pytest -q
```

(ou localmente, sem Docker — ver `backend/README.md`). 253 testes cobrem, entre outros:

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
- Dashboard para Supervisor: acesso restrito a administrador de clínica e supervisor (profissional
  comum e conta individual recebem 403), cálculo correto de percentual de sessões completas por
  terapeuta, adesão de 100% quando não há alerta de sem-coleta ativo, adesão de 0% e os dois alertas
  automáticos corretos quando um alerta de sem-coleta está ativo para o único objetivo do terapeuta,
  nenhum alerta falso para terapeuta sem paciente atribuído, e isolamento de tenant (terapeutas de
  uma clínica nunca aparecem no painel de outra).
- Dashboard para Gestor: acesso restrito ao administrador de clínica (supervisor, profissional e
  conta individual recebem 403), contagem correta de pacientes/profissionais ativos (excluindo
  excluídos e inativos), sessões e horas clínicas somadas apenas dentro do período informado, taxa
  de ocupação calculada corretamente (completas / (completas + faltas + canceladas)), período padrão
  igual ao mês corrente quando nenhum filtro é informado, e isolamento de tenant.
- Sugestões Clínicas: sugestão de fading gerada e nunca duplicada mesmo após recálculos repetidos,
  sugestão de "objetivo dominado" com o texto exato do exemplo do PRD e ausente quando o objetivo já
  está marcado como dominado, sugestão de novo programa apenas quando há uma área de referência já
  trabalhada (sem alertar já no primeiro objetivo do paciente) e nunca duplicada para o mesmo treino,
  aprovar/descartar registra a decisão sem alterar o objetivo automaticamente (verificado
  explicitamente), aprovar uma sugestão já decidida retorna conflito, e isolamento de tenant.
- Avaliações Padronizadas: `normalized_pct` calculado corretamente a partir de `raw_value`/
  `max_value`, protocolo sem domínio-padrão (ABLLS-R) exige `max_value` explícito e protocolo com
  padrão (VB-MAPP, somando os 170 pontos oficiais em 16 domínios) aceita omissão, rejeição de
  `domain_code` desconhecido e de `raw_value` acima do máximo, bloqueio de duplicidade de protocolo +
  data (Seção 27.3), comparação entre duas aplicações produz ganho absoluto e percentual corretos
  por domínio usando `normalized_pct` (AC-19), exigência de pelo menos duas avaliações para comparar,
  soft delete/restauração via Dados Excluídos, presença na Timeline Clínica, e isolamento de tenant.
- Biblioteca Inteligente: vínculo recurso↔treino e recurso↔objetivo criado e listado corretamente,
  recomendação do objetivo agrega vínculos diretos com vínculos dos treinos vinculados (sem exigir
  vínculo direto), bloqueio de vínculo duplicado, exigência de exatamente um alvo (treino OU
  objetivo, nunca os dois nem nenhum), limite de pontuação de relevância (1–5), permissão de remoção
  restrita ao autor do vínculo ou administrador, recurso privado de outro profissional nunca aparece
  na recomendação (mesma regra de visibilidade da Biblioteca de Recursos), e isolamento de tenant.
- Portal da Família: convite exige `patient_id` (e rejeita `patient_id` em convites de outros
  papéis), aceite cria `FamilyAccess` com todas as flags em `False` e `consent_given_at` preenchido,
  conta `family` recebe 403 em qualquer rota normal de paciente, cada categoria (evolução,
  agendamentos, orientações, materiais, mensagens) só responde depois de liberada explicitamente,
  orientações mostram apenas resumos com status aprovado, mensagens funcionam nos dois sentidos
  (família ↔ equipe), revogação bumpa `token_version` e invalida imediatamente o token de acesso já
  emitido (mesmo antes de expirar), convite de responsável só é permitido para quem já tem acesso ao
  paciente (isolamento de tenant no convite), e profissional individual (sem clínica) também
  consegue convidar um responsável para seus próprios pacientes.
- White-label: configuração rejeitada fora do plano Enterprise e também quando Enterprise mas com
  assinatura inativa (nunca confiar apenas no rótulo do plano), cor hexadecimal inválida rejeitada,
  configuração aplicada corretamente refletida no Family Portal (branding liga/desliga junto com o
  status real da assinatura), acesso restrito a administrador de clínica (profissional e conta
  individual recebem 403), e isolamento de tenant.
- Faturamento por Sessão: criação bloqueada fora do Premium/Enterprise e também quando o plano é
  correto mas a assinatura está inativa, valor zero/negativo rejeitado, uma sessão nunca recebe duas
  cobranças (conflito 409 na segunda tentativa), apenas administrador de clínica/conta individual
  pode criar ou editar (profissional recebe 403), marcar como Pago preenche `paid_at` e voltar para
  Pendente/Em atraso limpa esse campo, listagem por paciente e exportação CSV tenant-wide funcionam,
  e isolamento de tenant tanto na listagem quanto na exportação.
- Lista de Espera: conversão sem data de nascimento capturada na triagem exige o campo no momento da
  conversão (422 se ausente), conversão reaproveita a data já capturada quando presente, entrada
  descartada ou já convertida não pode ser editada nem convertida de novo (conflito 409), filtro por
  status funciona, profissional sem a permissão configurável de "cadastrar paciente" recebe 403,
  conta individual também consegue usar a lista de espera, e isolamento de tenant.

## O que **não** está nesta fase

- **Resumo de IA real**: a Seção 14.5 do PRD pede um resumo gerado por IA. Combinamos com você
  adiar a integração com um provedor externo — o resumo hoje é um rascunho determinístico
  (baseado em regras, não em um modelo de linguagem), claramente rotulado como tal, com a mesma
  estrutura de edição/aprovação/versionamento que a IA real usará depois. Quando você definir o
  provedor (Anthropic, OpenAI, etc.) e me passar a chave, trocamos só essa peça.
- Seguindo o roadmap (Seção 31.1/31.2 do PRD): **as Fases 1 a 4b estão concluídas**, e a Fase 5
  entregou tudo o que tinha um requisito concreto e implementável — **Portal da Família** (Seção
  29.6/17.2), **White-label por Clínica** (Seção 32.9), **Faturamento por Sessão** (Seção 32.10),
  **Lista de Espera** (Seção 32.11) e **Anotação por Voz** (Seção 32.12). Isso fecha o roadmap
  detalhado da Seção 31 até onde ele pode ser construído sem inventar requisito ou dado que o PRD não
  especifica. Três itens do escopo original da Fase 5 ficaram deliberadamente de fora, cada um por um
  motivo diferente, documentado aqui em vez de silenciosamente ignorado:
  - **Ondas seguintes de protocolos de avaliação** (AFLS, PEAK, ESDM, CARS, M-CHAT, IDADI, Vineland,
    Sensory Profile, Portage, SRS-2, Socially Savvy) — a própria Seção 30.1 exige que cada protocolo
    seja "validado com profissional especialista no instrumento antes da liberação". Implementá-los
    agora exigiria inventar o esquema de domínios/pontuação máxima de instrumentos proprietários sem
    essa validação — o mesmo risco de fabricação de dado clínico já evitado na decisão do ABLLS-R
    (Fase 4b). Fica pronto para entrar assim que você validar um protocolo por vez com um
    especialista, reaproveitando a mesma arquitetura `ProtocolDefinition` já construída.
  - **Machine Learning preditivo** (Seção 29.10) — a própria seção descreve isso como "visão de
    futuro": modelos que estimem risco de regressão, velocidade esperada de aprendizagem e
    efetividade histórica de estratégias, condicionados a "volume suficiente de coletas acumuladas na
    base". Não há critério de aceite, schema de features, nem um provedor/framework de ML definido —
    apenas uma direção declarada. Treinar (ou fingir que treinamos) um modelo agora seria inventar
    tanto o método quanto os resultados; o dado real para isso só existe depois de meses de uso em
    produção, o que este ambiente de desenvolvimento não tem como simular de forma honesta.
  - **Internacionalização** (Seção 20, Requisitos Não-Funcionais) — o texto exato do PRD é
    "Interface preparada para tradução, embora português seja o idioma inicial", ou seja, um requisito
    de arquitetura ("preparada para"), não um pedido para efetivamente lançar outro idioma. Todo o
    frontend hoje tem strings em português direto no JSX, sem nenhuma biblioteca de i18n
    (react-i18next ou equivalente) nem catálogo de textos extraído. Fazer essa extração retroativa
    em ~30 páginas é um refactor mecânico de alto risco de regressão sem nenhum ganho visível até que
    exista um segundo idioma real para validar contra — e você ainda não indicou qual seria esse
    idioma nem forneceu nenhuma tradução. Preferimos deixar isso explícito a fingir uma preparação
    para tradução que na prática não foi testada com nenhum idioma além do português.
- **Portal da Família**: revogação de acesso é imediata via um contador `token_version` no usuário,
  embutido em todo JWT emitido e conferido a cada requisição — bumpar esse contador invalida
  instantaneamente qualquer token já emitido para aquele responsável, sem precisar de uma tabela de
  sessões ativas completa (decisão registrada em detalhe no `backend/README.md`). O bloqueio de
  contas `family` nas rotas normais de paciente foi feito num único ponto central
  (`patient_service.get_patient_or_404`/`list_patients`, reaproveitado por quase todo endpoint
  escopado a paciente) em vez de auditar cada rota individualmente; como exposição residual
  conhecida e aceita, endpoints não escopados a paciente (Training Library, Recursos, lista de
  Profissionais) não têm essa checagem explícita — uma conta `family` que tentasse chamá-los via API
  direta ainda seria bloqueada por não ter `clinic_id`/atribuições compatíveis na prática, mas isso
  não foi coberto por teste automatizado dedicado nesta rodada. "Orientações da equipe" reaproveita
  os `ReportSummary` já existentes (Seção 14.5), mostrando apenas os com status `approved`; "materiais
  para casa" reaproveita a agregação de `resource_link_service` já construída na Biblioteca
  Inteligente (Fase 4b), restrita aos objetivos ativos do paciente. Mensagens são uma lista simples
  sem threading — suficiente para o MVP descrito no PRD, sem inventar um sistema de conversas
  aninhadas que a Seção 29.6 não pede.
- **White-label**: o logo (URL) só é exibido no Portal da Família — renderizado como `<img>` no
  navegador do responsável, nunca buscado pelo backend. Optamos por não embutir a imagem no PDF de
  Reports exportado justamente para não abrir uma rota de SSRF (o servidor baixando uma URL arbitrária
  fornecida pelo cliente); nome exibido e cor de destaque, por serem só texto/cor, aplicam-se
  normalmente também no PDF. O rodapé "Powered by Behavior Hub" nunca é removido, mesmo com
  white-label ativo, conforme a própria Seção 32.9 pede. O toggle de habilitação nunca confia apenas
  no rótulo do plano salvo (`subscription_plan == ENTERPRISE`): também exige
  `subscription_status` ativo/trialing, então uma clínica que atrasar ou cancelar o Enterprise perde
  o white-label imediatamente, mas os campos salvos continuam no banco para reativar sem
  reconfigurar tudo se ela voltar ao plano.
- **Faturamento por Sessão**: é um registro de controle interno da própria clínica — não integra com
  nenhum gateway de pagamento real (nem o Stripe da assinatura SaaS, que é um produto totalmente
  separado). O campo `due_date` é só informativo; o status "Em atraso" nunca é calculado
  automaticamente a partir da data de vencimento — é sempre uma ação explícita de quem gerencia o
  faturamento, já que o PRD não pede (nem faria sentido inventar) uma regra automática de quando
  algo conta como atrasado. Só administrador de clínica ou conta individual podem lançar/editar
  cobranças ou exportar o CSV (mesma restrição já usada para gestão de assinatura/Stripe em
  `billing_service.py`); qualquer usuário autenticado pode *ver* se uma sessão já tem cobrança
  (não é dado sensível por si só), mas a tentativa de criar uma nova sem o plano correto retorna 403
  — por isso a tela de cobrança aparece sempre, e só o clique em salvar revela a exigência de
  plano Premium/Enterprise.
- **Lista de Espera**: sem campos de convênio/plano de saúde ou fila com posição numérica — a Seção
  32.11 pede só "campos mínimos" e conversão sem redigitação, e o produto ainda não tem nenhum
  conceito de convênio/plano de saúde no modelo de dados (o mesmo tipo de lacuna já documentado para
  Faturamento por Sessão e o Dashboard do Gestor); adicionar esses campos agora seria inventar um
  requisito que a Seção 32.11 não pede. A mesma permissão configurável de "Cadastrar paciente" (Seção
  17.1) controla quem pode usar a lista de espera — não criamos uma permissão nova, já que triagem e
  admissão formal são, na prática, a mesma decisão de negócio sobre quem pode trazer um novo paciente
  para o sistema.
- **Anotação por Voz**: usa a Web Speech API nativa do navegador (transcrição "local", no sentido de
  que o Behavior Hub não processa nem armazena áudio algum — o próprio navegador decide como
  transcrever), em vez de uma API de terceiros paga — a Seção 32.12 já cita "transcrição local ou via
  API" como opções equivalentes, e a local evita depender de outra chave de provedor externo que
  você ainda não configurou (mesmo padrão já adotado para o resumo de Reports e as Sugestões
  Clínicas). Só funciona em navegadores com suporte a essa API (Chrome/Edge; não Firefox) — o botão
  de ditado simplesmente não aparece quando não suportado, sem quebrar o restante do formulário.
  Aplicado apenas ao campo de observação da tentativa, que é literalmente o que a Seção 32.12 pede
  ("permitir ditar a observação da tentativa por voz"); outros campos de texto livre do produto
  (comentários de objetivo, observações de sessão) não foram alterados nesta rodada.
- **Biblioteca Inteligente**: a "recomendação automática" da Seção 29.7 é, nesta fase, um vínculo
  manual (tagueamento) com pontuação de relevância definida pelo profissional — o próprio PRD já
  antecipava isso ("não há dado histórico suficiente para a IA inferir a relação sozinha no
  lançamento"). Não há ranking por IA real nem sugestão automática de quais recursos vincular; isso
  fica para quando houver volume de dados suficiente (Seção 29.10, Machine Learning, visão de
  futuro) ou um provedor de IA definido.
- **Sugestões Clínicas (Fase 4b bloco 1)**: as "sugestões geradas por IA" da Seção 29.1 são, nesta
  fase, geradas por regra determinística — o mesmo motivo do resumo de Reports acima: você ainda não
  definiu um fornecedor de IA (Anthropic, OpenAI, etc.) nem a política de tratamento de dados
  associada (Seção 34 do PRD lista isso como uma decisão pendente do Product Owner). Em vez de
  inventar uma integração ou fabricar uma chave, a lógica de sugestão hoje reaproveita exatamente os
  mesmos limiares/série histórica dos Alertas Clínicos (Fase 4a) — quando você definir o provedor,
  trocamos apenas a camada de geração de texto, mantendo o mesmo modelo de dados e fluxo de
  aprovação/descarte. A sugestão de **troca de reforçador** (também citada na Seção 29.1) não foi
  implementada: o produto não tem nenhum conceito de "reforçador" ou "engajamento" no modelo de
  dados atual, então não há dado real para basear essa sugestão — implementá-la exigiria antes um
  novo módulo de registro de reforçadores, fora do escopo deste bloco.
- **Dashboard para Gestor**: não inclui indicadores de receita ou taxa de faturamento (Seção 29.5
  os pede). O Behavior Hub não tem — e nunca teve no escopo definido até aqui — um módulo de
  cobrança por paciente/sessão; a única integração de pagamento existente (Stripe) é a assinatura
  SaaS que a própria clínica paga ao Behavior Hub (Seção 8, já coberta na Fase 3 e visível na página
  Planos), não uma receita operacional da clínica. Calcular "receita" a partir de dados que o
  sistema não coleta seria inventar números — por isso o painel traz só os indicadores realmente
  derivados dos dados operacionais (pacientes, sessões, horas, ocupação) e deixa explícita a
  ausência dos financeiros, em vez de preenchê-los com um valor fictício.
- **Timeline Clínica**: a linha do tempo é montada a partir de fontes já existentes (atendimentos,
  avaliações, log de auditoria de objetivos/atribuições, resumos de relatório) em vez de um novo
  modelo dedicado de "evento" — evita duplicar armazenamento e manter tudo sincronizado. Intercorrências/
  notas livres (não implementadas, sem modelo de dados) ainda não aparecem na timeline; entram quando
  esse módulo existir.
- **Avaliações Padronizadas**: só os protocolos-piloto da Seção 30.1 (VB-MAPP e ABLLS-R) foram
  implementados; as ondas seguintes (AFLS, PEAK, ESDM, CARS, M-CHAT, Vineland, etc.) ficam para a
  Fase 5, conforme o próprio roadmap do PRD. Nenhum item/tarefa de avaliação em si (conteúdo
  proprietário dos manuais oficiais) foi reproduzido no sistema — apenas os nomes de domínio/área
  (terminologia padrão da análise do comportamento, já citada no próprio PRD) e, para o VB-MAPP, os
  170 pontos oficiais em 16 domínios amplamente documentados na literatura. O ABLLS-R não tem
  `max_value` padrão por domínio no sistema — o profissional que aplica o instrumento informa o
  máximo do seu manual ao registrar cada avaliação, evitando qualquer número inventado. O texto
  interpretativo da comparação entre avaliações (Seção 30.2) é um rascunho por regras, não um texto
  gerado por IA real, pela mesma razão das Sugestões Clínicas (fornecedor de IA ainda não definido).
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
