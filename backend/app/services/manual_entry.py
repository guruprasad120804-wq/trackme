"""Handle manual transaction entry with smart asset resolution."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, TransactionType


async def process_manual_transaction(user_id: str, data: dict, db: AsyncSession) -> dict:
    uid = uuid.UUID(user_id)

    # Find portfolio
    portfolio_id = data.get("portfolio_id")
    if portfolio_id:
        result = await db.execute(
            select(Portfolio).where(Portfolio.id == uuid.UUID(portfolio_id), Portfolio.user_id == uid)
        )
    else:
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == uid, Portfolio.is_default.is_(True))
        )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    # Find or create asset
    asset = None
    if data.get("isin"):
        result = await db.execute(select(Asset).where(Asset.isin == data["isin"]))
        asset = result.scalar_one_or_none()
    if not asset and data.get("symbol"):
        result = await db.execute(select(Asset).where(Asset.symbol == data["symbol"]))
        asset = result.scalar_one_or_none()

    if not asset:
        asset = Asset(
            type=AssetType(data.get("asset_type", "other")),
            name=data["asset_name"],
            symbol=data.get("symbol"),
            isin=data.get("isin"),
        )
        db.add(asset)
        await db.flush()

    # Find or create holding
    folio = data.get("folio_number")
    result = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio.id,
            Holding.asset_id == asset.id,
            Holding.folio_number == folio if folio else Holding.folio_number.is_(None),
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        holding = Holding(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            folio_number=folio,
        )
        db.add(holding)
        await db.flush()

    # Create transaction
    qty = Decimal(str(data.get("quantity", 0)))
    price = Decimal(str(data.get("price", 0)))
    amount = Decimal(str(data.get("amount", 0))) or (qty * price)
    txn_type = TransactionType(data.get("transaction_type", "buy"))

    txn = Transaction(
        holding_id=holding.id,
        type=txn_type,
        trade_date=date.fromisoformat(data["trade_date"]),
        quantity=qty,
        price=price,
        amount=amount,
        charges=Decimal(str(data.get("charges", 0))),
        source="manual",
        notes=data.get("notes"),
    )
    db.add(txn)

    # Update holding quantities
    if txn_type in (TransactionType.BUY, TransactionType.SIP, TransactionType.BONUS, TransactionType.SWITCH_IN):
        holding.quantity += qty
        holding.total_invested += amount
    elif txn_type in (TransactionType.SELL, TransactionType.REDEMPTION, TransactionType.SWITCH_OUT):
        holding.quantity -= qty
        holding.total_invested -= min(amount, holding.total_invested)

    if holding.quantity > 0 and holding.total_invested > 0:
        holding.avg_cost = holding.total_invested / holding.quantity

    await db.commit()

    return {
        "status": "success",
        "transaction_id": str(txn.id),
        "holding_id": str(holding.id),
        "asset_name": asset.name,
    }
