"""seed training library starter data

Seção 12.1 do PRD: a Training Library deve oferecer um conjunto amplo de treinos
por categoria, clinicamente revisados antes de producao. Este seed entrega um
conjunto inicial ("starter set") de treinos de sistema para permitir o uso
imediato da coleta de dados na Fase 1 (MVP). A curadoria completa (~20 + 15
treinos por categoria, com revisao clinica formal) fica registrada como
trabalho pendente antes do lancamento em producao — ver README do backend.

Revision ID: 94f27f468fdb
Revises: ea268507959b
Create Date: 2026-07-18 03:15:45.566457

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94f27f468fdb'
down_revision: Union[str, None] = 'ea268507959b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    ("Comunicação", "Habilidades de comunicação funcional, verbal e alternativa."),
    ("Social", "Interação social, brincadeira compartilhada e habilidades de convivência."),
    ("Autonomia", "Atividades de vida diária, rotina e tomada de decisão independente."),
    ("Cognição", "Habilidades cognitivas, acadêmicas e de discriminação."),
    ("Motor", "Coordenação motora fina e grossa."),
    ("Autorregulação", "Tolerância à espera, frustração e regulação comportamental."),
]

TRAININGS = {
    "Comunicação": [
        ("Mando por item preferido", "Solicitar espontaneamente um item de interesse.",
         "Item preferido visível fora de alcance.", "Verbaliza ou sinaliza o pedido pelo nome do item.",
         "independente > gestual > verbal > modelação", "80% independente em 3 sessões consecutivas."),
        ("Mando por ajuda", "Solicitar ajuda quando necessário.",
         "Apresentar tarefa com item de dificil acesso/abertura.", "Solicita ajuda verbal ou gestualmente.",
         "independente > gestual > verbal", "80% em 3 sessões consecutivas."),
        ("Tato de objetos comuns", "Nomear objetos do cotidiano ao serem apresentados.",
         "Apresentar objeto e perguntar \"o que é isso?\".", "Nomeia corretamente o objeto.",
         "independente > verbal > modelação", "80% de acerto em 20 tentativas."),
        ("Resposta a saudações", "Responder a cumprimentos sociais básicos.",
         "Instrutor diz \"oi\" ou \"tchau\".", "Responde com saudação equivalente.",
         "independente > gestual > modelação", "8 em 10 tentativas consecutivas."),
        ("Comunicação funcional de recusa", "Recusar um item ou atividade de forma apropriada.",
         "Oferecer item não preferido.", "Sinaliza \"não\" verbalmente ou com gesto combinado.",
         "independente > gestual > física parcial", "80% em 3 sessões."),
        ("Nomeação de pessoas familiares", "Identificar e nomear pessoas próximas.",
         "Apresentar foto ou pessoa presente.", "Nomeia corretamente.",
         "independente > verbal", "90% de acerto em 20 tentativas."),
        ("Intraverbal de perguntas pessoais", "Responder perguntas sobre si mesmo.",
         "Perguntar nome, idade ou preferências.", "Responde de forma consistente.",
         "independente > verbal > modelação", "80% em 3 sessões."),
        ("Uso de figuras/PECS para pedido", "Utilizar sistema de comunicação por figuras para solicitar itens.",
         "Apresentar prancha de comunicação.", "Entrega ou aponta a figura correta.",
         "física total > física parcial > gestual > independente", "80% de iniciativa em 3 sessões."),
    ],
    "Social": [
        ("Contato visual em interação", "Estabelecer contato visual ao ser chamado pelo nome.",
         "Chamar o nome da criança.", "Direciona o olhar para o interlocutor em até 3 segundos.",
         "física parcial > gestual > independente", "80% em 20 tentativas."),
        ("Brincadeira paralela", "Brincar próximo a outra criança com o mesmo material.",
         "Disponibilizar material duplicado.", "Permanece brincando próximo por período combinado.",
         "modelação > gestual > independente", "Critério combinado com a equipe."),
        ("Espera da vez em jogo", "Aguardar a vez em jogo estruturado com outra pessoa.",
         "Jogo de turnos com sinalização visual.", "Aguarda sem interromper o turno do outro.",
         "física parcial > gestual > independente", "80% em 3 sessões consecutivas."),
        ("Imitação motora com pares", "Imitar ação motora simples demonstrada por outra criança.",
         "Par demonstra ação simples.", "Reproduz a ação em até 5 segundos.",
         "modelação > gestual > independente", "8 em 10 tentativas."),
        ("Compartilhar objeto a pedido", "Compartilhar um item quando solicitado por outra pessoa.",
         "Outra pessoa solicita o item.", "Entrega o item dentro de 10 segundos.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Iniciar brincadeira com colega", "Convidar um colega para uma atividade.",
         "Ambiente com colega disponível.", "Verbaliza ou gesticula convite reconhecível.",
         "modelação > gestual > independente", "Critério combinado com a equipe."),
        ("Reconhecer emoções básicas", "Identificar emoções em fotos ou expressões.",
         "Apresentar foto de expressão facial.", "Nomeia a emoção corretamente.",
         "independente > verbal > modelação", "80% em 20 tentativas."),
        ("Seguir regra de jogo em grupo", "Seguir regras simples em atividade em grupo.",
         "Jogo em grupo com regra explicada.", "Cumpre a regra combinada.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
    ],
    "Autonomia": [
        ("Lavar as mãos", "Realizar a sequência de lavar as mãos de forma independente.",
         "Apresentar pia com sabão e toalha.", "Completa a sequência sem apoio físico.",
         "física total > física parcial > gestual > independente", "80% da sequência em 3 sessões."),
        ("Vestir peça de roupa simples", "Vestir uma peça de roupa (ex.: camiseta) de forma independente.",
         "Apresentar a peça de roupa.", "Veste corretamente em até 2 minutos.",
         "física total > física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Guardar pertences após uso", "Guardar objetos/materiais no local apropriado após o uso.",
         "Finalizar atividade com materiais espalhados.", "Guarda os itens no local combinado.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Servir-se de água", "Servir a própria água de forma segura.",
         "Disponibilizar jarra leve e copo.", "Serve sem derramar excessivamente.",
         "física parcial > gestual > independente", "8 em 10 tentativas."),
        ("Escovar os dentes", "Realizar escovação dentária com sequência básica.",
         "Apresentar escova e pasta.", "Completa a sequência com apoio mínimo.",
         "física total > física parcial > gestual > independente", "Critério combinado com a equipe/família."),
        ("Seguir rotina visual", "Seguir os passos de uma rotina apresentada em quadro visual.",
         "Quadro de rotina com etapas ilustradas.", "Executa os passos na ordem indicada.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Tomada de decisão entre duas opções", "Escolher entre duas opções apresentadas.",
         "Apresentar duas opções concretas.", "Aponta ou verbaliza a escolha.",
         "independente > gestual > modelação", "8 em 10 tentativas."),
        ("Organizar mochila escolar", "Organizar itens da mochila conforme lista/rotina.",
         "Apresentar mochila e itens necessários.", "Organiza os itens corretamente.",
         "física parcial > gestual > independente", "Critério combinado com a equipe/família."),
    ],
    "Cognição": [
        ("Pareamento idêntico", "Parear objetos ou figuras idênticas.",
         "Apresentar conjunto de itens e amostra.", "Pareia corretamente o item idêntico.",
         "física parcial > gestual > independente", "90% em 20 tentativas."),
        ("Categorização simples", "Agrupar itens pela categoria (ex.: frutas, animais).",
         "Apresentar itens de duas ou mais categorias.", "Agrupa corretamente pela categoria.",
         "gestual > verbal > independente", "80% em 20 tentativas."),
        ("Contagem de objetos", "Contar uma quantidade de objetos até um número alvo.",
         "Apresentar conjunto de objetos.", "Conta corretamente em voz alta ou aponta.",
         "modelação > verbal > independente", "80% em 20 tentativas."),
        ("Reconhecimento de cores", "Identificar cores básicas quando nomeadas.",
         "Apresentar cartões de cores.", "Aponta a cor correta quando solicitado.",
         "gestual > verbal > independente", "90% em 20 tentativas."),
        ("Sequência lógica de 3 passos", "Ordenar uma sequência de 3 figuras em ordem lógica.",
         "Apresentar figuras embaralhadas.", "Ordena corretamente a sequência.",
         "modelação > gestual > independente", "80% em 3 sessões."),
        ("Discriminação condicional simples", "Selecionar item correto conforme instrução com dois atributos.",
         "Instrução com dois critérios (ex.: \"o carro vermelho\").", "Seleciona o item que atende aos dois critérios.",
         "gestual > verbal > independente", "80% em 20 tentativas."),
        ("Reconhecimento de letras do nome", "Identificar as letras que compõem o próprio nome.",
         "Apresentar cartões de letras.", "Aponta corretamente as letras do nome.",
         "gestual > verbal > independente", "Critério combinado com a equipe."),
        ("Resolução de quebra-cabeça simples", "Montar quebra-cabeça de poucas peças.",
         "Apresentar quebra-cabeça adequado à idade.", "Monta com apoio mínimo dentro do tempo combinado.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
    ],
    "Motor": [
        ("Preensão em pinça", "Realizar preensão em pinça com objetos pequenos.",
         "Apresentar objetos pequenos (ex.: contas).", "Realiza a preensão corretamente.",
         "física total > física parcial > gestual > independente", "80% em 20 tentativas."),
        ("Recorte com tesoura", "Recortar linha reta com tesoura sem ponta.",
         "Apresentar papel com linha marcada.", "Recorta seguindo a linha com desvio mínimo.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Equilíbrio em um pé", "Manter-se em equilíbrio sobre um pé por tempo determinado.",
         "Instrução verbal para equilibrar-se.", "Mantém a postura pelo tempo alvo.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Chutar bola em direção alvo", "Chutar a bola em direção a um alvo determinado.",
         "Posicionar bola e alvo visível.", "Acerta o alvo dentro da distância combinada.",
         "modelação > gestual > independente", "6 em 10 tentativas."),
        ("Traçado de linhas e formas", "Traçar linhas retas e curvas com lápis.",
         "Apresentar folha com modelo pontilhado.", "Traça seguindo o modelo com desvio mínimo.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Empilhar blocos", "Empilhar blocos formando uma torre estável.",
         "Disponibilizar blocos de encaixe.", "Empilha o número de blocos combinado sem derrubar.",
         "física parcial > gestual > independente", "8 em 10 tentativas."),
        ("Rosquear e desenroscar tampa", "Manipular tampas de rosca em potes/garrafas.",
         "Apresentar pote com tampa de rosca.", "Realiza a ação com coordenação bimanual.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Pular com os dois pés", "Realizar salto com os dois pés simultaneamente.",
         "Instrução verbal ou demonstração.", "Executa o salto despregando os dois pés do chão.",
         "modelação > gestual > independente", "6 em 10 tentativas."),
    ],
    "Autorregulação": [
        ("Aguardar por 30 segundos", "Aguardar um curto período antes de acessar reforçador.",
         "Sinalizar visualmente o tempo de espera.", "Aguarda sem comportamento disruptivo.",
         "física parcial > gestual > independente", "80% em 3 sessões consecutivas (exemplo Seção 33.2 do PRD)."),
        ("Pedido de pausa", "Solicitar uma pausa quando sobrecarregado.",
         "Apresentar cartão de pausa disponível.", "Solicita a pausa antes de comportamento disruptivo.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Transição entre atividades", "Realizar transição de uma atividade para outra com aviso prévio.",
         "Avisar com antecedência e sinal visual.", "Transiciona sem comportamento disruptivo.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Identificação do próprio estado emocional", "Reconhecer e nomear o próprio estado emocional.",
         "Perguntar \"como você está?\" em momento neutro.", "Nomeia ou aponta a emoção correspondente.",
         "gestual > verbal > independente", "Critério combinado com a equipe."),
        ("Uso de estratégia de autorregulação", "Utilizar estratégia combinada (ex.: respiração) diante de frustração.",
         "Apresentar situação de frustração controlada.", "Utiliza a estratégia ensinada dentro de 30 segundos.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Tolerância a mudança de rotina", "Tolerar pequena alteração na rotina esperada.",
         "Introduzir mudança combinada previamente.", "Aceita a mudança sem comportamento disruptivo.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
        ("Aceitar \"não\" como resposta", "Tolerar a negativa a um pedido sem comportamento disruptivo.",
         "Negar pedido de forma neutra.", "Aceita a negativa dentro de 30 segundos.",
         "física parcial > gestual > independente", "80% em 3 sessões."),
        ("Redirecionamento após frustração", "Aceitar redirecionamento para outra atividade após frustração.",
         "Oferecer alternativa após evento frustrante.", "Engaja na atividade alternativa em até 1 minuto.",
         "física parcial > gestual > independente", "Critério combinado com a equipe."),
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    category_ids: dict[str, str] = {}
    for name, description in CATEGORIES:
        category_id = str(uuid.uuid4())
        category_ids[name] = category_id
        conn.execute(
            sa.text(
                "INSERT INTO training_categories (id, name, description, created_at, updated_at) "
                "VALUES (:id, :name, :description, now(), now())"
            ),
            {"id": category_id, "name": name, "description": description},
        )

    for category_name, trainings in TRAININGS.items():
        category_id = category_ids[category_name]
        for title, objective, instruction, expected, hierarchy, mastery in trainings:
            conn.execute(
                sa.text(
                    "INSERT INTO trainings "
                    "(id, category_id, title, objective, discriminative_instruction, expected_response, "
                    "prompt_hierarchy, mastery_criteria, visibility, created_at, updated_at) "
                    "VALUES (:id, :category_id, :title, :objective, :instruction, :expected, "
                    ":hierarchy, :mastery, 'SYSTEM', now(), now())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "category_id": category_id,
                    "title": title,
                    "objective": objective,
                    "instruction": instruction,
                    "expected": expected,
                    "hierarchy": hierarchy,
                    "mastery": mastery,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM trainings WHERE visibility = 'SYSTEM'"))
    conn.execute(sa.text("DELETE FROM training_categories"))
