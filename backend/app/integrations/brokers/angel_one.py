"""Angel One SmartAPI adapter — credentials-based auth (no OAuth redirect).

Auth: API key + client code + PIN + TOTP → session token.
Holdings: GET /rest/secure/angelbroking/portfolio/v1/getHolding.
Docs: https://smartapi.angelbroking.com/
"""
from decimal import Decimal

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class AngelOneAdapter(BrokerAdapter):
    broker_name = "Angel One"
    auth_type = "credentials_form"  # No OAuth redirect — uses form input

    LOGIN_URL = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
    HOLDINGS_URL = "https://apiconnect.angelone.in/rest/secure/angelbroking/portfolio/v1/getHolding"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.angel_one_api_key)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError("Angel One uses credentials form, not OAuth redirect")

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        """For Angel One, 'code' is a JSON string with client_code, pin, totp."""
        import json
        s = get_settings()
        creds = json.loads(code)

        async with self._client() as client:
            resp = await client.post(
                self.LOGIN_URL,
                json={
                    "clientcode": creds["client_code"],
                    "password": creds["pin"],
                    "totp": creds["totp"],
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-UserType": "USER",
                    "X-SourceID": "WEB",
                    "X-ClientLocalIP": "127.0.0.1",
                    "X-ClientPublicIP": "127.0.0.1",
                    "X-MACAddress": "00:00:00:00:00:00",
                    "X-PrivateKey": s.angel_one_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

        return {
            "access_token": data.get("jwtToken", ""),
            "refresh_token": data.get("refreshToken"),
            "expires_in": 86400,
            "extra": {"feed_token": data.get("feedToken")},
        }

    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        s = get_settings()
        async with self._client() as client:
            resp = await client.get(
                self.HOLDINGS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-UserType": "USER",
                    "X-SourceID": "WEB",
                    "X-ClientLocalIP": "127.0.0.1",
                    "X-ClientPublicIP": "127.0.0.1",
                    "X-MACAddress": "00:00:00:00:00:00",
                    "X-PrivateKey": s.angel_one_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", []) or []

        holdings = []
        for h in data:
            qty = int(h.get("quantity", 0) or 0)
            if qty <= 0:
                continue
            holdings.append(NormalizedHolding(
                symbol=h.get("tradingsymbol", ""),
                name=h.get("tradingsymbol", ""),
                isin=h.get("isin", None),
                exchange=h.get("exchange", "NSE"),
                quantity=Decimal(str(qty)),
                avg_price=Decimal(str(h.get("averageprice", 0))),
                current_price=Decimal(str(h.get("ltp", 0))),
                pnl=Decimal(str(h.get("profitandloss", 0))),
            ))
        return holdings
