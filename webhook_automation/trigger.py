#!/usr/bin/env python3
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
CLI tool to fire a test webhook payload at the running server.

Usage:
    python -m webhook_automation.trigger [--url URL] [--payload single|multi|security]
"""

from __future__ import annotations

import argparse
import json  # noqa: TID251
import sys

import httpx

from .config import settings
from .sample_payloads import (
    MULTI_ISSUE_PAYLOAD,
    SECURITY_ISSUE_PAYLOAD,
    SINGLE_ISSUE_PAYLOAD,
)

PAYLOADS = {
    "single": SINGLE_ISSUE_PAYLOAD,
    "multi": MULTI_ISSUE_PAYLOAD,
    "security": SECURITY_ISSUE_PAYLOAD,
}


def _default_url() -> str:
    return f"http://localhost:{settings.port}/webhook"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a test payload to the webhook server"
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"Webhook endpoint URL (default: http://localhost:{settings.port}/webhook)",
    )
    parser.add_argument(
        "--payload",
        choices=list(PAYLOADS.keys()),
        default="single",
        help="Which sample payload to send (default: single)",
    )
    args = parser.parse_args()

    url: str = args.url if args.url is not None else _default_url()
    payload = PAYLOADS[args.payload]
    print(f"Sending '{args.payload}' payload to {url} ...")
    print(json.dumps(payload, indent=2))

    try:
        resp = httpx.post(url, json=payload, timeout=10)
        print(f"\nHTTP {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
    except httpx.ConnectError:
        print(
            f"\nERROR: Could not connect to {url}. Is the server running?",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
