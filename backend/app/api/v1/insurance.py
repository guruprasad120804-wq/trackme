"""Insurance policy tracking API."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.insurance import InsurancePolicy
from app.utils.dependencies import get_current_user

router = APIRouter()


class InsuranceRequest(BaseModel):
    policy_number: str
    provider: str
    type: str  # term, endowment, ulip, health, vehicle, travel
    sum_assured: float = 0
    premium_amount: float = 0
    premium_frequency: str = "yearly"
    next_premium_date: str | None = None
    maturity_date: str | None = None
    start_date: str | None = None
    nominee: str | None = None
    status: str = "active"
    notes: str | None = None


@router.get("/")
async def list_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsurancePolicy)
        .where(InsurancePolicy.user_id == user.id)
        .order_by(InsurancePolicy.next_premium_date.asc().nullslast())
    )
    policies = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "policy_number": p.policy_number,
            "provider": p.provider,
            "type": p.type,
            "sum_assured": str(p.sum_assured),
            "premium_amount": str(p.premium_amount),
            "premium_frequency": p.premium_frequency,
            "next_premium_date": p.next_premium_date.isoformat() if p.next_premium_date else None,
            "maturity_date": p.maturity_date.isoformat() if p.maturity_date else None,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "nominee": p.nominee,
            "status": p.status,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in policies
    ]


@router.post("/")
async def create_policy(
    body: InsuranceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type

    policy = InsurancePolicy(
        user_id=user.id,
        policy_number=body.policy_number,
        provider=body.provider,
        type=body.type,
        sum_assured=body.sum_assured,
        premium_amount=body.premium_amount,
        premium_frequency=body.premium_frequency,
        next_premium_date=date_type.fromisoformat(body.next_premium_date) if body.next_premium_date else None,
        maturity_date=date_type.fromisoformat(body.maturity_date) if body.maturity_date else None,
        start_date=date_type.fromisoformat(body.start_date) if body.start_date else None,
        nominee=body.nominee,
        status=body.status,
        notes=body.notes,
    )
    db.add(policy)
    await db.flush()

    # Auto-create premium due alert if next_premium_date is set
    if policy.next_premium_date:
        from app.models.alert import Alert, AlertCondition
        alert = Alert(
            user_id=user.id,
            name=f"Premium Due: {body.provider} ({body.type})",
            condition=AlertCondition.SIP_REMINDER,
            threshold=float(body.premium_amount) if body.premium_amount else None,
            channels=["PUSH"],
            is_active=True,
            is_recurring=True,
            rule_json={"policy_id": str(policy.id), "type": "premium_reminder"},
        )
        db.add(alert)

    await db.commit()
    await db.refresh(policy)
    return {"id": str(policy.id), "status": "created"}


@router.patch("/{policy_id}")
async def update_policy(
    policy_id: str,
    body: InsuranceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type

    result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.id == uuid.UUID(policy_id),
            InsurancePolicy.user_id == user.id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.policy_number = body.policy_number
    policy.provider = body.provider
    policy.type = body.type
    policy.sum_assured = body.sum_assured
    policy.premium_amount = body.premium_amount
    policy.premium_frequency = body.premium_frequency
    policy.next_premium_date = date_type.fromisoformat(body.next_premium_date) if body.next_premium_date else None
    policy.maturity_date = date_type.fromisoformat(body.maturity_date) if body.maturity_date else None
    policy.start_date = date_type.fromisoformat(body.start_date) if body.start_date else None
    policy.nominee = body.nominee
    policy.status = body.status
    policy.notes = body.notes
    await db.commit()
    return {"id": str(policy.id), "status": "updated"}


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.id == uuid.UUID(policy_id),
            InsurancePolicy.user_id == user.id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    await db.delete(policy)
    await db.commit()
    return {"status": "deleted"}
