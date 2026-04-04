from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.schemas.portfolio import TransactionResponse, TransactionPage
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=TransactionPage)
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    asset_type: str | None = Query(None),
    transaction_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
):
    base_query = (
        select(Transaction)
        .options(joinedload(Transaction.holding).joinedload(Holding.asset))
        .join(Transaction.holding)
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=user.id))
    )

    if asset_type:
        base_query = base_query.where(Holding.asset.has(type=asset_type))
    if transaction_type:
        base_query = base_query.where(Transaction.type == transaction_type)
    if date_from:
        base_query = base_query.where(Transaction.trade_date >= date_from)
    if date_to:
        base_query = base_query.where(Transaction.trade_date <= date_to)
    if search:
        base_query = base_query.where(Holding.asset.has(Asset.name.ilike(f"%{search}%")))

    # Count
    count_q = select(sqlfunc.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    result = await db.execute(
        base_query
        .order_by(Transaction.trade_date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    txns = result.unique().scalars().all()

    return TransactionPage(
        items=[
            TransactionResponse(
                id=str(t.id),
                holding_id=str(t.holding_id),
                asset_name=t.holding.asset.name,
                type=t.type.value,
                trade_date=str(t.trade_date),
                quantity=t.quantity,
                price=t.price,
                amount=t.amount,
                charges=t.charges,
                source=t.source,
                notes=t.notes,
            )
            for t in txns
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


from app.models.asset import Asset  # noqa: E402
