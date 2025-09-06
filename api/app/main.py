import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .middleware import register_middlewares
from .routers import register_routers
from .settings.config import settings
from .tasks.consumer import consume_forever
from .tasks.queue import queue_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await queue_manager.connect()
    stop_event = asyncio.Event()
    consumer_task = asyncio.create_task(
        consume_forever(queue_manager, stop_event),
    )
    _app.state.consumer_stop_event = stop_event
    _app.state.consumer_task = consumer_task
    try:
        yield
    finally:
        print("Shutting down consumer task")
        stop_event.set()
        try:
            print("Waiting for consumer task to finish")
            await asyncio.wait_for(consumer_task, timeout=5.0)
        except asyncio.TimeoutError:
            print("Timeout in consumer task")
            consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await consumer_task
        except Exception:
            print("Exception in consumer task")
            consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                print("Exception in consumer task")
                await consumer_task

        # Fecha a conexão com RabbitMQ
        with suppress(asyncio.TimeoutError, Exception):
            await asyncio.wait_for(queue_manager.close(), timeout=3.0)


class App(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, lifespan=lifespan, **kwargs)
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
