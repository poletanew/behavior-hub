# Behavior Hub

SaaS de gestão clínica multidisciplinar. Ver `docs/Behavior_Hub_PRD_v2_Completo.pdf` para o PRD
completo (fonte única de verdade do produto).

Este repositório está sendo construído **por fases**, seguindo o roadmap da Seção 31 do PRD.

- **Fase 1 — Core (MVP)**: autenticação, contas (clínica e individual), pacientes, atribuições,
  sessões/atendimentos com tentativas individualizadas e uma Training Library básica.
- **Fase 2 — Clínico (V1)**: Planos de Tratamento multidisciplinares, Reports com gráficos e resumo
  editável, Recursos Terapêuticos e Dados Excluídos (visão unificada com restauração).

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

### Rodando os testes automatizados do backend

```bash
docker compose exec backend pytest -q
```

(ou localmente, sem Docker — ver `backend/README.md`). 65 testes cobrem, entre outros:

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

## O que **não** está nesta fase

- **Resumo de IA real**: a Seção 14.5 do PRD pede um resumo gerado por IA. Combinamos com você
  adiar a integração com um provedor externo — o resumo hoje é um rascunho determinístico
  (baseado em regras, não em um modelo de linguagem), claramente rotulado como tal, com a mesma
  estrutura de edição/aprovação/versionamento que a IA real usará depois. Quando você definir o
  provedor (Anthropic, OpenAI, etc.) e me passar a chave, trocamos só essa peça.
- **Notificações, Templates de Sessão e Modo Offline/Tablet** (Seção 32.4/32.5/32.6): combinamos de
  deixar para uma iteração seguinte dentro da própria Fase 2, após validar o núcleo acima.
- Seguindo o roadmap (Seção 31.1 do PRD): RBAC completo, Stripe/planos pagos, Agenda/Scheduling e
  importação em lote de pacientes ficam para a **Fase 3**; Timeline clínica, heatmaps e alertas
  inteligentes para a **Fase 4**.

Consulte `backend/README.md` para observações sobre a curadoria da Training Library e o limite de
tamanho de arquivo dos Recursos Terapêuticos (Seção 34 — pendente de confirmação do PO).

## Estrutura do repositório

```
backend/    API FastAPI + SQLAlchemy + Alembic + testes (pytest)
frontend/   React + TypeScript + Tailwind
docs/       PRD (fonte única de verdade)
docker-compose.yml
```
