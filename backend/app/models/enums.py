import enum


class UserType(str, enum.Enum):
    CLINIC_ADMIN = "clinic_admin"
    PROFESSIONAL = "professional"
    INDIVIDUAL = "individual"
    SUPERVISOR = "supervisor"
    FAMILY = "family"
    # Addendum v2.1, RF-11 — Auxiliar Terapêutico: aplica treinos prescritos
    # (RF-10) em pacientes atribuídos, sob supervisão; sem acesso a
    # diagnóstico completo, plano de tratamento ou relatórios.
    AT = "at"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Specialty(str, enum.Enum):
    PSICOLOGO_INFANTIL = "psicologo_infantil"
    ANALISTA_COMPORTAMENTO_ABA = "analista_comportamento_aba"
    FONOAUDIOLOGO = "fonoaudiologo"
    TERAPEUTA_OCUPACIONAL = "terapeuta_ocupacional"
    PSICOPEDAGOGO = "psicopedagogo"
    FISIOTERAPEUTA_PEDIATRICO = "fisioterapeuta_pediatrico"
    NEUROPEDIATRA = "neuropediatra"
    PSIQUIATRA_INFANTIL = "psiquiatra_infantil"
    NUTRICIONISTA_INFANTIL = "nutricionista_infantil"
    MUSICOTERAPEUTA = "musicoterapeuta"
    ARTETERAPEUTA = "arteterapeuta"
    PSICOMOTRICISTA = "psicomotricista"


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Seção 8.3 — espelha os status de assinatura do Stripe; usado para nunca
    confiar apenas no rótulo do plano ao liberar funcionalidades (ex.: uma
    assinatura em atraso/cancelada não deve manter os direitos do plano pago)."""

    NONE = "none"
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class PatientStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AssignmentPermission(str, enum.Enum):
    READ_ONLY = "read_only"
    EDIT_SESSIONS = "edit_sessions"
    EDIT_AREA_PLAN = "edit_area_plan"
    FULL_ACCESS = "full_access"


class TrialResult(str, enum.Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    NO_RESPONSE = "no_response"


class PromptLevel(str, enum.Enum):
    INDEPENDENT = "independent"
    GESTURAL = "gestural"
    VERBAL = "verbal"
    MODELING = "modeling"
    PARTIAL_PHYSICAL = "partial_physical"
    FULL_PHYSICAL = "full_physical"


class TrainingVisibility(str, enum.Enum):
    SYSTEM = "system"
    CLINIC_SHARED = "clinic_shared"
    PRIVATE = "private"


class TreatmentArea(str, enum.Enum):
    """Seção 13.1 — áreas da grade multidisciplinar do plano de tratamento."""

    PSICOLOGIA = "psicologia"
    ABA = "aba"
    FONOAUDIOLOGIA = "fonoaudiologia"
    TERAPIA_OCUPACIONAL = "terapia_ocupacional"
    PSICOPEDAGOGIA = "psicopedagogia"
    FISIOTERAPIA = "fisioterapia"
    NUTRICAO = "nutricao"
    OUTRA = "outra"


# Seção 13.3 — mapeamento entre especialidade do profissional e a área do plano
# de tratamento que ele pode editar quando o vínculo é EDIT_AREA_PLAN.
SPECIALTY_TO_AREA: dict[Specialty, TreatmentArea] = {
    Specialty.PSICOLOGO_INFANTIL: TreatmentArea.PSICOLOGIA,
    Specialty.ANALISTA_COMPORTAMENTO_ABA: TreatmentArea.ABA,
    Specialty.FONOAUDIOLOGO: TreatmentArea.FONOAUDIOLOGIA,
    Specialty.TERAPEUTA_OCUPACIONAL: TreatmentArea.TERAPIA_OCUPACIONAL,
    Specialty.PSICOPEDAGOGO: TreatmentArea.PSICOPEDAGOGIA,
    Specialty.FISIOTERAPEUTA_PEDIATRICO: TreatmentArea.FISIOTERAPIA,
    Specialty.NUTRICIONISTA_INFANTIL: TreatmentArea.NUTRICAO,
}


class ObjectiveStatus(str, enum.Enum):
    """Seção 13.1 — status: não iniciado, em andamento, dominado, pausado, descontinuado."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    MASTERED = "mastered"
    PAUSED = "paused"
    DISCONTINUED = "discontinued"


class ObjectivePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResourceType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"


