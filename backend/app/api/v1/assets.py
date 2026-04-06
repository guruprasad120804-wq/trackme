"""Asset search API — searches local DB + MFAPI.in for mutual funds."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.user import User
from app.services.mf_data import search_mutual_funds, get_nav_history
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/search")
async def search_assets(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search assets by name or symbol (local DB + MFAPI for MFs)."""
    pattern = f"%{q}%"
    result = await db.execute(
        select(Asset)
        .where(or_(Asset.name.ilike(pattern), Asset.symbol.ilike(pattern)))
        .order_by(Asset.name)
        .limit(limit)
    )
    assets = result.scalars().all()

    local_results = [
        {
            "id": str(a.id),
            "name": a.name,
            "symbol": a.symbol,
            "type": a.type.value if a.type else None,
            "isin": a.isin,
            "source": "local",
        }
        for a in assets
    ]

    # Also search MFAPI for mutual funds (supplement local results)
    mf_results = []
    if len(local_results) < limit:
        mf_hits = await search_mutual_funds(q, limit=limit - len(local_results))
        for mf in mf_hits:
            mf_results.append({
                "id": None,
                "name": mf["scheme_name"],
                "symbol": mf["scheme_code"],
                "type": "mutual_fund",
                "isin": None,
                "source": "mfapi",
            })

    return local_results + mf_results


@router.get("/mf/{scheme_code}/nav-history")
async def mf_nav_history(
    scheme_code: str,
    user: User = Depends(get_current_user),
):
    """Get NAV history for a mutual fund scheme from MFAPI.in."""
    data = await get_nav_history(scheme_code)
    if not data:
        return {"error": "Scheme not found"}
    return data
