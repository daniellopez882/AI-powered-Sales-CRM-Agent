"""
integrations/slack.py
Real Slack Web API client for sending pipeline reports and alerts.
Docs: https://api.slack.com/methods/chat.postMessage
"""
import httpx
from typing import Optional
from integrations.base import BaseMessagingProvider
from config.settings import settings


class SlackIntegration(BaseMessagingProvider):
    def __init__(self):
        self.token = settings.slack_bot_token
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {self.token or ''}",
            "Content-Type": "application/json",
        }

    def post_message(self, channel: str, text: str,
                     blocks: Optional[list] = None) -> dict:
        """
        Post a message to a Slack channel.
        Args:
            channel: Channel ID or name (e.g. '#sales-alerts' or 'C0123456')
            text: Plain text fallback (required for notifications)
            blocks: Optional rich Block Kit payload
        """
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN not set.")

        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{self.base_url}/chat.postMessage",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

        return {
            "status": "success",
            "channel": data.get("channel"),
            "ts": data.get("ts"),  # Message timestamp (used for threading)
        }

    def post_alert(self, title: str, message: str, level: str = "info",
                   channel: str = "sales-alerts") -> dict:
        """
        Post a formatted alert with emoji level indicator.
        level: 'info' | 'warning' | 'critical'
        """
        icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}
        icon = icons.get(level, "ℹ️")
        return self.post_message(channel, f"{icon} *{title}*\n{message}")
