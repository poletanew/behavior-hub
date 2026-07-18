from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import (
    BillingPortalResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionStatusResponse,
)
from app.services import billing_service

router = APIRouter(tags=["billing"])


@router.get("/billing/status", response_model=SubscriptionStatusResponse)
def get_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return billing_service.get_subscription_status(db, user)


@router.post("/stripe/checkout", response_model=CheckoutSessionResponse)
def create_checkout(
    payload: CheckoutSessionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Seção 19.1 — POST /stripe/checkout (usuário autenticado)."""
    return billing_service.create_checkout_session(db, user, payload.plan)


@router.post("/stripe/portal", response_model=BillingPortalResponse)
def create_portal(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 26 — botão "Gerenciar assinatura" abre o Portal do Cliente Stripe."""
    return billing_service.create_billing_portal_session(db, user)


@router.post("/webhooks/stripe", status_code=200)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Seção 19.1/28.4 — POST /webhooks/stripe (assinatura validada, idempotente
    por chave de deduplicação de evento)."""
    payload = await request.body()
    signature_header = request.headers.get("stripe-signature")

    event = billing_service.verify_and_parse_event(payload, signature_header)
    is_new = billing_service.record_event_or_skip(db, event)
    if not is_new:
        return {"status": "duplicate_ignored"}

    billing_service.process_stripe_event(db, event)
    return {"status": "processed"}
