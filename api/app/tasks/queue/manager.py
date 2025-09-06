import asyncio
import json
import logging
import uuid
from datetime import timedelta
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
    FieldValue,
)
from aiormq.exceptions import ChannelPreconditionFailed

from ...settings.config import settings

logger = logging.getLogger(__name__)


class QueueManager:
    """Robust RabbitMQ manager using aio-pika.

    Declares topology:
    - Exchange: tasks (direct)
    - Queues:
      * tasks.main (bind: routing_key=tasks.main)
      * tasks.retry (DLX -> tasks, DLK=tasks.main)
      * tasks.dlq   (bind: routing_key=tasks.dlq)
    """

    def __init__(self) -> None:
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._main_queue: Optional[AbstractQueue] = None
        self._lock = asyncio.Lock()

    @property
    def is_ready(self) -> bool:
        """Check if all required components are connected and ready."""
        return all(
            [
                self._connection and not self._connection.is_closed,
                self._channel and not self._channel.is_closed,
                self._exchange,
            ],
        )

    async def _connect_channel(
        self,
        heartbeat: int = 60,
    ) -> AbstractChannel:
        async with asyncio.timeout(15.0):
            connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                heartbeat=heartbeat,
            )
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)
        self._connection = connection
        self._channel = channel
        return self._channel

    async def _declare_exchange(self, channel: AbstractChannel) -> AbstractExchange:
        self._exchange = await channel.declare_exchange(
            settings.RABBITMQ_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )
        return self._exchange

    async def _set_queues(
        self,
        channel: AbstractChannel,
        exchange: AbstractExchange,
    ) -> None:
        # DLQ bound to the same exchange with dedicated routing key
        try:
            q_dlq = await channel.declare_queue(
                settings.RABBITMQ_DLQ,
                durable=True,
            )
        except ChannelPreconditionFailed:
            logger.warning(
                "DLQ exists with different arguments; using passive declaration",
                extra={
                    "queue": settings.RABBITMQ_DLQ,
                    "exchange": settings.RABBITMQ_EXCHANGE,
                },
            )
            q_dlq = await channel.declare_queue(
                settings.RABBITMQ_DLQ,
                passive=True,
            )
        await q_dlq.bind(exchange, routing_key=settings.RABBITMQ_DLQ)

        # Retry queue with DLX back to main
        try:
            q_retry = await channel.declare_queue(
                settings.RABBITMQ_RETRY_QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": settings.RABBITMQ_EXCHANGE,
                    "x-dead-letter-routing-key": settings.RABBITMQ_MAIN_QUEUE,
                },
            )
        except ChannelPreconditionFailed:
            # Fallback: fila já existe com argumentos diferentes (ex.: x-message-ttl).
            # Usa declaração passiva para reutilizar a fila existente evitando falha de startup.
            logger.warning(
                "Retry queue exists with different arguments; using passive declaration",
                extra={
                    "queue": settings.RABBITMQ_RETRY_QUEUE,
                    "exchange": settings.RABBITMQ_EXCHANGE,
                },
            )
            q_retry = await channel.declare_queue(
                settings.RABBITMQ_RETRY_QUEUE,
                passive=True,
            )
        await q_retry.bind(
            exchange,
            routing_key=settings.RABBITMQ_RETRY_QUEUE,
        )

        # Main queue
        try:
            self._main_queue = await channel.declare_queue(
                settings.RABBITMQ_MAIN_QUEUE,
                durable=True,
                arguments={
                    "x-overflow": "reject-publish",
                },
            )
        except ChannelPreconditionFailed:
            logger.warning(
                "Main queue exists with different arguments; using passive declaration",
                extra={
                    "queue": settings.RABBITMQ_MAIN_QUEUE,
                    "exchange": settings.RABBITMQ_EXCHANGE,
                },
            )
            self._main_queue = await channel.declare_queue(
                settings.RABBITMQ_MAIN_QUEUE,
                passive=True,
            )
        await self._main_queue.bind(
            exchange,
            routing_key=settings.RABBITMQ_MAIN_QUEUE,
        )

        logger.info(
            "RabbitMQ topology declared",
            extra={
                "exchange": settings.RABBITMQ_EXCHANGE,
                "main_queue": settings.RABBITMQ_MAIN_QUEUE,
                "retry_queue": settings.RABBITMQ_RETRY_QUEUE,
                "dlq": settings.RABBITMQ_DLQ,
            },
        )

    async def connect(self) -> None:
        async with self._lock:
            if self.is_ready:
                return

            logger.info(
                "Connecting to RabbitMQ...",
                extra={"component": "QueueManager"},
            )
            channel = await self._connect_channel()
            exchange = await self._declare_exchange(channel)
            await self._set_queues(channel, exchange)

    async def _close_with_timeout(
        self,
        name: str,
        closer: Callable[[], Awaitable[None]],
        *,
        timeout_s: float = 2.0,
    ) -> None:
        try:
            async with asyncio.timeout(timeout_s):
                await closer()
        except asyncio.TimeoutError:
            logger.warning(
                f"{name.capitalize()} close timeout",
                extra={"component": "QueueManager"},
            )
        except Exception as exc:
            logger.warning(
                f"Error closing {name}: {exc}",
                extra={"component": "QueueManager"},
            )

    def _reset_state(self) -> None:
        self._channel = None
        self._exchange = None
        self._connection = None
        self._main_queue = None
        logger.info(
            "QueueManager connections closed",
            extra={"component": "QueueManager"},
        )

    async def close(self) -> None:
        async with self._lock:
            logger.info(
                "Closing QueueManager connections...",
                extra={"component": "QueueManager"},
            )

            if self._channel and not self._channel.is_closed:
                await self._close_with_timeout("channel", self._channel.close)

            if self._connection and not self._connection.is_closed:
                await self._close_with_timeout("connection", self._connection.close)

            self._reset_state()

    async def _publish(
        self,
        routing_key: str,
        payload: Dict[str, Any],
        headers: Optional[Mapping[str, FieldValue]] = None,
        expiration: Optional[timedelta] = None,
        message_id: Optional[str] = None,
    ) -> str:
        if not self.is_ready:
            await self.connect()
        if self._exchange is None:
            raise RuntimeError("Exchange not connected")

        final_message_id = message_id or str(uuid.uuid4())
        header_map: Dict[str, FieldValue] = dict(headers or {})
        header_map.setdefault("message_id", final_message_id)
        header_map.setdefault("source", "api")

        body = json.dumps(payload).encode("utf-8")
        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers=header_map,
            message_id=final_message_id,
            expiration=expiration,
        )

        await self._exchange.publish(message, routing_key=routing_key)
        logger.info(
            "Message published",
            extra={"message_id": final_message_id, "routing_key": routing_key},
        )
        return final_message_id

    async def publish_to_main(self, payload: Dict[str, Any]) -> str:
        return await self._publish(settings.RABBITMQ_MAIN_QUEUE, payload)

    async def publish_to_retry(
        self,
        payload: Dict[str, Any],
        headers: Mapping[str, FieldValue],
        delay_ms: int,
        message_id: str,
    ) -> None:
        await self._publish(
            settings.RABBITMQ_RETRY_QUEUE,
            payload,
            headers=headers,
            expiration=timedelta(milliseconds=delay_ms),
            message_id=message_id,
        )

    async def publish_to_dlq(
        self,
        payload: Dict[str, Any],
        headers: Mapping[str, FieldValue],
        message_id: str,
    ) -> None:
        await self._publish(
            settings.RABBITMQ_DLQ,
            payload,
            headers=headers,
            message_id=message_id,
        )

    async def ping(self) -> bool:
        try:
            if not self.is_ready:
                await self.connect()
            if self._channel is None:
                return False
            await self._channel.declare_queue(
                settings.RABBITMQ_MAIN_QUEUE,
                passive=True,
            )
            return True
        except Exception:
            return False

    async def get_main_queue(self) -> AbstractQueue:
        if not self.is_ready:
            await self.connect()
        if self._channel is None:
            raise RuntimeError("Channel not connected")
        if self._main_queue is None:
            self._main_queue = await self._channel.declare_queue(
                settings.RABBITMQ_MAIN_QUEUE,
                durable=True,
            )
        return self._main_queue


# Shared global instance for app lifecycle
queue_manager = QueueManager()
