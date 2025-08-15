from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import register_routers
from .settings.config import settings

app = FastAPI(
    title="API",
    description="API for the application",
    version="0.1.0",
    contact={
        "name": "API Support",
        "url": "https://www.google.com",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)
