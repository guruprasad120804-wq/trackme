from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert, AlertHistory
from app.models.asset import Asset
from app.schemas.alert import CreateAlertRequest, AlertResponse, AlertHistoryResponse
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()

    items = []
    for a in alerts:
        asset_name = None
        if a.asset_id:
            asset_result = await db.execute(select(Asset).where(Asset.id == a.asset_id))
            asset = asset_result.scalar_one_or_none()
            asset_name = asset.name if asset else None

        items.append(AlertResponse(
            id=str(a.id),
            name=a.name,
            asset_id=str(a.asset_id) if a.asset_id else None,
            asset_name=asset_name,
            condition=a.condition.value,
            threshold=a.threshold,
            channels=a.channels or ["push"],
            is_active=a.is_active,
            is_recurring=a.is_recurring,
            last_triggered=str(a.last_triggered) if a.last_triggered else None,
            created_at=str(a.created_at),
        ))
    return items


@router.post("/", response_model=AlertResponse)
async def create_alert(
    body: CreateAlertRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    alert = Alert(
        user_id=user.id,
        name=body.name,
        asset_id=uuid.UUID(body.asset_id) if body.asset_id else None,
        condition=body.condition,
        threshold=body.threshold,
        channels=body.channels,
        is_recurring=body.is_recurring,
        rule_json=body.rule_json,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return AlertResponse(
        id=str(alert.id),
        name=alert.name,
        asset_id=str(alert.asset_id) if alert.asset_id else None,
        asset_name=None,
        condition=alert.condition.value,
        threshold=alert.threshold,
        channels=alert.channels or ["push"],
        is_active=alert.is_active,
        is_recurring=alert.is_recurring,
        last_triggered=None,
        created_at=str(alert.created_at),
    )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(
        select(Alert).where(Alert.id == uuid.UUID(alert_id), Alert.user_id == user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
    return {"status": "deleted"}


@router.patch("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(
        select(Alert).where(Alert.id == uuid.UUID(alert_id), Alert.user_id == user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = not alert.is_active
    await db.commit()
    return {"is_active": alert.is_active}


@router.get("/history", response_model=list[AlertHistoryResponse])
async def get_alert_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertHistory)
        .join(AlertHistory.alert)
        .where(Alert.user_id == user.id)
        .order_by(AlertHistory.triggered_at.desc())
        .limit(50)
    )
    history = result.scalars().all()

    items = []
    for h in history:
        alert_result = await db.execute(select(Alert).where(Alert.id == h.alert_id))
        alert = alert_result.scalar_one_or_none()
        items.append(AlertHistoryResponse(
            id=str(h.id),
            alert_name=alert.name if alert else "Deleted alert",
            triggered_at=str(h.triggered_at),
            value_at_trigger=h.value_at_trigger,
            channel_used=h.channel_used,
            message=h.message,
        ))
    return items
