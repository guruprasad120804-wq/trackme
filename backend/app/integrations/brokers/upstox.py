"""Upstox adapter — standard OAuth2 with refresh tokens.

Auth: Standard OAuth2 redirect flow.
Holdings: GET /v2/portfolio/long-term-holdings with Bearer token.
Docs: https://upstox.com/developer/api-documentation/
"""
from decimal import Decimal
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class UpstoxAdapter(BrokerAdapter):
    broker_name = "Upstox"
    auth_type = "oauth"

    AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
    TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
    HOLDINGS_URL = "https://api.upstox.com/v2/portfolio/long-term-holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.upstox_client_id and s.upstox_client_secret)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = {
            "response_type": "code",
            "client_id": s.upstox_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with self._client() as client:
            resp = await client.post(self.TOKEN_URL, data={
                "code": code,
                "client_id": s.upstox_client_id,
                "client_secret": s.upstox_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            data = resp.json()

        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])

        holdings = []
        for h in data:
            holdings.append(NormalizedHolding(
                symbol=h.get("trading_symbol", h.get("tradingsymbol", "")),
                name=h.get("company_name", h.get("trading_symbol", "")),
                isin=h.get("isin", None),
                exchange=h.get("exchange", "NSE"),
                quantity=Decimal(str(h.get("quantity", 0))),
                avg_price=Decimal(str(h.get("average_price", 0))),
                current_price=Decimal(str(h.get("last_price", 0))),
                pnl=Decimal(str(h.get("pnl", 0))),
            ))
        return holdings
