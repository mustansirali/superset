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

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LINT = "lint"
    TYPE_ERROR = "type_error"
    DEPENDENCY = "dependency"
    TEST_FAILURE = "test_failure"
    OTHER = "other"


class IssuePayload(BaseModel):
    """Webhook payload describing an issue to remediate."""

    issue_id: str = Field(description="Unique identifier for the issue")
    title: str = Field(description="Short description of the issue")
    description: str = Field(
        description="Detailed description including file paths and expected fix"
    )
    severity: IssueSeverity = Field(default=IssueSeverity.MEDIUM)
    category: IssueCategory = Field(default=IssueCategory.BUG)
    file_paths: list[str] = Field(
        default_factory=list,
        description="Affected file paths relative to repo root",
    )
    labels: list[str] = Field(default_factory=list)


class WebhookEvent(BaseModel):
    """Wrapper around one or more issue payloads."""

    event_type: str = Field(default="issue_remediation")
    repo: str = Field(default="mustansirali/superset")
    issues: list[IssuePayload]
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionInfo(BaseModel):
    """Tracks a Devin session created for an issue."""

    issue_id: str
    session_id: str
    session_url: str
    status: str = "running"
    pull_requests: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


class RemediationReport(BaseModel):
    """Summary report after all sessions complete."""

    event_type: str
    repo: str
    total_issues: int
    sessions: list[SessionInfo]
    completed: int = 0
    failed: int = 0
    pending: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
