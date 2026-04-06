"""MF aggregator portfolio data import service.

Follows the same find-or-create pattern as cas_parser.py for
Asset, FundHouse, Scheme, Folio, Holding, and Transaction records.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, TransactionType
from app.models.mutual_fund import FundHouse, Scheme, Folio


# Aggregator transaction type mapping (same codes as casparser)
TRANSACTION_TYPE_MAP = {
    "PURCHASE": TransactionType.BUY,
    "PURCHASE_SIP": TransactionType.SIP,
    "REDEMPTION": TransactionType.REDEMPTION,
    "SWITCH_IN": TransactionType.SWITCH_IN,
    "SWITCH_OUT": TransactionType.SWITCH_OUT,
    "DIVIDEND_PAYOUT": TransactionType.DIVIDEND,
    "DIVIDEND_REINVESTMENT": TransactionType.DIVIDEND_REINVEST,
    "SEGREGATION": TransactionType.OTHER,
    "STAMP_DUTY_TAX": TransactionType.STAMP_DUTY,
    "TDS_TAX": TransactionType.TDS,
    "STT_TAX": TransactionType.STT,
    "MISC": TransactionType.OTHER,
}


async def import_mf_portfolio(
    user_id: str,
    portfolio_data: dict,
    db: AsyncSession,
) -> dict:
    """Import mutual fund portfolio data from the aggregator API response.

    The portfolio_data format matches the aggregator's response — same
    structure as casparser dict output (folios → schemes → transactions).
    """
    uid = uuid.UUID(user_id)

    # Get or create default portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == uid, Portfolio.is_default.is_(True))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=uid, name="My Portfolio", is_default=True)
        db.add(portfolio)
        await db.flush()

    stats = {
        "schemes_added": 0,
        "transactions_added": 0,
        "folios_added": 0,
        "holdings_updated": 0,
        "errors": [],
    }

    for folio_data in portfolio_data.get("folios", []):
        folio_number = str(folio_data.get("folio", "")).strip()

        for scheme_data in folio_data.get("schemes", []):
            try:
                amfi_code = str(scheme_data.get("amfi", "")).strip() or None
                isin = scheme_data.get("isin", "").strip() or None
                scheme_name = scheme_data.get("scheme", "Unknown Scheme")

                # --- Find or create FundHouse ---
                amc_name = folio_data.get("amc", "Unknown AMC")
                result = await db.execute(select(FundHouse).where(FundHouse.name == amc_name))
                fund_house = result.scalar_one_or_none()
                if not fund_house:
                    fund_house = FundHouse(name=amc_name)
                    db.add(fund_house)
                    await db.flush()

                # --- Find or create Asset (by amfi_code, then isin) ---
                asset = None
                if amfi_code:
                    result = await db.execute(select(Asset).where(Asset.amfi_code == amfi_code))
                    asset = result.scalar_one_or_none()
                if not asset and isin:
                    result = await db.execute(select(Asset).where(Asset.isin == isin))
                    asset = result.scalar_one_or_none()

                if not asset:
                    asset = Asset(
                        type=AssetType.MUTUAL_FUND,
                        name=scheme_name,
                        isin=isin,
                        amfi_code=amfi_code,
                    )
                    db.add(asset)
                    await db.flush()
                    stats["schemes_added"] += 1

                # --- Find or create Scheme ---
                result = await db.execute(select(Scheme).where(Scheme.asset_id == asset.id))
                scheme = result.scalar_one_or_none()
                if not scheme:
                    scheme = Scheme(
                        asset_id=asset.id,
                        fund_house_id=fund_house.id,
                        category=scheme_data.get("type", ""),
                        rta=scheme_data.get("rta", ""),
                        rta_code=scheme_data.get("rta_code", ""),
                    )
                    db.add(scheme)
                    await db.flush()

                # --- Find or create Folio ---
                result = await db.execute(
                    select(Folio).where(Folio.user_id == uid, Folio.folio_number == folio_number)
                )
                folio = result.scalar_one_or_none()
                if not folio:
                    folio = Folio(
                        user_id=uid,
                        fund_house_id=fund_house.id,
                        folio_number=folio_number,
                        pan=folio_data.get("pan", ""),
                    )
                    db.add(folio)
                    await db.flush()
                    stats["folios_added"] += 1

                # --- Find or create Holding ---
                result = await db.execute(
                    select(Holding).where(
                        Holding.portfolio_id == portfolio.id,
                        Holding.asset_id == asset.id,
                        Holding.folio_number == folio_number,
                    )
                )
                holding = result.scalar_one_or_none()
                if not holding:
                    holding = Holding(
                        portfolio_id=portfolio.id,
                        asset_id=asset.id,
                        folio_number=folio_number,
                    )
                    db.add(holding)
                    await db.flush()

                # --- Update holding from valuation data (authoritative) ---
                valuation = scheme_data.get("valuation", {})
                if valuation:
                    nav = valuation.get("nav", 0)
                    value = valuation.get("value", 0)
                    cost = valuation.get("cost", 0)

                    if nav and nav > 0:
                        holding.quantity = Decimal(str(value)) / Decimal(str(nav))
                    holding.current_price = Decimal(str(nav))
                    holding.current_value = Decimal(str(value))
                    if cost:
                        holding.total_invested = Decimal(str(cost))
                    if holding.total_invested and holding.total_invested > 0:
                        holding.total_gain = holding.current_value - holding.total_invested
                        holding.total_gain_pct = (
                            holding.total_gain / holding.total_invested * 100
                        )
                    stats["holdings_updated"] += 1

                # --- Import transactions (skip dupes via constraint) ---
                for txn_data in scheme_data.get("transactions", []):
                    txn_type_str = txn_data.get("type", "MISC")
                    txn_type = TRANSACTION_TYPE_MAP.get(txn_type_str, TransactionType.OTHER)

                    amount = Decimal(str(txn_data.get("amount", 0)))
                    units = Decimal(str(txn_data.get("units", 0)))
                    nav = Decimal(str(txn_data.get("nav", 0)))
                    txn_date = txn_data.get("date")

                    if isinstance(txn_date, str):
                        txn_date = date.fromisoformat(txn_date)

                    txn = Transaction(
                        holding_id=holding.id,
                        type=txn_type,
                        trade_date=txn_date or date.today(),
                        quantity=abs(units),
                        price=nav,
                        amount=abs(amount),
                        nav=nav,
                        stamp_duty=Decimal(str(txn_data.get("stamp_duty", 0))),
                        source="mf_aggregator",
                    )

                    try:
                        async with db.begin_nested():
                            db.add(txn)
                            await db.flush()
                        stats["transactions_added"] += 1
                    except Exception:
                        pass  # Savepoint rolled back; session still usable

            except Exception as e:
                stats["errors"].append(str(e))

    await db.commit()
    return stats
