from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    current_period_end: str | None
    limits: dict


class CreateSubscriptionRequest(BaseModel):
    plan: str  # "pro" or "premium"


class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: dict


class PlanInfo(BaseModel):
    name: str
    price_monthly: int
    price_yearly: int
    features: list[str]
    limits: dict