class ResourceVisibility(str, enum.Enum):
    PRIVATE = "private"
    CLINIC_SHARED = "clinic_shared"


class ReportSummaryStatus(str, enum.Enum):
    """Seção 14.5 — o terapeuta pode editar, aprovar ou descartar o texto."""

    DRAFT = "draft"
    APPROVED = "approved"
    DISCARDED = "discarded"


class AppointmentStatus(str, enum.Enum):
    """Seção 32.2 — diferencia sessão agendada de sessão registrada."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class CancellationReason(str, enum.Enum):
    """Seção 32.3 — motivo de cancelamento/falta."""

    PATIENT = "patient"
    CLINIC = "clinic"
    PROFESSIONAL = "professional"
    FORCE_MAJEURE = "force_majeure"


class ClinicalAlertType(str, enum.Enum):
    """Seção 29.1/29.9 — as quatro regras computáveis obrigatórias antes do
    desenvolvimento (AC-15/AC-16)."""

    NO_COLLECTION = "no_collection"
    REGRESSION = "regression"
    STAGNATION = "stagnation"
    FADING_CANDIDATE = "fading_candidate"


class SuggestionType(str, enum.Enum):
    """Seção 29.1 (Fase 4b) — sugestões geradas por regra (não por um modelo de
    IA real ainda — ver nota de escopo em clinical_suggestion_service.py)."""

    NEW_PROGRAM = "new_program"
    FADING = "fading"
    MASTERY_READY = "mastery_ready"


class SuggestionStatus(str, enum.Enum):
    """Seção 29.1 — toda sugestão é uma recomendação editável: o profissional
    aprova ou descarta, nunca é aplicada automaticamente."""

    PENDING = "pending"
    APPROVED = "approved"
    DISMISSED = "dismissed"


class AssessmentProtocol(str, enum.Enum):
    """Seção 30.1 — protocolos-piloto (V3): VB-MAPP e ABLLS-R. Demais
    protocolos (AFLS, PEAK, ESDM, etc.) entram em ondas futuras."""

    VB_MAPP = "vb_mapp"
    ABLLS_R = "ablls_r"


class WaitlistStatus(str, enum.Enum):
    """Seção 32.11 — Lista de Espera: cadastro simplificado antes da admissão
    formal. "Convertido" cria o paciente completo sem redigitação."""

    WAITING = "waiting"
    CONVERTED = "converted"
    DISCARDED = "discarded"


class SchoolShift(str, enum.Enum):
    """Addendum v2.1, RF-03 — turno escolar do paciente, campo opcional."""

    MANHA = "manha"
    TARDE = "tarde"
    INTEGRAL = "integral"
    NAO_FREQUENTA = "nao_frequenta"


class TrainingLinkStatus(str, enum.Enum):
    """Addendum v2.1, RF-10 — vínculo treino↔paciente ("treino prescrito").
    Passa de PRESCRIBED para APPLIED automaticamente na primeira sessão que
    de fato usar esse treino com esse paciente."""

    PRESCRIBED = "prescribed"
    APPLIED = "applied"


class BehaviorIntensity(str, enum.Enum):
    """Addendum v3.0, RF-18 — intensidade do comportamento-alvo registrado no
    modelo ABC, mesmo vocabulário já usado em outras escalas do sistema."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class SessionMediaType(str, enum.Enum):
    """Addendum v3.0, RF-20 — o antigo campo único "Foto" da Seção 11.2 vira
    "Foto/Vídeo"; este enum identifica qual dos dois foi anexado."""

    PHOTO = "photo"
    VIDEO = "video"


class ChecklistAnswerType(str, enum.Enum):
    """Addendum v3.0, RF-22 — tipo de resposta de uma pergunta de checklist
    personalizado: sim/não, escala (1-5) ou texto curto."""

    YES_NO = "yes_no"
    SCALE = "scale"
    SHORT_TEXT = "short_text"


class GeneralizationContext(str, enum.Enum):
    """Addendum v3.0, RF-24 — onde a generalização de um alvo dominado já foi
    testada (Seção 13.1: manutenção/generalização)."""

    CLINICA = "clinica"
    CASA = "casa"
    ESCOLA = "escola"
    OUTRO = "outro"


class ApplierType(str, enum.Enum):
    """Addendum v3.0, RF-25 — quem aplica um objetivo: o próprio profissional
    (padrão) ou um pai/cuidador marcado explicitamente como aplicador."""

    PROFESSIONAL = "professional"
    PARENT = "parent"
