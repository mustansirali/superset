# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class DevinAPIClient:
    """Async wrapper around the Devin v3 REST API."""

    def __init__(self) -> None:
        self.base_url = settings.devin_api_base_url.rstrip("/")
        self.org_id = settings.devin_org_id
        self._headers = {
            "Authorization": f"Bearer {settings.devin_api_key}",
            "Content-Type": "application/json",
        }

    def _sessions_url(self, session_id: str = "") -> str:
        base = f"{self.base_url}/organizations/{self.org_id}/sessions"
        if session_id:
            return f"{base}/{session_id}"
        return base

    async def create_session(
        self,
        prompt: str,
        *,
        title: str | None = None,
        repos: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new Devin session and return the response JSON."""
        payload: dict[str, Any] = {"prompt": prompt}
        if title:
            payload["title"] = title
        if repos:
            payload["repos"] = repos
        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._sessions_url(),
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            logger.info(
                "Created session %s – %s", data.get("session_id"), data.get("url")
            )
            return data

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Fetch the latest state of a session."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._sessions_url(session_id),
                headers=self._headers,
            )
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        """Send a follow-up message to a running session."""
        url = f"{self._sessions_url(session_id)}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={"message": message},
            )
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def poll_until_done(
        self,
        session_id: str,
        *,
        interval: int = settings.poll_interval_seconds,
        max_attempts: int = settings.poll_max_attempts,
    ) -> dict[str, Any]:
        """Poll a session until it reaches a terminal status."""
        terminal_statuses = {"exit", "error", "suspended"}
        for attempt in range(1, max_attempts + 1):
            data = await self.get_session(session_id)
            status = data.get("status", "")
            logger.info(
                "Poll %d/%d – session %s status=%s",
                attempt,
                max_attempts,
                session_id,
                status,
            )
            if status in terminal_statuses:
                return data
            await asyncio.sleep(interval)
        logger.warning(
            "Polling timed out for session %s after %d attempts",
            session_id,
            max_attempts,
        )
        return await self.get_session(session_id)
