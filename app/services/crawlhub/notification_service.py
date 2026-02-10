import json
import logging
from datetime import datetime, timezone

import httpx

from models.crawlhub.notification_channel import (
    NotificationChannelConfig,
    NotificationChannelType,
)
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    """通知发送服务"""

    async def send(
        self, channel: NotificationChannelConfig, title: str, message: str
    ) -> bool:
        """根据渠道类型分发通知"""
        try:
            config = json.loads(channel.config) if isinstance(channel.config, str) else channel.config
        except (json.JSONDecodeError, TypeError):
            logger.error(f"Invalid config JSON for channel {channel.id}")
            return False

        match channel.channel_type:
            case NotificationChannelType.EMAIL:
                return await self._send_email(config, title, message)
            case NotificationChannelType.WEBHOOK:
                return await self._send_webhook(config, title, message)
            case NotificationChannelType.DINGTALK:
                return await self._send_dingtalk(config, title, message)
            case NotificationChannelType.SLACK:
                return await self._send_slack(config, title, message)
            case _:
                logger.error(f"Unsupported channel type: {channel.channel_type}")
                return False

    async def _send_email(self, config: dict, title: str, message: str) -> bool:
        """通过邮件发送通知"""
        try:
            from extensions.ext_mail import mail

            to = config.get("to")
            if not to:
                logger.error("Email config missing 'to' field")
                return False

            mail.send(
                to=to,
                subject=title,
                html=f"<h3>{title}</h3><p>{message}</p>",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    async def _send_webhook(self, config: dict, title: str, message: str) -> bool:
        """通过 Webhook 发送通知"""
        try:
            url = config.get("url")
            if not url:
                logger.error("Webhook config missing 'url' field")
                return False

            payload = {
                "title": title,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

    async def _send_dingtalk(self, config: dict, title: str, message: str) -> bool:
        """通过钉钉机器人发送通知"""
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                logger.error("DingTalk config missing 'webhook_url' field")
                return False

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": message,
                },
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")
            return False

    async def _send_slack(self, config: dict, title: str, message: str) -> bool:
        """通过 Slack Webhook 发送通知"""
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                logger.error("Slack config missing 'webhook_url' field")
                return False

            payload = {
                "text": f"*{title}*\n{message}",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
