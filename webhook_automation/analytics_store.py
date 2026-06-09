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
Local file-based analytics store for remediation reports.

Persists session analytics to a JSON file so that dashboard
data survives server restarts and accurately reflects the
lifecycle of all sessions that have been kicked off.
"""

from __future__ import annotations

import json  # noqa: TID251
import logging
from pathlib import Path
from typing import Any

from .models import RemediationReport

logger = logging.getLogger(__name__)


class AnalyticsStore:
    """Read/write remediation reports to a local JSON file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, RemediationReport]:
        """Load all persisted reports from disk."""
        if not self._path.exists():
            return {}

        try:
            raw = self._path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt analytics file at %s – starting fresh", self._path)
            return {}

        reports: dict[str, RemediationReport] = {}
        for key, blob in data.get("reports", {}).items():
            try:
                reports[key] = RemediationReport.model_validate(blob)
            except Exception:
                logger.warning("Skipping invalid report entry: %s", key)
        logger.info(
            "Loaded %d report(s) from %s",
            len(reports),
            self._path,
        )
        return reports

    def save(self, reports: dict[str, RemediationReport]) -> None:
        """Persist all reports to disk atomically."""
        data = {
            "reports": {
                key: report.model_dump(mode="json") for key, report in reports.items()
            }
        }
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except OSError:
            logger.exception("Failed to save analytics to %s", self._path)

    def save_report(
        self,
        reports: dict[str, RemediationReport],
        key: str,
    ) -> None:
        """Convenience: save after a single report changes."""
        self.save(reports)
        logger.info("Persisted report %s to %s", key, self._path)
