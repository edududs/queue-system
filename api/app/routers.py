from fastapi import FastAPI

from .auth.controller import router as auth_router
from .tasks.controller import router as tasks_router
from .users.controller import router as users_router


def register_routers(app: FastAPI):
    """Register all routers to the FastAPI app."""
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(tasks_router)
