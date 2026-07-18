import datetime

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.clinic import Clinic
from app.models.enums import SubscriptionPlan, SubscriptionStatus, UserType
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.models.user import User
from app.services import audit_service

settings = get_settings()

UPGRADABLE_PLANS = (SubscriptionPlan.BASIC, SubscriptionPlan.PREMIUM, SubscriptionPlan.ENTERPRISE)
VALID_SUBSCRIPTION_STATUSES = {s.value for s in SubscriptionStatus}


def _price_id_for_plan(plan: SubscriptionPlan) -> str | None:
    return {
        SubscriptionPlan.BASIC: settings.STRIPE_PRICE_ID_BASIC,
        SubscriptionPlan.PREMIUM: settings.STRIPE_PRICE_ID_PREMIUM,
        SubscriptionPlan.ENTERPRISE: settings.STRIPE_PRICE_ID_ENTERPRISE,
    }.get(plan)


def _plan_for_price_id(price_id: str) -> SubscriptionPlan | None:
    mapping = {
        settings.STRIPE_PRICE_ID_BASIC: SubscriptionPlan.BASIC,
        settings.STRIPE_PRICE_ID_PREMIUM: SubscriptionPlan.PREMIUM,
        settings.STRIPE_PRICE_ID_ENTERPRISE: SubscriptionPlan.ENTERPRISE,
    }
    mapping.pop(None, None)
    return mapping.get(price_id)


def _ensure_configured() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this server yet. Set STRIPE_SECRET_KEY to enable billing.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _ensure_billing_owner(user: User) -> None:
    """Seção 8 — quem gerencia planos/assinatura é o dono do tenant (admin de
    clínica ou profissional individual), não profissionais/supervisores."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage billing")


def get_tenant(db: Session, user: User) -> Clinic | User:
    if user.clinic_id is not None:
        clinic = db.get(Clinic, user.clinic_id)
        if clinic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
        return clinic
    return user


def _find_tenant_by_customer_id(db: Session, customer_id: str) -> Clinic | User | None:
    clinic = db.query(Clinic).filter(Clinic.stripe_customer_id == customer_id).first()
    if clinic is not None:
        return clinic
    return db.query(User).filter(User.stripe_customer_id == customer_id, User.clinic_id.is_(None)).first()


def _ensure_customer(db: Session, user: User) -> Clinic | User:
    tenant = get_tenant(db, user)
    if tenant.stripe_customer_id:
        return tenant

    customer = stripe.Customer.create(
        email=user.email,
        name=tenant.name,
        metadata={"tenant_type": "clinic" if isinstance(tenant, Clinic) else "individual", "tenant_id": str(tenant.id)},
    )
    tenant.stripe_customer_id = customer.id
    db.commit()
    db.refresh(tenant)
    return tenant


def get_subscription_status(db: Session, user: User) -> dict:
    tenant = get_tenant(db, user)
    return {
        "subscription_plan": tenant.subscription_plan,
        "subscription_status": tenant.subscription_status,
        "subscription_current_period_end": tenant.subscription_current_period_end,
        "has_paid_access": tenant.has_paid_access,
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
    }


def create_checkout_session(db: Session, user: User, plan: SubscriptionPlan) -> dict:
    """Seção 8.3 — cria uma Stripe Checkout Session para upgrade/downgrade de plano."""
    _ensure_billing_owner(user)
    _ensure_configured()

    if plan not in UPGRADABLE_PLANS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan for checkout")

    price_id = _price_id_for_plan(plan)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No Stripe Price ID configured for plan '{plan.value}'.",
        )

    tenant = _ensure_customer(db, user)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=tenant.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/plans?checkout=success",
        cancel_url=f"{settings.FRONTEND_URL}/plans?checkout=cancel",
        metadata={"tenant_type": "clinic" if isinstance(tenant, Clinic) else "individual", "tenant_id": str(tenant.id)},
    )
    return {"checkout_url": session.url}


def create_billing_portal_session(db: Session, user: User) -> dict:
    """Seção 26 — botão "Gerenciar assinatura" abre o Portal do Cliente Stripe."""
    _ensure_billing_owner(user)
    _ensure_configured()

    tenant = get_tenant(db, user)
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No billing account yet — subscribe to a plan first")

    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/plans",
    )
    return {"portal_url": session.url}


def verify_and_parse_event(payload: bytes, signature_header: str | None) -> dict:
    """Seção 28.4 — todo webhook deve validar assinatura antes de qualquer processamento."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe webhook secret not configured")
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(payload, signature_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload or signature") from exc
    return event


def record_event_or_skip(db: Session, event: dict) -> bool:
    """Seção 28.4 — chave de deduplicação por evento. Retorna False (e não
    processa nada) se o evento já foi registrado antes — reentregas do Stripe
    para o mesmo evento nunca reaplicam o efeito duas vezes."""
    existing = db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == event["id"]).first()
    if existing is not None:
        return False
    db.add(StripeWebhookEvent(stripe_event_id=event["id"], event_type=event["type"]))
    db.commit()
    return True


