import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds


class WebhookService:
    """Webhook 回调通知服务"""

    @staticmethod
    async def send(
        url: str,
        event: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        发送 Webhook 通知

        Args:
            url: Webhook 回调 URL
            event: 事件类型 (task_completed / task_failed)
            payload: 事件数据

        Returns:
            是否发送成功
        """
        body = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code < 400:
                    logger.info(f"Webhook sent to {url}: {event} (status={response.status_code})")
                    return True
                else:
                    logger.warning(
                        f"Webhook failed for {url}: status={response.status_code}"
                    )
                    return False
        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout for {url}")
            return False
        except Exception as e:
            logger.error(f"Webhook error for {url}: {e}")
            return False

    @staticmethod
    async def notify_task_result(
        webhook_url: str,
        spider_name: str,
        spider_id: str,
        task_id: str,
        status: str,
        total_count: int = 0,
        success_count: int = 0,
        error_message: str | None = None,
        duration: float = 0,
    ) -> bool:
        """任务结果通知的快捷方法"""
        event = "task_completed" if status == "completed" else "task_failed"
        payload = {
            "spider_id": spider_id,
            "spider_name": spider_name,
            "task_id": task_id,
            "status": status,
            "total_count": total_count,
            "success_count": success_count,
            "duration_seconds": duration,
        }
        if error_message:
            payload["error_message"] = error_message

        return await WebhookService.send(webhook_url, event, payload)
