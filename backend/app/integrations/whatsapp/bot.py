"""WhatsApp bot command handler."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import async_session
from app.models.whatsapp import WhatsAppConfig
from app.models.holding import Holding
from app.integrations.whatsapp.client import send_whatsapp_message


HELP_TEXT = """📊 *TrackMe Bot Commands*

/portfolio - View portfolio summary
/holdings - List all holdings
/alerts - View active alerts
/value - Get current portfolio value
/help - Show this help message

Just type your question and I'll try to answer using AI!"""


async def handle_whatsapp_message(phone: str, text: str):
    """Route incoming WhatsApp messages to appropriate handlers."""
    # Find user by phone number
    async with async_session() as db:
        result = await db.execute(
            select(WhatsAppConfig).where(
                WhatsAppConfig.phone_number == phone,
                WhatsAppConfig.is_verified.is_(True),
                WhatsAppConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            await send_whatsapp_message(phone, "Your phone number is not linked to a TrackMe account. Please set up WhatsApp integration in the app.")
            return

        user_id = str(config.user_id)
        command = text.strip().lower()

        if command in ("/help", "help", "hi", "hello"):
            await send_whatsapp_message(phone, HELP_TEXT)

        elif command in ("/portfolio", "/value", "portfolio", "value"):
            await _send_portfolio_summary(phone, user_id, db)

        elif command in ("/holdings", "holdings"):
            await _send_holdings_list(phone, user_id, db)

        else:
            # Use AI for free-form questions
            from app.services.ai_assistant import get_ai_response
            response = await get_ai_response(
                user_id=user_id,
                message=text,
                history=[],
                db=db,
            )
            # Truncate for WhatsApp (max ~4096 chars)
            content = response["content"][:4000]
            await send_whatsapp_message(phone, content)


async def _send_portfolio_summary(phone: str, user_id: str, db):
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
        await send_whatsapp_message(phone, "📊 Your portfolio is empty. Add investments in the TrackMe app.")
        return

    total_invested = sum(h.total_invested for h in holdings)
    current_value = sum(h.current_value for h in holdings)
    gain = current_value - total_invested
    pct = (gain / total_invested * 100) if total_invested else Decimal(0)
    emoji = "📈" if gain >= 0 else "📉"

    msg = f"""📊 *Portfolio Summary*

💰 Invested: ₹{total_invested:,.0f}
{emoji} Current Value: ₹{current_value:,.0f}
{"🟢" if gain >= 0 else "🔴"} Gain/Loss: ₹{gain:,.0f} ({pct:+.1f}%)
📦 Holdings: {len(holdings)}"""

    await send_whatsapp_message(phone, msg)


async def _send_holdings_list(phone: str, user_id: str, db):
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
        await send_whatsapp_message(phone, "No holdings found.")
        return

    holdings_sorted = sorted(holdings, key=lambda h: h.current_value, reverse=True)
    lines = ["📋 *Your Holdings*\n"]

    for h in holdings_sorted[:15]:  # Limit to 15 for WhatsApp
        emoji = "🟢" if h.total_gain >= 0 else "🔴"
        lines.append(f"{emoji} *{h.asset.name[:30]}*")
        lines.append(f"   ₹{h.current_value:,.0f} ({h.total_gain_pct:+.1f}%)")

    if len(holdings_sorted) > 15:
        lines.append(f"\n_...and {len(holdings_sorted) - 15} more. View all in the app._")

    await send_whatsapp_message(phone, "\n".join(lines))
