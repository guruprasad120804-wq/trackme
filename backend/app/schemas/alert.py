from decimal import Decimal
from pydantic import BaseModel


class CreateAlertRequest(BaseModel):
    name: str
    asset_id: str | None = None
    condition: str
    threshold: Decimal | None = None
    channels: list[str] = ["push"]
    is_recurring: bool = False
    rule_json: dict | None = None


class AlertResponse(BaseModel):
    id: str
    name: str
    asset_id: str | None
    asset_name: str | None
    condition: str
    threshold: Decimal | None
    channels: list[str]
    is_active: bool
    is_recurring: bool
    last_triggered: str | None
    created_at: str


class AlertHistoryResponse(BaseModel):
    id: str
    alert_name: str
    triggered_at: str
    value_at_trigger: Decimal | None
    channel_used: str | None
    message: str | None
