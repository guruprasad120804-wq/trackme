"""Mutual Fund data service using MFAPI.in (free, no auth required)."""
import logging

import httpx

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in"


async def search_mutual_funds(query: str, limit: int = 10) -> list[dict]:
    """Search mutual fund schemes by name."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{MFAPI_BASE}/mf/search", params={"q": query})
            resp.raise_for_status()
            results = resp.json()
            return [
                {
                    "scheme_code": str(r.get("schemeCode", "")),
                    "scheme_name": r.get("schemeName", ""),
                }
                for r in results[:limit]
            ]
        except Exception as e:
            logger.warning("MFAPI search failed: %s", e)
            return []


async def get_nav_history(scheme_code: str) -> dict:
    """Get NAV history for a mutual fund scheme."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{MFAPI_BASE}/mf/{scheme_code}")
            resp.raise_for_status()
            data = resp.json()
            return {
                "scheme_code": scheme_code,
                "scheme_name": data.get("meta", {}).get("scheme_name", ""),
                "fund_house": data.get("meta", {}).get("fund_house", ""),
                "scheme_type": data.get("meta", {}).get("scheme_type", ""),
                "scheme_category": data.get("meta", {}).get("scheme_category", ""),
                "nav_data": [
                    {"date": d.get("date", ""), "nav": d.get("nav", "")}
                    for d in (data.get("data", []))[:365]  # Last ~1 year
                ],
            }
        except Exception as e:
            logger.warning("MFAPI NAV history failed for %s: %s", scheme_code, e)
            return {}


async def get_latest_nav(scheme_code: str) -> dict | None:
    """Get latest NAV for a scheme."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{MFAPI_BASE}/mf/{scheme_code}/latest")
            resp.raise_for_status()
            data = resp.json()
            nav_data = data.get("data", [{}])
            if nav_data:
                return {"date": nav_data[0].get("date", ""), "nav": nav_data[0].get("nav", "")}
            return None
        except Exception as e:
            logger.warning("MFAPI latest NAV failed for %s: %s", scheme_code, e)
            return None
