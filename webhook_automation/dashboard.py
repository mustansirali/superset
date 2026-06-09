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
Dashboard routes: ``/dashboard`` (HTML) and ``/api/stats`` (JSON).

The HTML page uses Chart.js (loaded from CDN) to render charts.
``/api/stats`` returns aggregated analytics that the page fetches
via ``fetch()``, so the dashboard auto-refreshes without a full
page reload.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .models import RemediationReport

router = APIRouter()

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_DASHBOARD_HTML = (_TEMPLATE_DIR / "dashboard.html").read_text()

# This will be set by the main server module after import so the
# dashboard can read the shared in-memory store.
_reports: dict[str, RemediationReport] = {}


def bind_reports(reports: dict[str, RemediationReport]) -> None:
    """Give the dashboard access to the shared reports dict."""
    global _reports  # noqa: PLW0603
    _reports = reports


def _compute_stats() -> dict[str, Any]:
    """Aggregate analytics across all remediation reports."""
    total_events = len(_reports)
    total_issues = 0
    completed = 0
    failed = 0
    pending = 0
    total_prs = 0
    status_counts: Counter[str] = Counter()
    timeline: list[dict[str, Any]] = []

    for key, report in _reports.items():
        total_issues += report.total_issues
        completed += report.completed
        failed += report.failed
        pending += report.pending

        for session in report.sessions:
            status_counts[session.status] += 1
            total_prs += len(session.pull_requests)

        timeline.append(
            {
                "report_key": key,
                "timestamp": report.generated_at.isoformat(),
                "total": report.total_issues,
                "completed": report.completed,
                "failed": report.failed,
                "pending": report.pending,
            }
        )

    success_rate = (completed / total_issues * 100) if total_issues > 0 else 0.0

    return {
        "overview": {
            "total_events": total_events,
            "total_issues": total_issues,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "total_prs_created": total_prs,
            "success_rate": round(success_rate, 1),
        },
        "status_breakdown": dict(status_counts),
        "timeline": sorted(timeline, key=lambda t: t["timestamp"]),
    }


@router.get("/api/stats")
async def stats() -> dict[str, Any]:
    """Return aggregated analytics JSON."""
    return _compute_stats()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    """Serve the analytics dashboard HTML page."""
    return _DASHBOARD_HTML
