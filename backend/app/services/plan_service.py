from app.models.user import User


def current_plan(user: User) -> str:
    """Seção 8.1 — plano vigente do tenant (clinica ou profissional individual).

    Seção 8.3 — "nunca confiar apenas no frontend para liberar funcionalidades":
    o rótulo subscription_plan só concede os direitos do plano pago enquanto a
    assinatura Stripe subjacente estiver em um status que efetivamente paga
    (active/trialing). Uma assinatura cancelada, em atraso ou nunca integrada
    ao Stripe (subscription_status="none", o caso de todo tenant Free) sempre
    cai de volta para "free", mesmo que subscription_plan ainda esteja
    com o rótulo antigo (ex.: logo após um cancelamento, antes do próximo
    evento de webhook confirmar o downgrade)."""
    tenant = user.clinic if user.clinic_id is not None else user
    if tenant is None:
        return "free"
    if tenant.subscription_plan is None or tenant.subscription_plan.value == "free":
        return "free"
    return tenant.subscription_plan.value if tenant.has_paid_access else "free"
