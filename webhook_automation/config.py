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

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    devin_api_key: str = ""
    devin_org_id: str = ""
    devin_api_base_url: str = "https://api.devin.ai/v3"
    target_repo: str = "mustansirali/superset"
    webhook_secret: str = ""
    poll_interval_seconds: int = 30
    poll_max_attempts: int = 120
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    model_config = {
        "env_prefix": "WEBHOOK_",
        "env_file": "webhook_automation/.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
