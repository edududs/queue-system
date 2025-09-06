import time
import uuid
from typing import TYPE_CHECKING, Any, Dict

from ...settings.config import settings
from .manager import QueueManager, logger

if TYPE_CHECKING:
    from aio_pika.abc import FieldValue


def compute_next_retry_delay_ms(current_retry_count: int) -> int:
    base = settings.RABBITMQ_RETRY_DELAY_MS
    # exponential backoff: base * (2 ** current_retry_count)
    return int(base * (2 ** max(0, current_retry_count)))


async def handle_processing_failure(
    manager: QueueManager,
    payload: Dict[str, Any],
    headers: Dict[str, Any],
    reason: str,
) -> None:
    """Route failed message to retry or DLQ depending on retry count."""
    retry_count = int(headers.get("x-retry-count", 0))
    message_id = headers.get("message_id") or str(uuid.uuid4())

    if retry_count < settings.RABBITMQ_MAX_RETRIES:
        next_retry_count = retry_count + 1
        delay_ms = compute_next_retry_delay_ms(retry_count)
        new_headers: Dict[str, FieldValue] = {
            **headers,
            "x-retry-count": next_retry_count,
            "x-retry-reason": reason,
            "x-retry-timestamp": int(time.time()),
        }
        await manager.publish_to_retry(payload, new_headers, delay_ms, message_id)
        logger.warning(
            "Message sent to retry",
            extra={
                "message_id": message_id,
                "retry_count": next_retry_count,
                "delay_ms": delay_ms,
                "reason": reason,
            },
        )
        return

    # Max retries exceeded => DLQ
    dlq_headers: Dict[str, FieldValue] = {
        **headers,
        "x-final-failure-reason": reason,
        "x-final-failure-timestamp": int(time.time()),
        "x-total-retry-count": retry_count,
    }
    await manager.publish_to_dlq(payload, dlq_headers, message_id)
    logger.error(
        "Message sent to DLQ",
        extra={
            "message_id": message_id,
            "final_reason": reason,
            "total_retries": retry_count,
        },
    )
