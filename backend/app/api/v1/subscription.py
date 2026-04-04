from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, PLAN_LIMITS
from app.schemas.subscription import SubscriptionResponse, PlanInfo
from app.utils.dependencies import get_current_user

router = APIRouter()

PLAN_PRICING = {
    "pro": {"monthly": 299, "yearly": 2999, "name": "Pro", "features": [
        "5 portfolios", "5 broker connections", "25 alerts",
        "50 AI queries/day", "WhatsApp bot", "Email scanning",
        "Excel export", "Advanced analytics",
    ]},
    "premium": {"monthly": 599, "yearly": 5999, "name": "Premium", "features": [
        "Unlimited portfolios", "Unlimited broker connections",
        "Unlimited alerts", "Unlimited AI queries",
        "WhatsApp bot", "Email scanning", "Excel export",
        "Advanced analytics", "Priority support", "API access",
    ]},
}


@router.get("/", response_model=SubscriptionResponse)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    plan = sub.plan if sub else SubscriptionPlan.FREE
    status = sub.status if sub else SubscriptionStatus.ACTIVE

    return SubscriptionResponse(
        plan=plan.value,
        status=status.value,
        current_period_end=str(sub.current_period_end) if sub and sub.current_period_end else None,
        limits=PLAN_LIMITS[plan],
    )


@router.get("/plans", response_model=list[PlanInfo])
async def get_plans():
    return [
        PlanInfo(
            name=info["name"],
            price_monthly=info["monthly"],
            price_yearly=info["yearly"],
            features=info["features"],
            limits=PLAN_LIMITS[SubscriptionPlan(plan_key)],
        )
        for plan_key, info in PLAN_PRICING.items()
    ]


@router.post("/checkout")
async def create_checkout(
    plan: str,
    billing: str = "monthly",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a Razorpay subscription and returns checkout data."""
    if plan not in PLAN_PRICING:
        raise HTTPException(status_code=400, detail="Invalid plan")

    from app.config import get_settings
    settings = get_settings()

    if not settings.razorpay_key_id:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    import razorpay
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    amount = PLAN_PRICING[plan]["monthly" if billing == "monthly" else "yearly"]

    order = client.order.create({
        "amount": amount * 100,  # Razorpay expects paise
        "currency": "INR",
        "receipt": f"trackme_{user.id}_{plan}",
        "notes": {"user_id": str(user.id), "plan": plan, "billing": billing},
    })

    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "key_id": settings.razorpay_key_id,
        "user_email": user.email,
        "user_name": user.name,
    }


@router.post("/verify")
async def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    plan: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment and activate subscription."""
    from app.config import get_settings
    settings = get_settings()

    import razorpay
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Activate subscription
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    if sub:
        sub.plan = SubscriptionPlan(plan)
        sub.status = SubscriptionStatus.ACTIVE
        sub.razorpay_subscription_id = razorpay_payment_id
    else:
        sub = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan(plan),
            status=SubscriptionStatus.ACTIVE,
            razorpay_subscription_id=razorpay_payment_id,
        )
        db.add(sub)

    await db.commit()
    return {"status": "active", "plan": plan}
