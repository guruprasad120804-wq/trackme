"""AI-powered portfolio assistant using Claude."""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models.holding import Holding
from app.models.asset import Asset

settings = get_settings()

SYSTEM_PROMPT = """You are TrackMe AI, an intelligent portfolio assistant. You help users understand their investments, analyze portfolio performance, and provide educational financial insights.

IMPORTANT RULES:
- You have access to the user's real portfolio data (provided below).
- Answer questions about their holdings, performance, allocation, and transactions.
- Provide educational explanations about financial concepts.
- You may suggest general strategies (diversification, rebalancing) but NEVER give specific buy/sell recommendations.
- Always include a disclaimer when discussing investment strategies.
- Be concise and use numbers from the actual portfolio data.
- Format currency in INR (₹).
- When uncertain, say so clearly.

USER'S PORTFOLIO SNAPSHOT:
{portfolio_context}
"""


async def _build_portfolio_context(user_id: str, db: AsyncSession) -> str:
    """Build a text summary of the user's portfolio for the AI."""
    import uuid

    result = await db.execute(
        select(Holding)
        .options(joinedload(Holding.asset))
        .join(Holding.portfolio)
        .where(Holding.portfolio.has(user_id=uuid.UUID(user_id)))
        .where(Holding.quantity > 0)
    )
    holdings = result.unique().scalars().all()

    if not holdings:
        return "User has no holdings yet."

    total_invested = sum(h.total_invested for h in holdings)
    current_value = sum(h.current_value for h in holdings)
    total_gain = current_value - total_invested
    gain_pct = (total_gain / total_invested * 100) if total_invested else Decimal(0)

    lines = [
        f"Total Invested: ₹{total_invested:,.2f}",
        f"Current Value: ₹{current_value:,.2f}",
        f"Total Gain/Loss: ₹{total_gain:,.2f} ({gain_pct:+.2f}%)",
        f"Number of Holdings: {len(holdings)}",
        "",
        "Holdings:",
    ]

    for h in sorted(holdings, key=lambda x: x.current_value, reverse=True):
        gain = h.total_gain
        pct = h.total_gain_pct
        lines.append(
            f"- {h.asset.name} ({h.asset.type.value}): "
            f"Qty {h.quantity}, Invested ₹{h.total_invested:,.2f}, "
            f"Current ₹{h.current_value:,.2f}, "
            f"Gain ₹{gain:,.2f} ({pct:+.2f}%)"
        )

    return "\n".join(lines)


async def get_ai_response(
    user_id: str,
    message: str,
    history: list[tuple[str, str]],
    db: AsyncSession,
) -> dict:
    """Get AI response with portfolio context."""
    if not settings.anthropic_api_key:
        return {
            "content": "AI assistant is not configured. Please add your Anthropic API key in settings.",
            "metadata": {"error": "no_api_key"},
        }

    import anthropic

    portfolio_context = await _build_portfolio_context(user_id, db)
    system = SYSTEM_PROMPT.format(portfolio_context=portfolio_context)

    messages = []
    for role, content in history[-20:]:  # Last 20 messages for context
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    return {
        "content": response.content[0].text,
        "metadata": {
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        },
    }
