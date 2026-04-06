"""Dhan adapter — programmatic token generation with client ID + PIN + TOTP.

Auth: User provides Dhan client ID, PIN, and TOTP → we generate access token.
Holdings: GET /v2/holdings with access-token header.
Docs: https://dhanhq.co/docs/v2/
"""
import json
import logging
from decimal import Decimal

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding

logger = logging.getLogger(__name__)


class DhanAdapter(BrokerAdapter):
    broker_name = "Dhan"
    auth_type = "credentials_form"

    LOGIN_URL = "https://api.dhan.co/v2/token"
    HOLDINGS_URL = "https://api.dhan.co/v2/holdings"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.dhan_client_id)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError("Dhan uses programmatic token generation, not OAuth redirect")

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        """Authenticate with Dhan using client ID + PIN + TOTP or direct access token.

        'code' is a JSON string with either:
        - {"dhan_client_id": "...", "pin": "...", "totp": "..."} for programmatic login
        - {"access_token": "..."} for direct token paste
        """
        s = get_settings()
        creds = json.loads(code)

        # If user directly provides an access token, use it
        if creds.get("access_token"):
            access_token = creds["access_token"]
        elif creds.get("dhan_client_id") and creds.get("pin") and creds.get("totp"):
            # Programmatic token generation
            async with self._client() as client:
                # Try Dhan's token generation endpoint
                resp = await client.post(
                    self.LOGIN_URL,
                    json={
                        "dhanClientId": creds["dhan_client_id"],
                        "pin": creds["pin"],
                        "totp": creds["totp"],
                    },
                    headers={
                        "Content-Type": "application/json",
                        "client-id": s.dhan_client_id,
                    },
                )
                if resp.status_code != 200:
                    logger.error(f"Dhan login failed: {resp.status_code} {resp.text}")
                    # Fall back: try alternate endpoint format
                    resp2 = await client.post(
                        "https://api.dhan.co/token",
                        json={
                            "client_id": s.dhan_client_id,
                            "client_secret": s.dhan_secret,
                            "dhan_client_id": creds["dhan_client_id"],
                            "pin": creds["pin"],
                            "totp": creds["totp"],
                            "grant_type": "client_credentials",
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    if resp2.status_code != 200:
                        logger.error(f"Dhan login fallback failed: {resp2.status_code} {resp2.text}")
                        raise ValueError(
                            f"Dhan authentication failed. You can paste your access token directly from web.dhan.co instead."
                        )
                    data = resp2.json()
                    access_token = data.get("access_token") or data.get("data", {}).get("access_token", "")
                else:
                    data = resp.json()
                    access_token = data.get("access_token") or data.get("data", {}).get("access_token", "")
        else:
            raise ValueError("Provide either Dhan Client ID + PIN + TOTP, or an access token")

        if not access_token:
            raise ValueError("No access token received from Dhan")

        # Verify token works
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={
                    "access-token": access_token,
                    "client-id": s.dhan_client_id,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (401, 403):
                raise ValueError("Token verification failed. Try pasting your access token from web.dhan.co")

        return {
            "access_token": access_token,
            "refresh_token": None,
            "expires_in": 86400,
            "extra": {"dhan_client_id": creds.get("dhan_client_id", "")},
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
