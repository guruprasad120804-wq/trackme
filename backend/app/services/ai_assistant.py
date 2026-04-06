"""AI-powered portfolio assistant using OpenRouter with caching, retry, and deep context."""
import hashlib
import logging
import time
import uuid
from collections import defaultdict
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models.holding import Holding
from app.models.asset import Asset
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)
settings = get_settings()

# --- Response cache ---
_cache: dict[str, tuple[float, dict]] = {}  # key -> (expiry_timestamp, response)
CACHE_TTL = 90  # seconds
CACHE_MAX_SIZE = 200

SYSTEM_PROMPT = """You are TrackMe AI, a portfolio intelligence assistant with access to the user's real-time portfolio data.

CAPABILITIES:
- Analyze portfolio composition, performance, and risk
- Identify concentration risks and diversification gaps
- Explain holdings performance with actual numbers
- Provide educational insights on financial concepts
- Spot trends in recent transaction activity

RULES:
- ALWAYS ground answers in the provided portfolio data — cite specific numbers
- If the portfolio is empty, acknowledge it and suggest getting started
- Never fabricate holdings or prices not in the data
- Suggest general strategies (diversification, rebalancing) but NEVER specific buy/sell recommendations
- Include a brief disclaimer when discussing investment strategies
- Format all currency in INR (₹)
- Be concise — lead with the insight, then support with data

USER'S PORTFOLIO DATA:
{portfolio_context}
"""


def _get_cache_key(user_id: str, message: str) -> str:
    return hashlib.sha256(f"{user_id}:{message}".encode()).hexdigest()


def _prune_cache():
    if len(_cache) <= CACHE_MAX_SIZE:
        return
    now = time.time()
    expired = [k for k, (exp, _) in _cache.items() if exp < now]
    for k in expired:
        del _cache[k]
    # If still over limit, drop oldest
    if len(_cache) > CACHE_MAX_SIZE:
        sorted_keys = sorted(_cache, key=lambda k: _cache[k][0])
        for k in sorted_keys[: len(_cache) - CACHE_MAX_SIZE]:
            del _cache[k]


async def _build_portfolio_context(user_id: str, db: AsyncSession) -> str:
    """Build structured portfolio context for the AI."""
    uid = uuid.UUID(user_id)

    # --- Fetch holdings ---
    result = await db.execute(
        select(Holding)
        .options(joinedload(Holding.asset))
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=uid))
        .where(Holding.quantity > 0)
    )
    holdings = result.unique().scalars().all()

    if not holdings:
        return "User has no holdings yet. Portfolio is empty."

    # --- Summary ---
    total_invested = sum(h.total_invested for h in holdings)
    current_value = sum(h.current_value for h in holdings)
    total_gain = current_value - total_invested
    gain_pct = (total_gain / total_invested * 100) if total_invested else Decimal(0)
    day_change = sum(h.day_change for h in holdings)
    day_change_pct = (day_change / current_value * 100) if current_value else Decimal(0)

    lines = [
        "PORTFOLIO SUMMARY:",
        f"Total Invested: ₹{total_invested:,.2f} | Current Value: ₹{current_value:,.2f} | P&L: ₹{total_gain:,.2f} ({gain_pct:+.2f}%)",
        f"Day Change: ₹{day_change:,.2f} ({day_change_pct:+.2f}%)",
        f"Holdings Count: {len(holdings)}",
    ]

    # --- Allocation by asset type ---
    allocation: dict[str, Decimal] = defaultdict(Decimal)
    for h in holdings:
        allocation[h.asset.type.value] += h.current_value

    lines.append("")
    lines.append("ALLOCATION BY TYPE:")
    for atype, value in sorted(allocation.items(), key=lambda x: x[1], reverse=True):
        pct = (value / current_value * 100) if current_value else Decimal(0)
        lines.append(f"- {atype.replace('_', ' ').title()}: {pct:.1f}% (₹{value:,.2f})")

    # --- Top 10 holdings ---
    top = sorted(holdings, key=lambda x: x.current_value, reverse=True)[:10]
    lines.append("")
    lines.append("TOP HOLDINGS (by value):")
    for i, h in enumerate(top, 1):
        symbol = f" [{h.asset.symbol}]" if h.asset.symbol else ""
        day = f", Day: {h.day_change_pct:+.2f}%" if h.day_change_pct else ""
        xirr = f", XIRR: {h.xirr:.1f}%" if h.xirr else ""
        lines.append(
            f"{i}. {h.asset.name}{symbol} ({h.asset.type.value}) — "
            f"Qty: {h.quantity:.4f}, Avg: ₹{h.avg_cost:,.2f}, "
            f"Current: ₹{h.current_price:,.2f}, Value: ₹{h.current_value:,.2f}, "
            f"P&L: {h.total_gain_pct:+.2f}%{day}{xirr}"
        )

    # --- Recent transactions ---
    txn_result = await db.execute(
        select(Transaction)
        .join(Transaction.holding)
        .join(Holding.portfolio)
        .options(joinedload(Transaction.holding).joinedload(Holding.asset))
        .where(Holding.portfolio.has(user_id=uid))
        .order_by(Transaction.trade_date.desc())
        .limit(10)
    )
    recent_txns = txn_result.unique().scalars().all()

    if recent_txns:
        lines.append("")
        lines.append("RECENT TRANSACTIONS:")
        for t in recent_txns:
            asset_name = t.holding.asset.name if t.holding and t.holding.asset else "Unknown"
            lines.append(
                f"- {t.trade_date}: {t.type.value.upper()} {asset_name} — "
                f"{t.quantity:.4f} units @ ₹{t.price:,.2f} = ₹{t.amount:,.2f}"
            )

    return "\n".join(lines)


