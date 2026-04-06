"""Dhan adapter — credentials-based auth with access-token header.

Auth: User generates access token from web.dhan.co → pastes into our app.
Holdings: GET /v2/holdings with access-token header (not Bearer).
Docs: https://dhanhq.co/docs/v2/
"""
import json
from decimal import Decimal

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class DhanAdapter(BrokerAdapter):
    broker_name = "Dhan"
    auth_type = "credentials_form"  # User pastes access token from Dhan dashboard

    HOLDINGS_URL = "https://api.dhan.co/v2/holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.dhan_client_id)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError("Dhan uses access token from dashboard, not OAuth redirect")

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        """For Dhan, 'code' is a JSON string with access_token from the user."""
        creds = json.loads(code)
        access_token = creds.get("access_token", "")
        if not access_token:
            raise ValueError("Access token is required")

        # Verify the token works by making a test API call
        s = get_settings()
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={
                    "access-token": access_token,
                    "client-id": s.dhan_client_id,
                    "Content-Type": "application/json",
                },
            )
            # If we get 401/403, token is invalid
            if resp.status_code in (401, 403):
                raise ValueError("Invalid access token. Generate a new one from web.dhan.co")

        return {
            "access_token": access_token,
            "refresh_token": None,
            "expires_in": 86400,  # Dhan tokens valid for 24 hours
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        s = get_settings()
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={
                    "access-token": access_token,
                    "client-id": s.dhan_client_id,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()
            data = raw if isinstance(raw, list) else raw.get("data", [])

        holdings = []
        for h in data:
            qty = int(h.get("totalQty", h.get("quantity", 0)) or 0)
            if qty <= 0:
                continue
            holdings.append(NormalizedHolding(
                symbol=h.get("tradingSymbol", ""),
                name=h.get("tradingSymbol", ""),
                isin=h.get("isin", None),
                exchange=h.get("exchange", "NSE"),
                quantity=Decimal(str(qty)),
                avg_price=Decimal(str(h.get("avgCostPrice", 0))),
                current_price=Decimal(str(h.get("lastTradedPrice", 0))),
                pnl=Decimal(str(h.get("unrealizedProfit", 0))),
            ))
        return holdings
