"""Pluggable alert dispatcher (ADR-0003).

Adapters implement `send(event)`. Channels are chosen by config (ALERT_CHANNELS).
Adding a channel = one adapter class; the engine is untouched.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("afdd.dispatcher")


class AlertAdapter:
    name = "base"

    async def send(self, event: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class LogAdapter(AlertAdapter):
    name = "log"

    async def send(self, event: dict) -> None:
        log.info("ALERT", extra={"alert": event})


class WebhookAdapter(AlertAdapter):
    name = "webhook"

    def __init__(self, url: str):
        self.url = url

    async def send(self, event: dict) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self.url, json=event)
        except Exception as exc:  # noqa: BLE001
            log.warning("webhook dispatch failed", extra={"error": str(exc), "url": self.url})


class AlertDispatcher:
    def __init__(self, adapters: list[AlertAdapter]):
        self.adapters = adapters

    async def dispatch(self, event: dict) -> None:
        for adapter in self.adapters:
            await adapter.send(event)

    @classmethod
    def from_env(cls) -> "AlertDispatcher":
        channels = os.environ.get("ALERT_CHANNELS", "log").split(",")
        adapters: list[AlertAdapter] = []
        for ch in (c.strip() for c in channels):
            if ch == "log":
                adapters.append(LogAdapter())
            elif ch == "webhook":
                url = os.environ.get("ALERT_WEBHOOK_URL", "")
                if url:
                    adapters.append(WebhookAdapter(url))
        if not adapters:
            adapters.append(LogAdapter())
        return cls(adapters)