def _apply_subscription_state(db: Session, tenant: Clinic | User, subscription: dict) -> None:
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan = _plan_for_price_id(price_id)
    if plan is not None:
        tenant.subscription_plan = plan

    raw_status = subscription.get("status")
    if raw_status in VALID_SUBSCRIPTION_STATUSES:
        tenant.subscription_status = SubscriptionStatus(raw_status)

    tenant.stripe_subscription_id = subscription["id"]
    period_end = subscription.get("current_period_end")
    if period_end:
        tenant.subscription_current_period_end = datetime.datetime.fromtimestamp(period_end, tz=datetime.timezone.utc)

    audit_service.record(
        db,
        actor_user_id=None,
        action="stripe_subscription_updated",
        entity_type="clinic" if isinstance(tenant, Clinic) else "user",
        entity_id=tenant.id,
        after={"plan": tenant.subscription_plan.value if tenant.subscription_plan else None, "status": tenant.subscription_status.value},
    )


def process_stripe_event(db: Session, event: dict) -> None:
    """Seção 8.3/19.2 — processa o evento já validado/deduplicado, atualizando
    subscription_status/subscription_plan (evento SubscriptionUpdated do PRD)."""
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        tenant = _find_tenant_by_customer_id(db, data["customer"])
        subscription_id = data.get("subscription")
        if tenant is not None and subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            _apply_subscription_state(db, tenant, subscription)
            db.commit()

    elif event_type == "customer.subscription.updated":
        tenant = _find_tenant_by_customer_id(db, data["customer"])
        if tenant is not None:
            _apply_subscription_state(db, tenant, data)
            db.commit()

    elif event_type == "customer.subscription.deleted":
        tenant = _find_tenant_by_customer_id(db, data["customer"])
        if tenant is not None:
            tenant.subscription_status = SubscriptionStatus.CANCELED
            tenant.subscription_plan = SubscriptionPlan.FREE
            tenant.stripe_subscription_id = None
            audit_service.record(
                db,
                actor_user_id=None,
                action="stripe_subscription_canceled",
                entity_type="clinic" if isinstance(tenant, Clinic) else "user",
                entity_id=tenant.id,
            )
            db.commit()

    elif event_type == "invoice.payment_succeeded":
        tenant = _find_tenant_by_customer_id(db, data["customer"])
        if tenant is not None:
            audit_service.record(
                db,
                actor_user_id=None,
                action="stripe_invoice_payment_succeeded",
                entity_type="clinic" if isinstance(tenant, Clinic) else "user",
                entity_id=tenant.id,
            )
            db.commit()

    elif event_type == "invoice.payment_failed":
        tenant = _find_tenant_by_customer_id(db, data["customer"])
        if tenant is not None:
            tenant.subscription_status = SubscriptionStatus.PAST_DUE
            audit_service.record(
                db,
                actor_user_id=None,
                action="stripe_invoice_payment_failed",
                entity_type="clinic" if isinstance(tenant, Clinic) else "user",
                entity_id=tenant.id,
            )
            db.commit()
