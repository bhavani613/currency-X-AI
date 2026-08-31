from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.payments import router as payments_router
from app.api.razorpay_pay import router as razorpay_router
from app.api.advisor import router as advisor_router
from app.database.connection import init_db


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

# CORS configuration for the React frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

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


@app.get("/")
def root():
    return {"message": "CurrencyX AI Backend is running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "CurrencyX AI API",
    }


@app.get("/api/v1/info")
def info():
    return {
        "project": "CurrencyX AI",
        "description": "AI-powered cross-border payment intelligence API",
        "version": "1.0.0",
    }