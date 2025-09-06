import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict

from aio_pika.abc import AbstractIncomingMessage

from .queue import QueueManager, handle_processing_failure

logger = logging.getLogger(__name__)


ProcessFunc = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]


async def default_process_func(
    payload: Dict[str, Any],
    headers: Dict[str, Any],
) -> None:
    """Example processor. Replace with domain-specific logic."""
    _ = headers  # used for typing and future usage
    should_fail = bool(payload.get("should_fail"))
    await asyncio.sleep(0)  # yield control
    if should_fail:
        raise RuntimeError("Simulated processing failure")


async def _process_message_queue(
    queue_iter,
    manager: QueueManager,
    process_func: ProcessFunc,
    stop_event: asyncio.Event,
) -> None:
    """Process messages from queue iterator with reduced nesting."""
    async for message in queue_iter:
        if stop_event.is_set():
            logger.info(
                "Stop event received, stopping consumer",
                extra={"component": "Consumer"},
            )
            break

        async with message.process(ignore_processed=True):
            await _handle_message(manager, message, process_func)


async def consume_forever(
    manager: QueueManager,
    stop_event: asyncio.Event,
    process_func: ProcessFunc | None = None,
) -> None:
    """Consume messages from main queue until stop_event is set.

    Acks on success; on failure routes to retry or DLQ and acks to avoid redelivery.
    """
    process_func = process_func or default_process_func
    logger.info("Consumer started", extra={"component": "Consumer"})

    try:
        while not stop_event.is_set():
            if not manager.is_ready:
                await manager.connect()

            queue = await manager.get_main_queue()

            async with queue.iterator() as queue_iter:
                try:
                    await _process_message_queue(
                        queue_iter,
                        manager,
                        process_func,
                        stop_event,
                    )
                except Exception:
                    if stop_event.is_set():
                        logger.info(
                            "Consumer stopped due to stop event",
                            extra={"component": "Consumer"},
                        )
                        break
                    logger.exception(
                        "Error in message iteration",
                        extra={"component": "Consumer"},
                    )
                    await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        logger.info("Consumer task cancelled", extra={"component": "Consumer"})
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error in consumer",
            extra={"component": "Consumer", "error": str(exc)},
        )
        raise
    finally:
        logger.info("Consumer stopped", extra={"component": "Consumer"})


async def _handle_message(
    manager: QueueManager,
    message: AbstractIncomingMessage,
    process_func: ProcessFunc,
) -> None:
    headers = dict(message.headers or {})

    try:
        payload = json.loads(message.body.decode("utf-8"))
    except Exception as exc:
        logger.exception(
            "Invalid JSON payload; sending to DLQ",
            extra={"error": str(exc)},
        )
        await handle_processing_failure(
            manager,
            {"raw": message.body.decode("utf-8", "ignore")},
            headers,
            "invalid-json",
        )
        return

    try:
        await process_func(payload, headers)
        logger.info(
            "Message processed",
            extra={
                "message_id": headers.get("message_id"),
                "payload_keys": list(payload.keys()),
            },
        )
    except Exception as exc:
        logger.exception(
            "Processing failed; routing to retry/DLQ",
            extra={"message_id": headers.get("message_id"), "error": str(exc)},
        )
        await handle_processing_failure(
            manager,
            payload,
            headers,
            reason=type(exc).__name__,
        )
