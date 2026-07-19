"""Seção 30.1.1 — arquivo de configuração por protocolo (ProtocolDefinition):
mapeia domain_code -> domain_label e um max_value sugerido, sem alterar o
schema do banco (raw_scores continua sendo um JSON genérico).

Escopo deliberado: VB-MAPP e ABLLS-R são instrumentos comerciais licenciados
(Seção 30.3 — "protocolos com exigência de licenciamento formal ficam
marcados como 'requer licença' e não são distribuídos pelo sistema, apenas
referenciados para registro de pontuação"). Por isso só reproduzimos aqui os
NOMES dos domínios/áreas — terminologia padrão da análise do comportamento já
citada no próprio PRD (ex.: "mando", "tato") — nunca os itens/tarefas de
avaliação em si, que pertencem ao manual oficial de cada instrumento.

Os `max_value` do VB-MAPP são os oficialmente publicados (16 áreas somando
170 pontos, conforme a Seção 30.1.1 do PRD) e servem apenas de valor sugerido
no formulário — o profissional aplicando o instrumento sempre pode ajustar,
já que a responsabilidade pela aplicação e pontuação é dele (Seção 30.3). Já
o ABLLS-R não tem um "max_value" padrão por domínio aqui: o número de tarefas
por área varia por edição/adaptação do instrumento, e preencher um valor sem
certeza equivaleria a inventar dado — o profissional informa o max_value real
do seu manual ao registrar cada aplicação."""

from app.models.enums import AssessmentProtocol

PROTOCOL_DEFINITIONS: dict[AssessmentProtocol, dict] = {
    AssessmentProtocol.VB_MAPP: {
        "label": "VB-MAPP",
        "requires_license": True,
        "domains": [
            {"domain_code": "mando", "domain_label": "Mando", "max_value": 15},
            {"domain_code": "tato", "domain_label": "Tato", "max_value": 15},
            {"domain_code": "ecoico", "domain_label": "Ecoico", "max_value": 10},
            {"domain_code": "intraverbal", "domain_label": "Intraverbal", "max_value": 15},
            {"domain_code": "vocalizacao_espontanea", "domain_label": "Vocalização Espontânea", "max_value": 5},
            {"domain_code": "ouvinte", "domain_label": "Ouvinte (Listener Responding)", "max_value": 15},
            {
                "domain_code": "ouvinte_ffc",
                "domain_label": "Ouvinte por Função/Característica/Classe (LRFFC)",
                "max_value": 10,
            },
            {
                "domain_code": "percepcao_visual_mts",
                "domain_label": "Percepção Visual e Pareamento (VP-MTS)",
                "max_value": 10,
            },
            {"domain_code": "imitacao_motora", "domain_label": "Imitação Motora", "max_value": 5},
            {"domain_code": "brincar_independente", "domain_label": "Brincar Independente", "max_value": 10},
            {
                "domain_code": "comportamento_social",
                "domain_label": "Comportamento Social e Brincar Social",
                "max_value": 10,
            },
            {"domain_code": "estrutura_linguistica", "domain_label": "Estrutura Linguística", "max_value": 10},
            {
                "domain_code": "rotinas_grupo",
                "domain_label": "Rotinas de Sala de Aula e Habilidades em Grupo",
                "max_value": 10,
            },
            {"domain_code": "matematica", "domain_label": "Matemática", "max_value": 10},
            {"domain_code": "leitura", "domain_label": "Leitura", "max_value": 10},
            {"domain_code": "escrita", "domain_label": "Escrita", "max_value": 10},
        ],
    },
    AssessmentProtocol.ABLLS_R: {
        "label": "ABLLS-R",
        "requires_license": True,
        "domains": [
            {"domain_code": "a", "domain_label": "Cooperação e Eficácia do Reforçador", "max_value": None},
            {"domain_code": "b", "domain_label": "Desempenho Visual", "max_value": None},
            {"domain_code": "c", "domain_label": "Linguagem Receptiva", "max_value": None},
            {"domain_code": "d", "domain_label": "Imitação Motora", "max_value": None},
            {"domain_code": "e", "domain_label": "Imitação Vocal", "max_value": None},
            {"domain_code": "f", "domain_label": "Pedidos (Mando)", "max_value": None},
            {"domain_code": "g", "domain_label": "Nomeação (Tato)", "max_value": None},
            {"domain_code": "h", "domain_label": "Intraverbal", "max_value": None},
            {"domain_code": "i", "domain_label": "Vocalização Espontânea", "max_value": None},
            {"domain_code": "j", "domain_label": "Sintaxe e Gramática", "max_value": None},
            {"domain_code": "k", "domain_label": "Brincar e Lazer", "max_value": None},
            {"domain_code": "l", "domain_label": "Interação Social", "max_value": None},
            {"domain_code": "m", "domain_label": "Instrução em Grupo", "max_value": None},
            {"domain_code": "n", "domain_label": "Rotinas de Sala de Aula", "max_value": None},
            {"domain_code": "o", "domain_label": "Generalização de Respostas", "max_value": None},
            {"domain_code": "p", "domain_label": "Leitura", "max_value": None},
            {"domain_code": "q", "domain_label": "Matemática", "max_value": None},
            {"domain_code": "r", "domain_label": "Escrita", "max_value": None},
            {"domain_code": "s", "domain_label": "Soletração", "max_value": None},
            {"domain_code": "t", "domain_label": "Vestir-se", "max_value": None},
            {"domain_code": "u", "domain_label": "Alimentação", "max_value": None},
            {"domain_code": "v", "domain_label": "Higiene Pessoal", "max_value": None},
            {"domain_code": "w", "domain_label": "Uso do Banheiro", "max_value": None},
            {"domain_code": "x", "domain_label": "Motricidade Grossa", "max_value": None},
            {"domain_code": "y", "domain_label": "Motricidade Fina", "max_value": None},
        ],
    },
}


def list_protocol_definitions() -> list[dict]:
    return [
        {"protocol": protocol.value, "label": definition["label"], "requires_license": definition["requires_license"], "domains": definition["domains"]}
        for protocol, definition in PROTOCOL_DEFINITIONS.items()
    ]


def get_protocol_definition(protocol: AssessmentProtocol) -> dict:
    return PROTOCOL_DEFINITIONS[protocol]
