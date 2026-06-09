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
5. A remediation report is stored locally (JSON file) and available via
   `GET /reports`. Analytics persist across server restarts.

## Quick Start (Docker)

```bash
cd webhook_automation

# 1. Create your .env file
cp .env.example .env
# Edit .env with your Devin API key and org ID

# 2. Start the server
docker compose up -d

# 3. Fire a test payload
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"issues":[{"issue_id":"TEST-001","title":"Fix bug","description":"Fix the bug in utils.py"}]}'

# 4. Check reports
curl http://localhost:8000/reports

# 5. Stop the server
docker compose down
```

## Quick Start (Local Python)

> **Important:** Run all commands from the **repo root** (`superset/`),
> not from inside `webhook_automation/`.

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r webhook_automation/requirements.txt

# 3. Create your .env file
cp webhook_automation/.env.example webhook_automation/.env
# Edit webhook_automation/.env with your Devin API key and org ID

# 4. Start the server
python -m webhook_automation

# 5. In a separate terminal (with venv activated, from repo root):
python -m webhook_automation.trigger --payload single
```

## Environment Variables

Set these in `webhook_automation/.env` (auto-loaded) or as env vars:

| Variable | Required | Description |
|---|---|---|
| `WEBHOOK_DEVIN_API_KEY` | Yes | Devin API key (starts with `cog_`) |
| `WEBHOOK_DEVIN_ORG_ID` | Yes | Devin organization ID |
| `WEBHOOK_WEBHOOK_SECRET` | No | HMAC-SHA256 secret for signature verification |
| `WEBHOOK_TARGET_REPO` | No | Override target repo (default: `mustansirali/superset`) |
| `WEBHOOK_POLL_INTERVAL_SECONDS` | No | Polling interval (default: 30) |
| `WEBHOOK_HOST` | No | Bind host (default: `0.0.0.0`) |
| `WEBHOOK_ANALYTICS_FILE` | No | Path to analytics JSON file (default: `webhook_automation/data/analytics.json`) |
| `WEBHOOK_PORT` | No | Bind port (default: `8000`) |

> **Note:** Do not wrap values in quotes in `.env` — write
> `WEBHOOK_DEVIN_API_KEY=cog_abc123`, not `WEBHOOK_DEVIN_API_KEY='cog_abc123'`.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/webhook` | Receive issue payloads |
| `GET` | `/reports` | List all remediation reports |
| `GET` | `/reports/{key}` | Get a specific report |
| `GET` | `/dashboard` | Analytics dashboard (HTML) |
| `GET` | `/api/stats` | Aggregated analytics (JSON) |

## Sending Payloads

### Built-in Sample Payloads

```bash
# From repo root (local Python):
python -m webhook_automation.trigger --payload single
python -m webhook_automation.trigger --payload multi
python -m webhook_automation.trigger --payload security
```

### Custom Payloads with curl

**Single issue:**

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issues": [{
      "issue_id": "MY-001",
      "title": "Add retry logic to API client",
      "description": "The HTTP client in superset/utils/core.py has no retry logic. Add exponential backoff for transient failures.",
      "severity": "medium",
      "category": "bug"
    }]
  }'
```

**Multiple issues at once:**

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issues": [
      {
        "issue_id": "MY-002",
        "title": "Fix N+1 query in dashboard list",
        "description": "The GET /api/v1/dashboard/ endpoint issues a separate query per dashboard for owners. Use a joined load instead.",
        "severity": "high",
        "category": "performance",
        "file_paths": ["superset/dashboards/api.py"]
      },
      {
        "issue_id": "MY-003",
        "title": "Add unit test for date parser",
        "description": "superset/utils/date_parser.py has no test coverage for ISO 8601 durations. Add pytest tests.",
        "severity": "low",
        "category": "test_failure",
        "file_paths": ["superset/utils/date_parser.py"]
      }
    ]
  }'
```

**Custom payload from a JSON file:**

```bash
# Save your payload to a file:
cat > my_payload.json << 'EOF'
{
  "event_type": "security_scan",
  "repo": "mustansirali/superset",
  "issues": [{
    "issue_id": "SEC-001",
    "title": "Update vulnerable dependency",
    "description": "cryptography<42.0.0 has a known CVE. Bump to >=42.0.0 in requirements.",
    "severity": "critical",
    "category": "dependency",
    "file_paths": ["requirements/base.txt"],
    "labels": ["security", "dependencies"]
  }]
}
EOF

# Send it:
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d @my_payload.json
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

Only `issue_id`, `title`, and `description` are required per issue. All other
fields are optional and help Devin focus its remediation.

## Signature Verification

If `WEBHOOK_WEBHOOK_SECRET` is set, the server requires a valid
`X-Webhook-Signature` header on every request:

```python
import hashlib, hmac, json

body = json.dumps(payload).encode()
signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
# Send as header: X-Webhook-Signature: sha256=abc123...
```

## Dashboard

Open **<http://localhost:8000/dashboard>** in your browser to see a
real-time analytics dashboard showing:

- **Summary cards** — total events, issues, completed, failed, pending,
  PRs created, and success rate.
- **Task Status chart** — doughnut chart of session outcomes.
- **Throughput Over Time** — stacked bar chart of completed/failed/pending
  per event.
- **Recent Events table** — reverse-chronological list with status badges.

The dashboard auto-refreshes every 10 seconds. Click **Refresh** for an
immediate update.

For programmatic access, `GET /api/stats` returns the same data as JSON.

### Analytics Persistence

All session analytics are saved to a local JSON file
(`webhook_automation/data/analytics.json` by default). This means:

- Dashboard data **survives server restarts** — historical runs are
  preserved and the success rate reflects all sessions ever tracked.
- When using Docker Compose, a named volume (`analytics-data`) keeps the
  data file across container recreations.
- Override the storage path with `WEBHOOK_ANALYTICS_FILE` in your `.env`.

## Monitoring Remediation Progress

After sending a webhook, poll the reports endpoint:

```bash
# List all reports
curl http://localhost:8000/reports

# Get specific report (use report_key from webhook response)
curl http://localhost:8000/reports/<report_key>
```

Each report shows per-issue session status, Devin session URLs, and any PRs
created.

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest webhook_automation/tests/ -v
```

## Docker Details

**Build manually:**

```bash
cd webhook_automation
docker build -t webhook-automation .
docker run --rm -p 8000:8000 --env-file .env webhook-automation
```

**Custom port (docker compose):**

Set `WEBHOOK_PORT` in `.env` to change the host-side port. The container
always listens on 8000 internally:

```bash
# .env
WEBHOOK_PORT=8080
# → accessible at http://localhost:8080
```

**View logs:**

```bash
docker compose logs -f
```
