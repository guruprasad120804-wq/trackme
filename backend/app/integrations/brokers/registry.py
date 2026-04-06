"""Broker adapter registry — maps BrokerType to adapter classes."""
from app.models.broker import BrokerType
from app.integrations.brokers.base import BrokerAdapter


_ADAPTER_MAP: dict[BrokerType, type[BrokerAdapter]] = {}
_instances: dict[BrokerType, BrokerAdapter] = {}


def _ensure_registered():
    if _ADAPTER_MAP:
        return
    from app.integrations.brokers.zerodha import ZerodhaAdapter
    from app.integrations.brokers.upstox import UpstoxAdapter
    from app.integrations.brokers.fyers import FyersAdapter
    from app.integrations.brokers.angel_one import AngelOneAdapter
    from app.integrations.brokers.five_paisa import FivePaisaAdapter
    from app.integrations.brokers.dhan import DhanAdapter

    _ADAPTER_MAP.update({
        BrokerType.ZERODHA: ZerodhaAdapter,
        BrokerType.UPSTOX: UpstoxAdapter,
        BrokerType.FYERS: FyersAdapter,
        BrokerType.ANGEL_ONE: AngelOneAdapter,
        BrokerType.FIVE_PAISA: FivePaisaAdapter,
        BrokerType.DHAN: DhanAdapter,
    })


def get_adapter(broker_type: BrokerType) -> BrokerAdapter:
    """Get a singleton adapter instance for the given broker type."""
    _ensure_registered()
    if broker_type not in _ADAPTER_MAP:
        raise ValueError(f"No adapter for broker type: {broker_type}")
    if broker_type not in _instances:
        _instances[broker_type] = _ADAPTER_MAP[broker_type]()
    return _instances[broker_type]


def get_configured_broker_types() -> list[BrokerType]:
    """Return broker types that have API credentials configured."""
    _ensure_registered()
    return [bt for bt, cls in _ADAPTER_MAP.items() if cls().is_configured()]
