from decimal import Decimal
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_invested: Decimal
    current_value: Decimal
    total_gain: Decimal
    total_gain_pct: Decimal
    day_change: Decimal
    day_change_pct: Decimal
    xirr: Decimal | None
    total_holdings: int
    asset_type_breakdown: list["AssetTypeBreakdown"]


class AssetTypeBreakdown(BaseModel):
    type: str
    invested: Decimal
    current_value: Decimal
    gain: Decimal
    gain_pct: Decimal
    allocation_pct: Decimal
    count: int


class HoldingSummary(BaseModel):
    id: str
    asset_name: str
    asset_type: str
    symbol: str | None
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal
    invested: Decimal
    current_value: Decimal
    gain: Decimal
    gain_pct: Decimal
    day_change: Decimal
    day_change_pct: Decimal
    xirr: Decimal | None
    allocation_pct: Decimal


class PerformancePoint(BaseModel):
    date: str
    invested: Decimal
    value: Decimal


class TopMover(BaseModel):
    asset_name: str
    symbol: str | None
    change_pct: Decimal
    change_value: Decimal
    direction: str  # "up" or "down"
