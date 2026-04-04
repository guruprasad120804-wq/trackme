"""TrackMe — Next-generation portfolio tracking & financial intelligence."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title="TrackMe API",
    description="Portfolio tracking & financial intelligence platform",
    version="2.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from app.api.v1.router import api_router
from app.integrations.whatsapp.webhook import router as whatsapp_router

app.include_router(api_router)
app.include_router(whatsapp_router, tags=["whatsapp"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
