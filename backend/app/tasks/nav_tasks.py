"""Background tasks for NAV and market price updates."""
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.nav_tasks.update_all_navs")
def update_all_navs():
    """Fetch latest NAVs from AMFI for all mutual fund schemes."""
    import asyncio
    asyncio.run(_update_navs())


async def _update_navs():
    import httpx
    from decimal import Decimal
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import async_session
    from app.models.asset import Asset
    from app.models.market import CurrentPrice
    from app.services.portfolio_calc import recalculate_holdings

    settings = get_settings()

    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.amfi_nav_url, timeout=60)
        resp.raise_for_status()

    updated_asset_ids = []

    async with async_session() as db:
        lines = resp.text.strip().split("\n")
        updated = 0

        for line in lines:
            parts = line.strip().split(";")
            if len(parts) < 5:
                continue

            try:
                amfi_code = parts[0].strip()
                nav_value = Decimal(parts[4].strip())
            except (ValueError, IndexError):
                continue

            if not amfi_code or amfi_code == "Scheme Code":
                continue

            result = await db.execute(select(Asset).where(Asset.amfi_code == amfi_code))
            asset = result.scalar_one_or_none()
            if not asset:
                continue

            result = await db.execute(select(CurrentPrice).where(CurrentPrice.asset_id == asset.id))
            current = result.scalar_one_or_none()

            if current:
                old_price = current.price
                current.price = nav_value
                current.change = nav_value - old_price
                current.change_pct = ((nav_value - old_price) / old_price * 100) if old_price else Decimal(0)
            else:
                current = CurrentPrice(asset_id=asset.id, price=nav_value)
                db.add(current)

            updated_asset_ids.append(asset.id)
            updated += 1

        await db.commit()

        # Recalculate holdings with updated prices
        if updated_asset_ids:
            await recalculate_holdings(db, updated_asset_ids)

        logger.info("NAV update: %d schemes updated", updated)
        return {"updated": updated}


@celery_app.task(name="app.tasks.nav_tasks.update_market_prices")
def update_market_prices():
    """Update stock/ETF prices during market hours using yfinance."""
    import asyncio
    asyncio.run(_update_market_prices())


async def _update_market_prices():
    import time
    from decimal import Decimal
    from sqlalchemy import select

    from app.database import async_session
    from app.models.asset import Asset, AssetType
    from app.models.market import CurrentPrice
    from app.services.portfolio_calc import recalculate_holdings

    async with async_session() as db:
        result = await db.execute(
            select(Asset).where(
                Asset.type.in_([AssetType.STOCK, AssetType.ETF]),
                Asset.symbol.isnot(None),
            )
        )
        assets = result.scalars().all()

        if not assets:
            logger.info("No stock/ETF assets to update")
            return {"updated": 0}

        # yfinance is sync — run in batches
        import yfinance as yf

        updated = 0
        updated_asset_ids = []

        for asset in assets:
            try:
                symbol = f"{asset.symbol}.NS"
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info

                price = Decimal(str(info.last_price)) if info.last_price else None
                prev_close = Decimal(str(info.previous_close)) if info.previous_close else None

                if not price:
                    logger.warning("No price for %s", symbol)
                    continue

                change = (price - prev_close) if prev_close else Decimal(0)
                change_pct = (change / prev_close * 100) if prev_close and prev_close > 0 else Decimal(0)

                # Update current price
                result = await db.execute(select(CurrentPrice).where(CurrentPrice.asset_id == asset.id))
                current = result.scalar_one_or_none()

                if current:
                    current.price = price
                    current.change = change
                    current.change_pct = change_pct
                else:
                    current = CurrentPrice(asset_id=asset.id, price=price, change=change, change_pct=change_pct)
                    db.add(current)

                updated_asset_ids.append(asset.id)
                updated += 1
                logger.info("%s: ₹%s (%s%%)", asset.symbol, price, change_pct)

                time.sleep(1)  # Rate limit: 1 request per second

            except Exception as e:
                logger.warning("Failed to fetch price for %s: %s", asset.symbol, e)

        await db.commit()

        # Recalculate holdings
        if updated_asset_ids:
            await recalculate_holdings(db, updated_asset_ids)

        logger.info("Market prices: %d stocks updated", updated)
        return {"updated": updated}
