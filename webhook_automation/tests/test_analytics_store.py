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
Tests for the local file-based analytics store.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from webhook_automation.analytics_store import AnalyticsStore
from webhook_automation.models import RemediationReport, SessionInfo


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "analytics.json"


@pytest.fixture
def store(store_path: Path) -> AnalyticsStore:
    return AnalyticsStore(store_path)


def _make_report(
    *,
    total: int = 1,
    completed: int = 0,
    failed: int = 0,
    pending: int = 1,
) -> RemediationReport:
    sessions = [
        SessionInfo(
            issue_id="ISSUE-1",
            session_id="devin-abc",
            session_url="https://app.devin.ai/sessions/devin-abc",
            status="exit" if completed else "error",
        )
    ]
    return RemediationReport(
        event_type="issue_remediation",
        repo="mustansirali/superset",
        total_issues=total,
        sessions=sessions,
        completed=completed,
        failed=failed,
        pending=pending,
    )


def test_load_returns_empty_when_no_file(store: AnalyticsStore) -> None:
    result = store.load()
    assert result == {}


def test_save_and_load_roundtrip(
    store: AnalyticsStore,
    store_path: Path,
) -> None:
    reports: dict[str, RemediationReport] = {
        "2026-01-01T00:00:00+00:00": _make_report(
            completed=1,
            failed=0,
            pending=0,
        ),
    }
    store.save(reports)

    assert store_path.exists()

    loaded = store.load()
    assert len(loaded) == 1
    key = "2026-01-01T00:00:00+00:00"
    assert loaded[key].completed == 1
    assert loaded[key].failed == 0
    assert loaded[key].total_issues == 1
    assert len(loaded[key].sessions) == 1
    assert loaded[key].sessions[0].status == "exit"


def test_save_report_convenience(store: AnalyticsStore) -> None:
    reports: dict[str, RemediationReport] = {
        "key-1": _make_report(failed=1, pending=0),
    }
    store.save_report(reports, "key-1")

    loaded = store.load()
    assert "key-1" in loaded
    assert loaded["key-1"].failed == 1


def test_load_handles_corrupt_file(
    store: AnalyticsStore,
    store_path: Path,
) -> None:
    store_path.write_text("not valid json", encoding="utf-8")
    result = store.load()
    assert result == {}


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    deep_path = tmp_path / "a" / "b" / "c" / "analytics.json"
    s = AnalyticsStore(deep_path)
    reports: dict[str, RemediationReport] = {
        "k": _make_report(),
    }
    s.save(reports)
    assert deep_path.exists()


def test_multiple_reports_persist(store: AnalyticsStore) -> None:
    reports: dict[str, RemediationReport] = {
        "evt-1": _make_report(total=2, completed=1, failed=1, pending=0),
        "evt-2": _make_report(total=3, completed=2, failed=0, pending=1),
    }
    store.save(reports)
    loaded = store.load()

    assert len(loaded) == 2
    assert loaded["evt-1"].completed == 1
    assert loaded["evt-1"].failed == 1
    assert loaded["evt-2"].completed == 2
    assert loaded["evt-2"].pending == 1
