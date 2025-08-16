"""Middleware components for the Queue System API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..settings.config import settings


def register_middlewares(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


__all__ = ["register_middlewares"]
