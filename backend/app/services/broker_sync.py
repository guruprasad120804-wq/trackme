"""Broker holdings sync service — fetches and imports stock holdings."""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brokers.base import NormalizedHolding
from app.models.asset import Asset, AssetType
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.import_log import ImportLog

logger = logging.getLogger(__name__)


async def sync_holdings_from_broker(
    user_id: str,
    broker_connection_id: str,
    holdings_data: list[NormalizedHolding],
    db: AsyncSession,
) -> dict:
    """Import normalized broker holdings into the database.

    Same find-or-create pattern as cas_parser.py and mf_import.py.
    """
    import uuid
    uid = uuid.UUID(user_id)
    conn_id = uuid.UUID(broker_connection_id)

    # Get or create default portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == uid, Portfolio.is_default.is_(True))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=uid, name="My Portfolio", is_default=True)
        db.add(portfolio)
        await db.flush()

    stats = {"holdings_synced": 0, "assets_created": 0, "errors": []}

    for h in holdings_data:
        try:
            # Find or create Asset by ISIN first, then by symbol
            asset = None
            if h.get("isin"):
                result = await db.execute(select(Asset).where(Asset.isin == h["isin"]))
                asset = result.scalar_one_or_none()

            if not asset:
                result = await db.execute(
                    select(Asset).where(Asset.symbol == h["symbol"], Asset.type == AssetType.STOCK)
                )
                asset = result.scalar_one_or_none()

            if not asset:
                try:
                    async with db.begin_nested():
                        asset = Asset(
                            type=AssetType.STOCK,
                            name=h["name"],
                            symbol=h["symbol"],
                            isin=h.get("isin"),
                            exchange=h.get("exchange", "NSE"),
                        )
                        db.add(asset)
                        await db.flush()
                    stats["assets_created"] += 1
                except Exception:
                    # Re-fetch on constraint violation
                    if h.get("isin"):
                        result = await db.execute(select(Asset).where(Asset.isin == h["isin"]))
                        asset = result.scalar_one_or_none()
                    if not asset:
                        result = await db.execute(
                            select(Asset).where(Asset.symbol == h["symbol"], Asset.type == AssetType.STOCK)
                        )
                        asset = result.scalar_one_or_none()

            if not asset:
                stats["errors"].append(f"Could not create asset: {h['symbol']}")
                continue

            # Find or create Holding linked to this broker connection
            result = await db.execute(
                select(Holding).where(
                    Holding.portfolio_id == portfolio.id,
                    Holding.asset_id == asset.id,
                    Holding.broker_connection_id == conn_id,
                )
            )
            holding = result.scalar_one_or_none()

            if not holding:
                try:
                    async with db.begin_nested():
                        holding = Holding(
                            portfolio_id=portfolio.id,
                            asset_id=asset.id,
                            broker_connection_id=conn_id,
                        )
                        db.add(holding)
                        await db.flush()
                except Exception:
                    result = await db.execute(
                        select(Holding).where(
                            Holding.portfolio_id == portfolio.id,
                            Holding.asset_id == asset.id,
                            Holding.broker_connection_id == conn_id,
                        )
                    )
                    holding = result.scalar_one_or_none()

            if not holding:
                stats["errors"].append(f"Could not create holding: {h['symbol']}")
                continue

            # Update holding values
            holding.quantity = h["quantity"]
            holding.avg_cost = h["avg_price"]
            holding.current_price = h["current_price"]
            holding.current_value = h["quantity"] * h["current_price"]
            holding.total_invested = h["quantity"] * h["avg_price"]
            if holding.total_invested and holding.total_invested > 0:
                holding.total_gain = holding.current_value - holding.total_invested
                holding.total_gain_pct = (holding.total_gain / holding.total_invested) * 100
            else:
                holding.total_gain = Decimal(0)
                holding.total_gain_pct = Decimal(0)

            stats["holdings_synced"] += 1

        except Exception as e:
            logger.error(f"Error syncing holding {h.get('symbol')}: {e}")
            stats["errors"].append(f"{h.get('symbol')}: {str(e)}")

    # Create import log
    import_log = ImportLog(
        user_id=uid,
        source="broker_sync",
        status="completed",
        schemes_added=stats["assets_created"],
        transactions_added=0,
        errors=len(stats["errors"]),
        error_details="; ".join(stats["errors"]) if stats["errors"] else None,
        summary_json=stats,
    )
    db.add(import_log)

    await db.commit()
    return stats
