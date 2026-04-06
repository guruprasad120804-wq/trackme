"""Fyers adapter — OAuth2 with appIdHash authentication.

Auth: appIdHash = SHA256(app_id:secret_id), used in token exchange.
Holdings: GET /api/v3/holdings with Authorization: app_id:access_token.
Docs: https://myapi.fyers.in/docsv3
"""
import hashlib
from decimal import Decimal
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class FyersAdapter(BrokerAdapter):
    broker_name = "Fyers"
    auth_type = "oauth"

    AUTH_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"
    TOKEN_URL = "https://api-t1.fyers.in/api/v3/validate-authcode"
    HOLDINGS_URL = "https://api-t1.fyers.in/api/v3/holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.fyers_app_id and s.fyers_secret_id)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = {
            "client_id": s.fyers_app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        app_id_hash = hashlib.sha256(
            f"{s.fyers_app_id}:{s.fyers_secret_id}".encode()
        ).hexdigest()

        async with self._client() as client:
            resp = await client.post(self.TOKEN_URL, json={
                "grant_type": "authorization_code",
                "appIdHash": app_id_hash,
                "code": code,
            })
            resp.raise_for_status()
            data = resp.json()

        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        s = get_settings()
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={"Authorization": f"{s.fyers_app_id}:{access_token}"},
            )
            resp.raise_for_status()
            data = resp.json().get("holdings", [])

        holdings = []
        for h in data:
            holdings.append(NormalizedHolding(
                symbol=h.get("symbol", "").split("-")[0] if "-" in h.get("symbol", "") else h.get("symbol", ""),
                name=h.get("symbol", ""),
                isin=h.get("isin", None),
                exchange="NSE" if ":NSE" in h.get("symbol", "") else "BSE",
                quantity=Decimal(str(h.get("quantity", 0))),
                avg_price=Decimal(str(h.get("costPrice", 0))),
                current_price=Decimal(str(h.get("ltp", 0))),
                pnl=Decimal(str(h.get("pl", 0))),
            ))
        return holdings
