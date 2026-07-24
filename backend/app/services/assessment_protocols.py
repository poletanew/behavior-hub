"""Seção 30.1.1 — arquivo de configuração por protocolo (ProtocolDefinition):
mapeia domain_code -> domain_label e um max_value sugerido, sem alterar o
schema do banco (raw_scores continua sendo um JSON genérico).

Escopo deliberado: VB-MAPP e Socially Savvy Checklist são instrumentos
comerciais licenciados (Seção 30.3 — "protocolos com exigência de
licenciamento formal ficam marcados como 'requer licença' e não são
distribuídos pelo sistema, apenas referenciados para registro de
pontuação"). Por isso só reproduzimos aqui os NOMES dos domínios/áreas e a
CONTAGEM de itens por domínio — nunca os itens/tarefas de avaliação em si,
que pertencem ao manual oficial de cada instrumento.

Os `max_value` do VB-MAPP são os oficialmente publicados (16 áreas somando
170 pontos, conforme a Seção 30.1.1 do PRD) e servem apenas de valor sugerido
no formulário — o profissional aplicando o instrumento sempre pode ajustar,
já que a responsabilidade pela aplicação e pontuação é dele (Seção 30.3). Já
o Socially Savvy Checklist pontua cada item de 0 a 3 (mais opção "NA"); o
`max_value` de cada domínio aqui é apenas nº de itens × 3 (a pontuação
máxima possível), não o texto de nenhum item."""

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
    AssessmentProtocol.SOCIALLY_SAVVY: {
        "label": "Socially Savvy Checklist",
        "requires_license": True,
        "domains": [
            {"domain_code": "atencao_compartilhada", "domain_label": "Atenção Compartilhada", "max_value": 27},
            {"domain_code": "brincadeira_social", "domain_label": "Brincadeira Social", "max_value": 72},
            {"domain_code": "autorregulacao", "domain_label": "Autorregulação", "max_value": 54},
            {"domain_code": "social_emocional", "domain_label": "Social/Emocional", "max_value": 18},
            {"domain_code": "linguagem_social", "domain_label": "Linguagem Social", "max_value": 72},
            {
                "domain_code": "comportamento_grupo_sala_aula",
                "domain_label": "Comportamento de Grupo/Sala de Aula",
                "max_value": 69,
            },
            {
                "domain_code": "linguagem_social_nao_verbal",
                "domain_label": "Linguagem Social Não-Verbal",
                "max_value": 18,
            },
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
