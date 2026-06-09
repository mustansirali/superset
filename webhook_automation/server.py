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
Webhook server that listens for issue payloads and dispatches
Devin sessions to remediate each issue.

Usage:
    WEBHOOK_DEVIN_API_KEY=cog_... WEBHOOK_DEVIN_ORG_ID=org-... \
        uvicorn webhook_automation.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .dashboard import bind_reports, router as dashboard_router
from .devin_client import DevinAPIClient
from .models import (
    IssuePayload,
    RemediationReport,
    SessionInfo,
    WebhookEvent,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Superset Issue Remediation Webhook",
    description=(
        "Receives webhook payloads describing issues in the "
        "mustansirali/superset repo, then uses the Devin API to "
        "create sessions that automatically remediate each issue."
    ),
    version="1.0.0",
)

client = DevinAPIClient()

# In-memory store keyed by event timestamp → report
reports: dict[str, RemediationReport] = {}

# Wire up the dashboard with access to the shared reports store.
bind_reports(reports)
app.include_router(dashboard_router)


def _verify_signature(body: bytes, signature: str | None) -> None:
    """Verify HMAC-SHA256 webhook signature when a secret is configured."""
    if not settings.webhook_secret:
        return
    if not signature:
        raise HTTPException(
            status_code=401, detail="Missing X-Webhook-Signature header"
        )
    expected = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _build_prompt(issue: IssuePayload, repo: str) -> str:
    """Build a Devin prompt from an issue payload."""
    file_hint = ""
    if issue.file_paths:
        file_hint = "\n\nAffected files:\n" + "\n".join(
            f"- {fp}" for fp in issue.file_paths
        )

    return (
        f"You are working on the repository `{repo}`.\n\n"
        f"## Issue: {issue.title}\n\n"
        f"**Severity:** {issue.severity.value}  \n"
        f"**Category:** {issue.category.value}\n\n"
        f"{issue.description}"
        f"{file_hint}\n\n"
        "Please:\n"
        "1. Investigate the issue in the codebase.\n"
        "2. Implement a fix following the repo's conventions "
        "(type hints, pre-commit, etc.).\n"
        "3. Run `pre-commit run --all-files` to validate.\n"
        "4. Open a pull request with a clear description of the fix.\n"
    )


async def _process_issue(
    issue: IssuePayload,
    repo: str,
    report: RemediationReport,
) -> None:
    """Create a Devin session for one issue and poll until done."""
    prompt = _build_prompt(issue, repo)
    try:
        session_data = await client.create_session(
            prompt=prompt,
            title=f"[Auto-Remediate] {issue.title}",
            repos=[repo],
            tags=["webhook-automation", issue.category.value, issue.severity.value],
        )
    except Exception:
        logger.exception("Failed to create session for issue %s", issue.issue_id)
        info = SessionInfo(
            issue_id=issue.issue_id,
            session_id="N/A",
            session_url="N/A",
            status="error",
        )
        report.sessions.append(info)
        report.failed += 1
        report.pending = max(0, report.pending - 1)
        return

    session_id = session_data["session_id"]
    session_url = session_data.get("url", "")

    info = SessionInfo(
        issue_id=issue.issue_id,
        session_id=session_id,
        session_url=session_url,
        status="running",
    )
    report.sessions.append(info)

    final = await client.poll_until_done(session_id)
    info.status = final.get("status", "unknown")
    info.finished_at = datetime.now(timezone.utc)

    prs = final.get("pull_requests", [])
    if isinstance(prs, list):
        info.pull_requests = [
            pr.get("url", "") if isinstance(pr, dict) else str(pr) for pr in prs
        ]

    if info.status == "exit":
        report.completed += 1
    else:
        report.failed += 1
    report.pending = max(0, report.pending - 1)

    logger.info(
        "Issue %s → session %s finished with status=%s, PRs=%s",
        issue.issue_id,
        session_id,
        info.status,
        info.pull_requests,
    )


async def _handle_event(event: WebhookEvent) -> None:
    """Process all issues in a webhook event concurrently."""
    report_key = event.triggered_at.isoformat()
    report = RemediationReport(
        event_type=event.event_type,
        repo=event.repo,
        total_issues=len(event.issues),
        sessions=[],
        pending=len(event.issues),
    )
    reports[report_key] = report

    tasks = [_process_issue(issue, event.repo, report) for issue in event.issues]
    await asyncio.gather(*tasks, return_exceptions=True)

    report.generated_at = datetime.now(timezone.utc)
    logger.info(
        "Event %s complete – %d/%d issues remediated",
        report_key,
        report.completed,
        report.total_issues,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=dict[str, Any])
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: str | None = Header(default=None),
) -> JSONResponse:
    """
    Receive a webhook payload containing one or more issues.

    The payload is validated, then each issue is dispatched to a
    background Devin session. Returns immediately with session metadata.
    """
    body = await request.body()
    _verify_signature(body, x_webhook_signature)

    try:
        event = WebhookEvent.model_validate_json(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {exc}") from exc

    if not event.issues:
        raise HTTPException(
            status_code=400, detail="Payload must contain at least one issue"
        )

    report_key = event.triggered_at.isoformat()

    background_tasks.add_task(_handle_event, event)

    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "report_key": report_key,
            "issues_queued": len(event.issues),
            "message": (
                f"Queued {len(event.issues)} issue(s) for remediation. "
                f"Poll GET /reports/{report_key} for status."
            ),
        },
    )


@app.get("/reports")
async def list_reports() -> dict[str, Any]:
    """List all remediation reports."""
    summaries = []
    for key, report in reports.items():
        summaries.append(
            {
                "report_key": key,
                "repo": report.repo,
                "total_issues": report.total_issues,
                "completed": report.completed,
                "failed": report.failed,
                "pending": report.pending,
            }
        )
    return {"reports": summaries}


@app.get("/reports/{report_key:path}")
async def get_report(report_key: str) -> RemediationReport:
    """Get a specific remediation report."""
    report = reports.get(report_key)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
