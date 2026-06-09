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
Sample webhook payloads for testing the issue remediation webhook.
"""

from __future__ import annotations

from typing import Any

SINGLE_ISSUE_PAYLOAD: dict[str, Any] = {
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
        {
            "issue_id": "SUPERSET-001",
            "title": "Missing type hints in utils/date_parser.py",
            "description": (
                "The function `parse_human_datetime` in "
                "`superset/utils/date_parser.py` lacks type annotations on its "
                "parameters and return value. Add proper type hints to comply "
                "with the project's MyPy requirements."
            ),
            "severity": "medium",
            "category": "type_error",
            "file_paths": ["superset/utils/date_parser.py"],
            "labels": ["type-hints", "backend"],
        }
    ],
}

MULTI_ISSUE_PAYLOAD: dict[str, Any] = {
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
        {
            "issue_id": "SUPERSET-002",
            "title": "Lint warning: unused import in views/api.py",
            "description": (
                "There is an unused import `from flask import jsonify` in "
                "`superset/views/api.py`. Remove it to satisfy ruff linting."
            ),
            "severity": "low",
            "category": "lint",
            "file_paths": ["superset/views/api.py"],
            "labels": ["lint", "backend"],
        },
        {
            "issue_id": "SUPERSET-003",
            "title": "Add docstring to DashboardDAO.copy_dashboard",
            "description": (
                "The method `copy_dashboard` in `superset/daos/dashboard.py` "
                "is missing a docstring. Add a clear docstring describing "
                "parameters, return type, and any exceptions raised."
            ),
            "severity": "low",
            "category": "other",
            "file_paths": ["superset/daos/dashboard.py"],
            "labels": ["documentation", "backend"],
        },
    ],
}

SECURITY_ISSUE_PAYLOAD: dict[str, Any] = {
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
        {
            "issue_id": "SUPERSET-004",
            "title": "Pin vulnerable dependency version",
            "description": (
                "A dependency listed in `requirements/base.txt` has a known "
                "CVE. Update the pinned version to the latest patched release. "
                "Check the project's requirements files and update accordingly."
            ),
            "severity": "high",
            "category": "dependency",
            "file_paths": ["requirements/base.txt"],
            "labels": ["security", "dependency"],
        }
    ],
}
