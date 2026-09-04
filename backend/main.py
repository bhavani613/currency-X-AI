from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.payments import router as payments_router
from app.api.razorpay_pay import router as razorpay_router
from app.api.advisor import router as advisor_router
from app.api.auth import router as auth_router
from app.api.revenue_recovery import router as recovery_router
from app.database.connection import init_db, engine
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""
    await init_db()
    yield


app = FastAPI(
    title="CurrencyX AI API",
    description="AI-powered cross-border payment intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for the React frontend — explicit allowlist loaded
# from the CORS_ORIGINS environment variable (see app/config.py).
origins = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(payments_router, prefix="/api/v1")
app.include_router(razorpay_router, prefix="/api/v1")
app.include_router(advisor_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(recovery_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "CurrencyX AI Backend is running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "CurrencyX AI API",
    }


@app.get("/ready")
async def ready():
    """Readiness probe — reports whether the database is reachable.

    Lightweight (single ``SELECT 1`` with a short timeout) and unauthenticated
    by design so load balancers / the frontend status indicator can call it.
    """
    if engine is None:
        return {"status": "degraded", "database": "not_configured"}
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3)
        return {"status": "ready", "database": "connected"}
    except Exception:  # noqa: BLE001 — readiness must never raise
        return {"status": "degraded", "database": "unavailable"}


@app.get("/api/v1/info")
def info():
    return {
        "project": "CurrencyX AI",
        "description": "AI-powered cross-border payment intelligence API",
        "version": "1.0.0",
    }