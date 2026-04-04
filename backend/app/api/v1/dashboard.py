from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User
from app.models.holding import Holding
from app.models.asset import Asset
from app.schemas.dashboard import DashboardSummary, AssetTypeBreakdown, HoldingSummary, TopMover
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Holding)
        .options(joinedload(Holding.asset))
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=user.id))
        .where(Holding.quantity > 0)
    )
    holdings = result.unique().scalars().all()

    total_invested = sum(h.total_invested for h in holdings)
    current_value = sum(h.current_value for h in holdings)
    total_gain = current_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else Decimal(0)
    day_change = sum(h.day_change for h in holdings)
    day_change_pct = (day_change / (current_value - day_change) * 100) if (current_value - day_change) else Decimal(0)

    # Group by asset type
    type_map: dict[str, dict] = {}
    for h in holdings:
        t = h.asset.type.value
        if t not in type_map:
            type_map[t] = {"invested": Decimal(0), "current_value": Decimal(0), "count": 0}
        type_map[t]["invested"] += h.total_invested
        type_map[t]["current_value"] += h.current_value
        type_map[t]["count"] += 1

    breakdown = []
    for asset_type, data in type_map.items():
        gain = data["current_value"] - data["invested"]
        breakdown.append(AssetTypeBreakdown(
            type=asset_type,
            invested=data["invested"],
            current_value=data["current_value"],
            gain=gain,
            gain_pct=(gain / data["invested"] * 100) if data["invested"] else Decimal(0),
            allocation_pct=(data["current_value"] / current_value * 100) if current_value else Decimal(0),
            count=data["count"],
        ))

    return DashboardSummary(
        total_invested=total_invested,
        current_value=current_value,
        total_gain=total_gain,
        total_gain_pct=total_gain_pct,
        day_change=day_change,
        day_change_pct=day_change_pct,
        xirr=None,  # Computed async via background job
        total_holdings=len(holdings),
        asset_type_breakdown=breakdown,
    )


@router.get("/holdings", response_model=list[HoldingSummary])
async def get_holdings_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    asset_type: str | None = Query(None),
    sort_by: str = Query("current_value"),
    sort_order: str = Query("desc"),
):
    query = (
        select(Holding)
        .options(joinedload(Holding.asset))
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=user.id))
        .where(Holding.quantity > 0)
    )
    if asset_type:
        query = query.where(Holding.asset.has(type=asset_type))

    result = await db.execute(query)
    holdings = result.unique().scalars().all()

    total_value = sum(h.current_value for h in holdings)

    items = []
    for h in holdings:
        items.append(HoldingSummary(
            id=str(h.id),
            asset_name=h.asset.name,
            asset_type=h.asset.type.value,
            symbol=h.asset.symbol,
            quantity=h.quantity,
            avg_cost=h.avg_cost,
            current_price=h.current_price,
            invested=h.total_invested,
            current_value=h.current_value,
            gain=h.total_gain,
            gain_pct=h.total_gain_pct,
            day_change=h.day_change,
            day_change_pct=h.day_change_pct,
            xirr=h.xirr,
            allocation_pct=(h.current_value / total_value * 100) if total_value else Decimal(0),
        ))

    reverse = sort_order == "desc"
    items.sort(key=lambda x: getattr(x, sort_by, 0) or 0, reverse=reverse)
    return items


@router.get("/top-movers", response_model=list[TopMover])
async def get_top_movers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(5),
):
    result = await db.execute(
        select(Holding)
        .options(joinedload(Holding.asset))
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=user.id))
        .where(Holding.quantity > 0)
    )
    holdings = result.unique().scalars().all()

    movers = sorted(holdings, key=lambda h: abs(h.day_change_pct), reverse=True)[:limit]
    return [
        TopMover(
            asset_name=h.asset.name,
            symbol=h.asset.symbol,
            change_pct=h.day_change_pct,
            change_value=h.day_change,
            direction="up" if h.day_change_pct >= 0 else "down",
        )
        for h in movers
    ]
