"""5paisa adapter — OAuth redirect with 30-second token exchange window.

Auth: OAuth redirect → request token (valid 30s) → exchange for access token.
Holdings: POST /V3/Holding with Bearer token.
Docs: https://www.5paisa.com/developerapi/overview
"""
from decimal import Decimal
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.brokers.base import BrokerAdapter, NormalizedHolding


class FivePaisaAdapter(BrokerAdapter):
    broker_name = "5paisa"
    auth_type = "oauth"

    AUTH_URL = "https://dev-openapi.5paisa.com/WebVendorLogin/VLogin/Index"
    TOKEN_URL = "https://dev-openapi.5paisa.com/connect/token"
    HOLDINGS_URL = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V3/Holding"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.five_paisa_vendor_key and s.five_paisa_encryption_key)

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = {
            "VendorKey": s.five_paisa_vendor_key,
            "ResponseURL": redirect_uri,
            "State": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with self._client() as client:
            resp = await client.post(self.TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": s.five_paisa_vendor_key,
                "client_secret": s.five_paisa_encryption_key,
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
            resp = await client.post(
                self.HOLDINGS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"head": {"key": get_settings().five_paisa_vendor_key}, "body": {}},
            )
            resp.raise_for_status()
            data = resp.json().get("body", {}).get("Data", [])

        holdings = []
        for h in data:
            qty = int(h.get("Quantity", 0) or 0)
            if qty <= 0:
                continue
            holdings.append(NormalizedHolding(
                symbol=h.get("ScripName", ""),
                name=h.get("ScripName", ""),
                isin=h.get("ISIN", None),
                exchange=h.get("Exch", "NSE"),
                quantity=Decimal(str(qty)),
                avg_price=Decimal(str(h.get("BuyAvgRate", 0))),
                current_price=Decimal(str(h.get("CurrentPrice", 0))),
                pnl=Decimal(str(h.get("BookedPL", 0))),
            ))
        return holdings
