# Superset Issue Remediation Webhook

A FastAPI webhook server that receives issue payloads and automatically creates
[Devin](https://devin.ai) sessions to remediate each issue in the
`mustansirali/superset` repository.

## Architecture

```
┌─────────────┐   POST /webhook   ┌──────────────┐   Devin API   ┌───────────┐
│  Trigger     │ ───────────────▶  │  FastAPI      │ ────────────▶ │  Devin    │
│  (CI, cron,  │                   │  Webhook      │               │  Sessions │
│   scanner)   │                   │  Server       │               │           │
└─────────────┘                    └──────────────┘               └───────────┘
                                          │                             │
                                          │  GET /reports/{key}         │  PRs
                                          ▼                             ▼
                                   ┌──────────────┐            ┌───────────────┐
                                   │  Remediation  │            │  Pull Requests│
                                   │  Reports      │            │  on GitHub    │
                                   └──────────────┘            └───────────────┘
```

### Flow

1. An external trigger (CI pipeline, cron job, security scanner) sends a
   `POST /webhook` request with one or more issue descriptions.
2. The server validates the payload (and optionally verifies an HMAC signature).
3. For each issue, a Devin session is created via the
   [Devin v3 API](https://docs.devin.ai/api-reference/overview). The prompt
   instructs Devin to investigate, fix, run pre-commit, and open a PR.
4. Sessions are polled asynchronously until they reach a terminal status.
5. A remediation report is stored in memory and available via `GET /reports`.

## Setup

> **Important:** All commands must be run from the **repo root** (`superset/`),
> not from inside `webhook_automation/`.

```bash
# From the repo root:
pip install -r webhook_automation/requirements.txt

# Copy .env template and fill in your API credentials:
cp webhook_automation/.env.example webhook_automation/.env
# Edit webhook_automation/.env with your values
```

### Environment Variables

Set these in `webhook_automation/.env` (auto-loaded) or as env vars:

| Variable | Required | Description |
|---|---|---|
| `WEBHOOK_DEVIN_API_KEY` | Yes | Devin API key (starts with `cog_`) |
| `WEBHOOK_DEVIN_ORG_ID` | Yes | Devin organization ID |
| `WEBHOOK_WEBHOOK_SECRET` | No | HMAC-SHA256 secret for signature verification |
| `WEBHOOK_TARGET_REPO` | No | Override target repo (default: `mustansirali/superset`) |
| `WEBHOOK_POLL_INTERVAL_SECONDS` | No | Polling interval (default: 30) |
| `WEBHOOK_HOST` | No | Bind host (default: `0.0.0.0`) |
| `WEBHOOK_PORT` | No | Bind port (default: `8000`) |

## Running the Server

```bash
# From the repo root (not from inside webhook_automation/):
python -m webhook_automation

# Or equivalently:
uvicorn webhook_automation.server:app --port 8000
```

The server exposes:
- `GET  /health` – Health check
- `POST /webhook` – Receive issue payloads
- `GET  /reports` – List all remediation reports
- `GET  /reports/{key}` – Get a specific report

## Sending Test Payloads

Use the built-in trigger script (run from the **repo root**):

```bash
# Single issue
python -m webhook_automation.trigger --payload single

# Multiple issues (note: use "multi", not "multiple")
python -m webhook_automation.trigger --payload multi

# Security issue
python -m webhook_automation.trigger --payload security

# Custom server URL
python -m webhook_automation.trigger --url https://your-server/webhook --payload single
```

Or use `curl`:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [{
      "issue_id": "TEST-001",
      "title": "Add missing type hints",
      "description": "Add type annotations to superset/utils/date_parser.py",
      "severity": "medium",
      "category": "type_error",
      "file_paths": ["superset/utils/date_parser.py"]
    }]
  }'
```

## Webhook Payload Schema

```json
{
  "event_type": "issue_remediation",
  "repo": "mustansirali/superset",
  "issues": [
    {
      "issue_id": "string (required)",
      "title": "string (required)",
      "description": "string (required)",
      "severity": "low | medium | high | critical",
      "category": "bug | security | performance | lint | type_error | dependency | test_failure | other",
      "file_paths": ["relative/path/to/file.py"],
      "labels": ["optional", "tags"]
    }
  ]
}
```

## Signature Verification

If `WEBHOOK_WEBHOOK_SECRET` is set, the server requires a valid
`X-Webhook-Signature` header on every request:

```python
import hashlib, hmac, json

body = json.dumps(payload).encode()
signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
# Send as header: X-Webhook-Signature: sha256=abc123...
```

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest webhook_automation/tests/ -v
```

## Monitoring Remediation Progress

After sending a webhook, poll the reports endpoint:

```bash
# List all reports
curl http://localhost:8000/reports

# Get specific report (use report_key from webhook response)
curl http://localhost:8000/reports/2025-01-15T10:30:00+00:00
```

Each report shows per-issue session status, Devin session URLs, and any PRs created.
