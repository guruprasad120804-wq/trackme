"""Zerodha Kite Connect adapter.

Auth: api_key + request_token → SHA256 checksum → access_token (valid 1 day, no refresh).
Holdings: GET /portfolio/holdings with token header.
Docs: https://kite.trade/docs/connect/v3/
"""
import hashlib
from decimal import Decimal
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class ZerodhaAdapter(BrokerAdapter):
    broker_name = "Zerodha"
    auth_type = "oauth"

    AUTH_URL = "https://kite.zerodha.com/connect/login"
    TOKEN_URL = "https://api.kite.trade/session/token"
    HOLDINGS_URL = "https://api.kite.trade/portfolio/holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.zerodha_api_key and s.zerodha_api_secret)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = {
            "v": "3",
            "api_key": s.zerodha_api_key,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        """Zerodha uses request_token + checksum instead of standard OAuth.

        checksum = SHA256(api_key + request_token + api_secret)
        """
        s = get_settings()
        checksum = hashlib.sha256(
            f"{s.zerodha_api_key}{code}{s.zerodha_api_secret}".encode()
        ).hexdigest()

        async with self._client() as client:
            resp = await client.post(self.TOKEN_URL, data={
                "api_key": s.zerodha_api_key,
                "request_token": code,
                "checksum": checksum,
            })
            resp.raise_for_status()
            data = resp.json().get("data", {})

        return {
            "access_token": data.get("access_token", ""),
            "refresh_token": None,  # Zerodha doesn't have refresh tokens
            "expires_in": 86400,  # Token valid for 1 trading day
            "extra": {"user_id": data.get("user_id")},
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        s = get_settings()
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={"Authorization": f"token {s.zerodha_api_key}:{access_token}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])

        holdings = []
        for h in data:
            holdings.append(NormalizedHolding(
                symbol=h.get("tradingsymbol", ""),
                name=h.get("tradingsymbol", ""),
                isin=h.get("isin", None),
                exchange=h.get("exchange", "NSE"),
                quantity=Decimal(str(h.get("quantity", 0))),
                avg_price=Decimal(str(h.get("average_price", 0))),
                current_price=Decimal(str(h.get("last_price", 0))),
                pnl=Decimal(str(h.get("pnl", 0))),
            ))
        return holdings
