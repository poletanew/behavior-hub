from app.models.user import User


def current_plan(user: User) -> str:
    """Seção 8.1 — plano vigente do tenant (clinica ou profissional individual).
    Fase 1 nao integra Stripe ainda; todo tenant novo comeca no plano Free
    (Seção 8.2), e a integracao completa entra na Fase 3 (Seção 31.1)."""
    if user.clinic_id is not None:
        return user.clinic.subscription_plan.value if user.clinic else "free"
    return user.subscription_plan.value if user.subscription_plan else "free"
