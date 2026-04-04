from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.schemas.portfolio import PortfolioResponse, CreatePortfolioRequest, HoldingDetail
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolios(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio)
        .options(joinedload(Portfolio.holdings))
        .where(Portfolio.user_id == user.id)
        .order_by(Portfolio.is_default.desc(), Portfolio.created_at)
    )
    portfolios = result.unique().scalars().all()

    return [
        PortfolioResponse(
            id=str(p.id),
            name=p.name,
            is_default=p.is_default,
            total_invested=sum(h.total_invested for h in p.holdings if h.quantity > 0),
            current_value=sum(h.current_value for h in p.holdings if h.quantity > 0),
            total_gain=sum(h.total_gain for h in p.holdings if h.quantity > 0),
            total_gain_pct=((sum(h.total_gain for h in p.holdings if h.quantity > 0) /
                            sum(h.total_invested for h in p.holdings if h.quantity > 0) * 100)
                           if sum(h.total_invested for h in p.holdings if h.quantity > 0) else 0),
            holdings_count=len([h for h in p.holdings if h.quantity > 0]),
        )
        for p in portfolios
    ]


@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(
    body: CreatePortfolioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = Portfolio(user_id=user.id, name=body.name, is_default=False)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)

    return PortfolioResponse(
        id=str(portfolio.id),
        name=portfolio.name,
        is_default=portfolio.is_default,
        total_invested=0,
        current_value=0,
        total_gain=0,
        total_gain_pct=0,
        holdings_count=0,
    )


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingDetail])
async def get_portfolio_holdings(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    asset_type: str | None = Query(None),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = (
        select(Holding)
        .options(joinedload(Holding.asset), joinedload(Holding.transactions))
        .where(Holding.portfolio_id == portfolio.id, Holding.quantity > 0)
    )
    if asset_type:
        query = query.where(Holding.asset.has(type=asset_type))

    result = await db.execute(query)
    holdings = result.unique().scalars().all()

    return [
        HoldingDetail(
            id=str(h.id),
            asset_id=str(h.asset_id),
            asset_name=h.asset.name,
            asset_type=h.asset.type.value,
            symbol=h.asset.symbol,
            folio_number=h.folio_number,
            quantity=h.quantity,
            avg_cost=h.avg_cost,
            total_invested=h.total_invested,
            current_price=h.current_price,
            current_value=h.current_value,
            day_change=h.day_change,
            day_change_pct=h.day_change_pct,
            total_gain=h.total_gain,
            total_gain_pct=h.total_gain_pct,
            xirr=h.xirr,
            transactions_count=len(h.transactions),
        )
        for h in holdings
    ]
