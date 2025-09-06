from typing import Any, Dict

from .manager import QueueManager, logger


class Publisher:
    def __init__(self):
        self.q_manager = QueueManager()

    async def send_message(self, payload: Dict[str, Any]) -> None:
        try:
            await self.q_manager.publish_to_main(payload)
            logger.info(f"Message sent to main queue: {payload}")
        except Exception as exc:
            logger.error(f"Error sending message: {exc}")
            raise


async def send_message(payload: Dict[str, Any]) -> None:
    publisher = Publisher()
    await publisher.send_message(payload)
