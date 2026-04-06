"""Recalculate holding values after price updates."""
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holding import Holding
from app.models.market import CurrentPrice

logger = logging.getLogger(__name__)


async def recalculate_holdings(db: AsyncSession, asset_ids: list | None = None):
    """Recalculate current_value, gains, and day_change for holdings.

    If asset_ids is provided, only recalculate holdings for those assets.
    Otherwise recalculates all holdings with quantity > 0.
    """
    query = select(Holding).where(Holding.quantity > 0)
    if asset_ids:
        query = query.where(Holding.asset_id.in_(asset_ids))

    result = await db.execute(query)
    holdings = result.scalars().all()

    updated = 0
    for h in holdings:
        # Get latest price
        price_result = await db.execute(
            select(CurrentPrice).where(CurrentPrice.asset_id == h.asset_id)
        )
        cp = price_result.scalar_one_or_none()
        if not cp or not cp.price:
            continue

        h.current_price = cp.price
        h.current_value = h.quantity * cp.price

        if h.total_invested and h.total_invested > 0:
            h.total_gain = h.current_value - h.total_invested
            h.total_gain_pct = (h.total_gain / h.total_invested) * Decimal("100")
        else:
            h.total_gain = Decimal("0")
            h.total_gain_pct = Decimal("0")

        if cp.change:
            h.day_change = h.quantity * cp.change
        if cp.change_pct:
            h.day_change_pct = cp.change_pct

        updated += 1

    await db.commit()
    logger.info("Recalculated %d holdings", updated)
    return updated
