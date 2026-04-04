"""CAS PDF parsing and data import service.
Ported and enhanced from reference project — handles CAMS & KFintech CAS formats.
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


# Mapping casparser transaction types to our enum
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


async def parse_and_import_cas(
    user_id: str,
    pdf_path: str,
    password: str,
    db: AsyncSession,
) -> dict:
    """Parse a CAS PDF and import all data into the database."""
    import casparser

    uid = uuid.UUID(user_id)
    data = casparser.read_cas_pdf(pdf_path, password, output="dict")

    # Get or create default portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == uid, Portfolio.is_default.is_(True))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=uid, name="My Portfolio", is_default=True)
        db.add(portfolio)
        await db.flush()

    stats = {"schemes_added": 0, "transactions_added": 0, "folios_added": 0, "errors": []}

    for folio_data in data.get("folios", []):
        folio_number = folio_data.get("folio", "").strip()

        for scheme_data in folio_data.get("schemes", []):
            try:
                amfi_code = str(scheme_data.get("amfi", "")).strip() or None
                isin = scheme_data.get("isin", "").strip() or None
                scheme_name = scheme_data.get("scheme", "Unknown Scheme")

                # Find or create fund house
                amc_name = folio_data.get("amc", "Unknown AMC")
                result = await db.execute(select(FundHouse).where(FundHouse.name == amc_name))
                fund_house = result.scalar_one_or_none()
                if not fund_house:
                    fund_house = FundHouse(name=amc_name)
                    db.add(fund_house)
                    await db.flush()

                # Find or create asset
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

                # Find or create scheme
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

                # Find or create folio
                result = await db.execute(
                    select(Folio).where(Folio.user_id == uid, Folio.folio_number == folio_number)
                )
                folio = result.scalar_one_or_none()
                if not folio:
                    folio = Folio(
                        user_id=uid,
                        fund_house_id=fund_house.id,
                        folio_number=folio_number,
                        pan=folio_data.get("PAN", ""),
                    )
                    db.add(folio)
                    await db.flush()
                    stats["folios_added"] += 1

                # Find or create holding
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

                # Update holding with valuation data
                valuation = scheme_data.get("valuation", {})
                if valuation:
                    holding.quantity = Decimal(str(valuation.get("value", 0) / valuation.get("nav", 1))) if valuation.get("nav") else Decimal(0)
                    holding.current_price = Decimal(str(valuation.get("nav", 0)))
                    holding.current_value = Decimal(str(valuation.get("value", 0)))
                    cost = valuation.get("cost", 0)
                    if cost:
                        holding.total_invested = Decimal(str(cost))

                # Import transactions
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
                        source="cas_import",
                    )

                    # Use merge to handle duplicates gracefully
                    try:
                        db.add(txn)
                        await db.flush()
                        stats["transactions_added"] += 1
                    except Exception:
                        await db.rollback()

            except Exception as e:
                stats["errors"].append(str(e))

    await db.commit()
    return stats
