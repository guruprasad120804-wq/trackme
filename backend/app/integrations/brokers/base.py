"""Abstract base class for broker adapters."""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TypedDict

import httpx


class NormalizedHolding(TypedDict):
    symbol: str
    name: str
    isin: str | None
    exchange: str  # NSE / BSE
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal
    pnl: Decimal


class BrokerAdapter(ABC):
    """Base class for all broker integrations."""

    auth_type: str = "oauth"  # "oauth" or "credentials_form"
    broker_name: str = ""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API credentials are set in environment."""
        ...

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate OAuth authorization URL for redirect."""
        ...

    @abstractmethod
    async def exchange_token(self, code: str, redirect_uri: str) -> dict:
        """Exchange auth code for access/refresh tokens.

        Returns dict with keys: access_token, refresh_token (optional),
        expires_in (optional), extra (optional dict for metadata).
        """
        ...

    @abstractmethod
    async def fetch_holdings(self, access_token: str, **kwargs) -> list[NormalizedHolding]:
        """Fetch and normalize holdings from broker API."""
        ...

    def _client(self, timeout: int = 30) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout)
