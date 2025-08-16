from fastapi import FastAPI

from .middleware import register_middlewares
from .routers import register_routers
from .settings.config import settings


class App(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = settings.PROJECT_NAME
        self.description = "API for the application"
        self.docs_url = "/docs"
        self.redoc_url = "/redoc"
        self.openapi_url = "/openapi.json"
        register_middlewares(self)
        register_routers(self)


app = App(
    version="0.1.0",
)
