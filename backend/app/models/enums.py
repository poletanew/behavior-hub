import enum


class UserType(str, enum.Enum):
    CLINIC_ADMIN = "clinic_admin"
    PROFESSIONAL = "professional"
    INDIVIDUAL = "individual"
    SUPERVISOR = "supervisor"


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
