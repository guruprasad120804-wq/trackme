"""Background tasks for NAV and market price updates."""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.nav_tasks.update_all_navs")
def update_all_navs():
    """Fetch latest NAVs from AMFI for all mutual fund schemes."""
    import asyncio
    asyncio.run(_update_navs())


async def _update_navs():
    import httpx
    from datetime import date
    from decimal import Decimal
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import async_session
    from app.models.asset import Asset, AssetType
    from app.models.market import CurrentPrice

    settings = get_settings()

    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.amfi_nav_url, timeout=60)
        resp.raise_for_status()

    async with async_session() as db:
        # Parse AMFI NAV data (semicolon-delimited)
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

            # Find asset by AMFI code
            result = await db.execute(select(Asset).where(Asset.amfi_code == amfi_code))
            asset = result.scalar_one_or_none()
            if not asset:
                continue

            # Update current price
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

            updated += 1

        await db.commit()
        return {"updated": updated}


@celery_app.task(name="app.tasks.nav_tasks.update_market_prices")
def update_market_prices():
    """Update stock/ETF prices during market hours. Placeholder for market data API integration."""
    # TODO: Integrate with NSE/BSE data feed or a market data provider
    pass
