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
"""
Tests for the webhook server endpoints and Devin API integration.
"""

from __future__ import annotations

import hashlib
import hmac
import json  # noqa: TID251
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from webhook_automation.sample_payloads import (
    MULTI_ISSUE_PAYLOAD,
    SINGLE_ISSUE_PAYLOAD,
)
from webhook_automation.server import app


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(test_client: TestClient) -> None:
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_webhook_accepts_valid_payload(test_client: TestClient) -> None:
    resp = test_client.post("/webhook", json=SINGLE_ISSUE_PAYLOAD)
    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted"] is True
    assert data["issues_queued"] == 1


def test_webhook_accepts_multi_issue_payload(test_client: TestClient) -> None:
    resp = test_client.post("/webhook", json=MULTI_ISSUE_PAYLOAD)
    assert resp.status_code == 202
    data = resp.json()
    assert data["issues_queued"] == 2


def test_webhook_rejects_empty_issues(test_client: TestClient) -> None:
    payload: dict[str, Any] = {
        "event_type": "issue_remediation",
        "repo": "mustansirali/superset",
        "issues": [],
    }
    resp = test_client.post("/webhook", json=payload)
    assert resp.status_code == 400


def test_webhook_rejects_invalid_json(test_client: TestClient) -> None:
    resp = test_client.post(
        "/webhook",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_webhook_signature_validation(test_client: TestClient) -> None:
    """When a webhook secret is set, missing/bad signatures are rejected."""
    secret = "test-secret-123"  # noqa: S105
    body = json.dumps(SINGLE_ISSUE_PAYLOAD).encode()
    valid_sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch("webhook_automation.server.settings") as mock_settings:
        mock_settings.webhook_secret = secret
        mock_settings.devin_api_key = "fake"
        mock_settings.devin_org_id = "org-fake"
        mock_settings.devin_api_base_url = "https://api.devin.ai/v3"
        mock_settings.poll_interval_seconds = 1
        mock_settings.poll_max_attempts = 1

        resp_no_sig = test_client.post(
            "/webhook",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp_no_sig.status_code == 401

        resp_bad_sig = test_client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": "sha256=bad",
            },
        )
        assert resp_bad_sig.status_code == 401

        resp_good_sig = test_client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": valid_sig,
            },
        )
        assert resp_good_sig.status_code == 202


def test_list_reports_empty(test_client: TestClient) -> None:
    from webhook_automation.server import reports

    reports.clear()
    resp = test_client.get("/reports")
    assert resp.status_code == 200
    assert resp.json()["reports"] == []


def test_get_report_not_found(test_client: TestClient) -> None:
    resp = test_client.get("/reports/nonexistent")
    assert resp.status_code == 404


def test_dashboard_returns_html(test_client: TestClient) -> None:
    resp = test_client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Webhook Automation Dashboard" in resp.text


def test_api_stats_empty(test_client: TestClient) -> None:
    from webhook_automation.server import reports

    reports.clear()
    resp = test_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overview"]["total_events"] == 0
    assert data["overview"]["total_issues"] == 0
    assert data["overview"]["success_rate"] == 0.0
    assert data["timeline"] == []


def test_api_stats_after_webhook(test_client: TestClient) -> None:
    from webhook_automation.server import reports

    reports.clear()
    test_client.post("/webhook", json=SINGLE_ISSUE_PAYLOAD)

    resp = test_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    overview = data["overview"]
    assert overview["total_events"] == 1
    assert overview["total_issues"] == 1
    assert len(data["timeline"]) == 1


@pytest.mark.asyncio
async def test_devin_client_create_session() -> None:
    """DevinAPIClient.create_session calls the correct endpoint."""
    mock_response = {
        "session_id": "devin-test123",
        "url": "https://app.devin.ai/sessions/devin-test123",
        "status": "running",
    }

    with patch("webhook_automation.devin_client.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_client_instance.post.return_value = mock_resp

        from webhook_automation.devin_client import DevinAPIClient

        client = DevinAPIClient()
        result = await client.create_session(prompt="test prompt", repos=["org/repo"])

        assert result["session_id"] == "devin-test123"
        mock_client_instance.post.assert_called_once()
