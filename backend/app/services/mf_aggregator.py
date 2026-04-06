"""MF Aggregator API client for PAN + OTP based mutual fund import."""
import httpx
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()


class MFAggregatorClient:
    """Client for communicating with the MF aggregator API (Setu/Perfios-style)."""

    def __init__(self):
        self.base_url = settings.mf_base_url.rstrip("/")
        self.api_key = settings.mf_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def start_session(self, pan: str) -> dict:
        """Create a new session and trigger OTP delivery to the user.

        POST {base_url}/sessions
        Body: {"pan": "ABCDE1234F"}
        Returns: {"session_id": "...", "message": "OTP sent to registered mobile"}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/sessions",
                    json={"pan": pan},
                    headers=self.headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                raise HTTPException(status_code=502, detail="Aggregator service timed out")
            except httpx.HTTPStatusError as e:
                detail = e.response.json().get("message", "Failed to start session") if e.response.content else "Failed to start session"
                raise HTTPException(status_code=e.response.status_code, detail=detail)
            except httpx.HTTPError:
                raise HTTPException(status_code=502, detail="Aggregator service unavailable")

    async def verify_otp(self, session_id: str, otp: str) -> dict:
        """Verify OTP and obtain a persistent consent_id.

        POST {base_url}/sessions/{session_id}/verify
        Body: {"otp": "123456"}
        Returns: {"consent_id": "...", "status": "verified"}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/sessions/{session_id}/verify",
                    json={"otp": otp},
                    headers=self.headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                raise HTTPException(status_code=502, detail="Aggregator service timed out")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    detail = e.response.json().get("message", "Invalid OTP") if e.response.content else "Invalid OTP"
                    raise HTTPException(status_code=400, detail=detail)
                detail = e.response.json().get("message", "Verification failed") if e.response.content else "Verification failed"
                raise HTTPException(status_code=e.response.status_code, detail=detail)
            except httpx.HTTPError:
                raise HTTPException(status_code=502, detail="Aggregator service unavailable")

    async def fetch_portfolio(self, consent_id: str) -> dict:
        """Fetch the user's mutual fund portfolio using a valid consent.

        GET {base_url}/portfolio/{consent_id}
        Returns: {
            "folios": [{
                "amc": "HDFC AMC",
                "folio": "1234567890",
                "pan": "ABCDE1234F",
                "schemes": [{
                    "scheme": "HDFC Flexi Cap Fund",
                    "amfi": "100123",
                    "isin": "INF...",
                    "type": "Equity",
                    "rta": "CAMS",
                    "rta_code": "...",
                    "valuation": {"nav": 45.67, "value": 125000, "cost": 100000},
                    "transactions": [{
                        "date": "2024-01-15",
                        "type": "PURCHASE_SIP",
                        "amount": 5000,
                        "units": 109.5,
                        "nav": 45.66,
                        "stamp_duty": 0.25
                    }]
                }]
            }]
        }
        """
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/portfolio/{consent_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                raise HTTPException(status_code=502, detail="Aggregator service timed out — portfolio fetch may take longer")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 410:
                    raise HTTPException(status_code=400, detail="Consent expired. Please reconnect with PAN + OTP.")
                detail = e.response.json().get("message", "Failed to fetch portfolio") if e.response.content else "Failed to fetch portfolio"
                raise HTTPException(status_code=e.response.status_code, detail=detail)
            except httpx.HTTPError:
                raise HTTPException(status_code=502, detail="Aggregator service unavailable")


# Singleton instance
aggregator_client = MFAggregatorClient()