async def _call_openrouter(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    messages: list[dict],
) -> dict:
    """Make a single OpenRouter API call. Raises on failure."""
    resp = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "TrackMe AI",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        },
    )
    resp.raise_for_status()
    return resp.json()


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


async def get_ai_response(
    user_id: str,
    message: str,
    history: list[tuple[str, str]],
    db: AsyncSession,
) -> dict:
    """Get AI response with caching, per-model retry, and deep portfolio context."""
    api_key = settings.openrouter_api_key or settings.anthropic_api_key
    if not api_key:
        return {
            "content": "AI assistant is not configured. Please add your API key.",
            "metadata": {"error": "no_api_key"},
        }

    # --- Cache check ---
    cache_key = _get_cache_key(user_id, message)
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.time():
        logger.info("Cache hit for user %s", user_id[:8])
        result = cached[1].copy()
        result["metadata"] = {**result.get("metadata", {}), "cached": True}
        return result

    # --- Build context and messages ---
    portfolio_context = await _build_portfolio_context(user_id, db)
    system = SYSTEM_PROMPT.format(portfolio_context=portfolio_context)

    messages = [{"role": "system", "content": system}]
    for role, content in history[-20:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    # --- Call with per-model retry ---
    models = [
        settings.openrouter_primary_model,
        settings.openrouter_fallback_model,
        settings.openrouter_backup_model,
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        last_error = None
        bail = False

        for model in models:
            if bail:
                break
            for attempt in (1, 2):
                try:
                    logger.info("Trying %s (attempt %d)", model, attempt)
                    data = await _call_openrouter(client, api_key, model, messages)
                    logger.info("Success with %s on attempt %d", model, attempt)

                    result = {
                        "content": data["choices"][0]["message"]["content"],
                        "metadata": {
                            "model": data.get("model", model),
                            "model_requested": model,
                            "usage": data.get("usage", {}),
                        },
                    }

                    # Store in cache
                    _cache[cache_key] = (time.time() + CACHE_TTL, result)
                    _prune_cache()

                    return result

                except httpx.HTTPStatusError as e:
                    last_error = e
                    status = e.response.status_code
                    logger.warning("%s attempt %d failed: HTTP %d", model, attempt, status)
                    if status not in _RETRYABLE_STATUSES:
                        bail = True  # non-retryable client error — stop everything
                        break
                    # retryable — try same model again (inner loop continues)

                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_error = e
                    logger.warning("%s attempt %d: timeout/unreachable", model, attempt)
                    # retryable — try same model again

        # All models exhausted
        if isinstance(last_error, httpx.HTTPStatusError):
            status = last_error.response.status_code
            if status == 429:
                msg = "AI is busy right now. Please try again in a moment."
            else:
                msg = "AI service is temporarily unavailable."
            return {"content": msg, "metadata": {"error": str(status)}}

        return {
            "content": "Could not reach AI service. Please try again.",
            "metadata": {"error": "connection_error"},
        }
