from decimal import Decimal
from pydantic import BaseModel


class PortfolioResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    total_invested: Decimal
    current_value: Decimal
    total_gain: Decimal
    total_gain_pct: Decimal
    holdings_count: int

    model_config = {"from_attributes": True}


class CreatePortfolioRequest(BaseModel):
    name: str


class HoldingDetail(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    asset_type: str
    symbol: str | None
    folio_number: str | None
    quantity: Decimal
    avg_cost: Decimal
    total_invested: Decimal
    current_price: Decimal
    current_value: Decimal
    day_change: Decimal
    day_change_pct: Decimal
    total_gain: Decimal
    total_gain_pct: Decimal
    xirr: Decimal | None
    transactions_count: int


class TransactionResponse(BaseModel):
    id: str
    holding_id: str
    asset_name: str
    type: str
    trade_date: str
    quantity: Decimal
    price: Decimal
    amount: Decimal
    charges: Decimal
    source: str | None
    notes: str | None


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ManualTransactionRequest(BaseModel):
    portfolio_id: str
    asset_type: str
    asset_name: str
    symbol: str | None = None
    isin: str | None = None
    transaction_type: str
    trade_date: str
    quantity: Decimal
    price: Decimal
    amount: Decimal | None = None
    charges: Decimal = Decimal(0)
    folio_number: str | None = None
    notes: str | None = None
