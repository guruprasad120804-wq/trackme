"""Background tasks for alert evaluation and notification."""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.alert_tasks.evaluate_all_alerts")
def evaluate_all_alerts():
    """Check all active alerts against current prices and portfolio values."""
    import asyncio
    asyncio.run(_evaluate_alerts())


async def _evaluate_alerts():
    from decimal import Decimal
    from datetime import datetime, timezone
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.database import async_session
    from app.models.alert import Alert, AlertHistory, AlertCondition
    from app.models.market import CurrentPrice
    from app.models.holding import Holding

    async with async_session() as db:
        result = await db.execute(
            select(Alert).where(Alert.is_active.is_(True))
        )
        alerts = result.scalars().all()

        for alert in alerts:
            triggered = False
            current_value = None

            if alert.condition == AlertCondition.PRICE_ABOVE and alert.asset_id:
                price_result = await db.execute(
                    select(CurrentPrice).where(CurrentPrice.asset_id == alert.asset_id)
                )
                cp = price_result.scalar_one_or_none()
                if cp and alert.threshold and cp.price >= alert.threshold:
                    triggered = True
                    current_value = cp.price

            elif alert.condition == AlertCondition.PRICE_BELOW and alert.asset_id:
                price_result = await db.execute(
                    select(CurrentPrice).where(CurrentPrice.asset_id == alert.asset_id)
                )
                cp = price_result.scalar_one_or_none()
                if cp and alert.threshold and cp.price <= alert.threshold:
                    triggered = True
                    current_value = cp.price

            elif alert.condition == AlertCondition.PORTFOLIO_VALUE_ABOVE:
                holdings_result = await db.execute(
                    select(Holding)
                    .join(Holding.portfolio)
                    .where(Holding.portfolio.has(user_id=alert.user_id))
                    .where(Holding.quantity > 0)
                )
                holdings = holdings_result.scalars().all()
                total = sum(h.current_value for h in holdings)
                if alert.threshold and total >= alert.threshold:
                    triggered = True
                    current_value = total

            elif alert.condition == AlertCondition.PORTFOLIO_VALUE_BELOW:
                holdings_result = await db.execute(
                    select(Holding)
                    .join(Holding.portfolio)
                    .where(Holding.portfolio.has(user_id=alert.user_id))
                    .where(Holding.quantity > 0)
                )
                holdings = holdings_result.scalars().all()
                total = sum(h.current_value for h in holdings)
                if alert.threshold and total <= alert.threshold:
                    triggered = True
                    current_value = total

            if triggered:
                # Record in history
                history = AlertHistory(
                    alert_id=alert.id,
                    value_at_trigger=current_value,
                    notification_sent=False,
                    message=f"Alert '{alert.name}' triggered: value = {current_value}",
                )
                db.add(history)

                alert.last_triggered = datetime.now(timezone.utc)

                if not alert.is_recurring:
                    alert.is_active = False

                # Send notifications
                for channel in (alert.channels or []):
                    await _send_notification(alert, channel, current_value)
                    history.notification_sent = True
                    history.channel_used = channel

        await db.commit()


async def _send_notification(alert, channel: str, value):
    """Send alert notification via the specified channel."""
    if channel == "whatsapp":
        from app.integrations.whatsapp.client import send_whatsapp_message
        # TODO: Get user's phone number and send
        pass
    elif channel == "email":
        # TODO: Send email notification
        pass
    elif channel == "push":
        # TODO: Send push notification
        pass
