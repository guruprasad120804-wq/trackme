from fastapi import APIRouter

from app.api.v1 import auth, dashboard, portfolio, transactions, alerts, chat, subscription, import_data, settings

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(chat.router, prefix="/chat", tags=["ai-chat"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
api_router.include_router(import_data.router, prefix="/import", tags=["import"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
