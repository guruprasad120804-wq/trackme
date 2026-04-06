"""Dhan adapter — OAuth/partner flow with access-token header.

Auth: Partner OAuth flow or manual token generation.
Holdings: GET /v2/holdings with access-token header (not Bearer).
Docs: https://dhanhq.co/docs/v2/
"""
from decimal import Decimal
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class DhanAdapter(BrokerAdapter):
    broker_name = "Dhan"
    auth_type = "oauth"

    AUTH_URL = "https://api.dhan.co/partner/authorize"
    TOKEN_URL = "https://api.dhan.co/partner/token"
    HOLDINGS_URL = "https://api.dhan.co/v2/holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.dhan_client_id and s.dhan_secret)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = {
            "client_id": s.dhan_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with self._client() as client:
            resp = await client.post(self.TOKEN_URL, json={
                "client_id": s.dhan_client_id,
                "client_secret": s.dhan_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            })
            resp.raise_for_status()
            data = resp.json()

        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 86400),
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={"access-token": access_token, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])

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
