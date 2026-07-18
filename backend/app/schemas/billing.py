import datetime

from pydantic import BaseModel

from app.models.enums import SubscriptionPlan, SubscriptionStatus


class CheckoutSessionRequest(BaseModel):
    plan: SubscriptionPlan


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingPortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatusResponse(BaseModel):
    subscription_plan: SubscriptionPlan | None
    subscription_status: SubscriptionStatus
    subscription_current_period_end: datetime.datetime | None
    has_paid_access: bool
    stripe_configured: bool
