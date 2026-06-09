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
                                   GET /dashboard                 PRs on GitHub
                                          ▼
                                   ┌──────────────┐
                                   │  Analytics    │
                                   │  Dashboard    │
                                   └──────────────┘
```

### Flow

1. An external trigger sends `POST /webhook` with one or more issue descriptions.
2. The server validates the payload (and optionally verifies an HMAC signature).
3. For each issue, a Devin session is created via the
   [Devin v3 API](https://docs.devin.ai/api-reference/overview).
4. Sessions are polled until they reach a terminal status.
5. Results are persisted to a local JSON file and surfaced via the analytics
   dashboard and the reports API.

---

## Running with Docker (Recommended)

### 1. Configure environment

```bash
cd webhook_automation
cp .env.example .env
```

Edit `.env` with your Devin credentials (find them at
[Settings → Service Users](https://app.devin.ai) in the Devin dashboard):

```
WEBHOOK_DEVIN_API_KEY=cog_your_api_key_here
WEBHOOK_DEVIN_ORG_ID=org-your_org_id_here
```

> **Tip:** Do not wrap values in quotes — write `WEBHOOK_DEVIN_API_KEY=cog_abc123`,
> not `WEBHOOK_DEVIN_API_KEY='cog_abc123'`.

### 2. Start the server

```bash
docker compose up -d --build
```

Verify it's running:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### 3. View logs

```bash
docker compose logs -f
```

### 4. Stop the server

```bash
docker compose down
```

> Analytics data is stored in a Docker named volume (`analytics-data`) and
> persists across `docker compose down` / `docker compose up` cycles. To
> wipe analytics, run `docker volume rm webhook_automation_analytics-data`.

---

## Testing the Webhook (curl)

With the server running (`docker compose up -d`), fire payloads from any
terminal. All commands below assume the default port `8000` — adjust if you
changed `WEBHOOK_PORT` in `.env`.

### Quick smoke test

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Single issue

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
      {
        "issue_id": "TEST-001",
        "title": "Missing type hints in utils/date_parser.py",
        "description": "Add type annotations to parse_human_datetime in superset/utils/date_parser.py.",
        "severity": "medium",
        "category": "type_error",
        "file_paths": ["superset/utils/date_parser.py"]
      }
    ]
  }'
```

### Multiple issues in one payload

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
      {
        "issue_id": "TEST-002",
        "title": "Remove unused import in views/api.py",
        "description": "Remove unused flask jsonify import in superset/views/api.py.",
        "severity": "low",
        "category": "lint",
        "file_paths": ["superset/views/api.py"]
      },
      {
        "issue_id": "TEST-003",
        "title": "Add docstring to DashboardDAO.copy_dashboard",
        "description": "Add a docstring to copy_dashboard in superset/daos/dashboard.py describing params and return type.",
        "severity": "low",
        "category": "other",
        "file_paths": ["superset/daos/dashboard.py"]
      }
    ]
  }'
```

### Security / dependency issue

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "issue_remediation",
    "repo": "mustansirali/superset",
    "issues": [
      {
        "issue_id": "SEC-001",
        "title": "Update vulnerable dependency",
        "description": "A dependency in requirements/base.txt has a known CVE. Bump to the latest patched release.",
        "severity": "critical",
        "category": "dependency",
        "file_paths": ["requirements/base.txt"],
        "labels": ["security", "dependencies"]
      }
    ]
  }'
```

### Custom payload from a JSON file

```bash
cat > my_payload.json << 'EOF'
{
  "event_type": "custom_scan",
  "repo": "mustansirali/superset",
  "issues": [
    {
      "issue_id": "CUSTOM-001",
      "title": "Your custom issue title",
      "description": "Describe the issue and what needs to change.",
      "severity": "high",
      "category": "bug",
      "file_paths": ["path/to/file.py"],
      "labels": ["custom"]
    }
  ]
}
EOF

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d @my_payload.json
```

---

## Testing the Analytics Dashboard

### Open the dashboard

Navigate to **<http://localhost:8000/dashboard>** in your browser.

The dashboard shows:
- **Summary cards** — total events, issues, completed, failed, pending,
  PRs created, and success rate.
- **Task Status chart** — doughnut chart of session outcomes.
- **Throughput Over Time** — stacked bar chart of completed/failed/pending
  per event.
- **Recent Events table** — reverse-chronological list with status badges.

It auto-refreshes every 10 seconds. Click **Refresh** for an immediate update.

### Verify dashboard updates

1. Open the dashboard in your browser.
2. Fire a webhook payload (see curl examples above).
3. Wait up to 10 seconds (or click Refresh) — the cards and table should
   reflect the new event.

### Get analytics as JSON

```bash
curl -s http://localhost:8000/api/stats | python3 -m json.tool
```

Response includes `overview`, `status_breakdown`, and `timeline` objects.

### Verify persistence across restarts

```bash
# Fire a payload
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"issues":[{"issue_id":"PERSIST-001","title":"Persistence test","description":"Verify data survives restart."}]}'

# Check the stats
curl -s http://localhost:8000/api/stats | python3 -m json.tool

# Restart the container
docker compose restart

# Verify data is still there
curl -s http://localhost:8000/api/stats | python3 -m json.tool
```

The `total_events` count should be the same before and after the restart.

---

## Checking Reports

```bash
# List all remediation reports
curl -s http://localhost:8000/reports | python3 -m json.tool

# Get a specific report (use the report_key from the webhook response)
curl -s http://localhost:8000/reports/<report_key> | python3 -m json.tool
```

Each report shows per-issue session status, Devin session URLs, and any PRs
created.

---

## Using the Built-in Trigger Script

If you're running the server locally (not Docker), the repo includes a Python
trigger CLI that sends pre-built sample payloads:

```bash
# From repo root (superset/), with venv activated:
python -m webhook_automation.trigger --payload single
python -m webhook_automation.trigger --payload multi
python -m webhook_automation.trigger --payload security
```

The trigger reads `WEBHOOK_PORT` from your `.env` automatically. Override the
URL with `--url`:

```bash
python -m webhook_automation.trigger --payload single --url http://localhost:9090/webhook
```

---

## Running Locally (without Docker)

> Run all commands from the **repo root** (`superset/`), not from inside
> `webhook_automation/`.

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r webhook_automation/requirements.txt

# 3. Create your .env
cp webhook_automation/.env.example webhook_automation/.env
# Edit webhook_automation/.env with your API key and org ID

# 4. Start the server
python -m webhook_automation

# 5. Fire a test payload (separate terminal, same venv)
python -m webhook_automation.trigger --payload single

# Or use any of the curl commands above
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest webhook_automation/tests/ -v
```

18 tests cover the server endpoints, Devin API client, and analytics
persistence layer.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{"status":"ok"}` |
| `POST` | `/webhook` | Receive issue payloads, kick off Devin sessions |
| `GET` | `/reports` | List all remediation reports |
| `GET` | `/reports/{key}` | Get a specific report by key |
| `GET` | `/dashboard` | Real-time analytics dashboard (HTML) |
| `GET` | `/api/stats` | Aggregated analytics data (JSON) |

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

## Environment Variables

Set these in `webhook_automation/.env` (auto-loaded) or as env vars:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_DEVIN_API_KEY` | Yes | — | Devin API key (starts with `cog_`) |
| `WEBHOOK_DEVIN_ORG_ID` | Yes | — | Devin organization ID |
| `WEBHOOK_WEBHOOK_SECRET` | No | — | HMAC-SHA256 secret for signature verification |
| `WEBHOOK_TARGET_REPO` | No | `mustansirali/superset` | Target repo for Devin sessions |
| `WEBHOOK_POLL_INTERVAL_SECONDS` | No | `30` | Session polling interval in seconds |
| `WEBHOOK_ANALYTICS_FILE` | No | `webhook_automation/data/analytics.json` | Path to analytics persistence file |
| `WEBHOOK_HOST` | No | `0.0.0.0` | Server bind host |
| `WEBHOOK_PORT` | No | `8000` | Server bind port (also controls Docker host port) |

## Signature Verification

If `WEBHOOK_WEBHOOK_SECRET` is set, the server requires a valid
`X-Webhook-Signature` header:

```python
import hashlib, hmac, json

body = json.dumps(payload).encode()
signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
# Send as: X-Webhook-Signature: sha256=abc123...
```

## Docker Details

**Build the image manually:**

```bash
cd webhook_automation
docker build -t webhook-automation .
docker run --rm -p 8000:8000 --env-file .env webhook-automation
```

**Custom host port:**

Set `WEBHOOK_PORT` in `.env`. The container always listens on 8000 internally;
`docker-compose.yml` maps `${WEBHOOK_PORT:-8000}:8000`:

```bash
# In .env:
WEBHOOK_PORT=9090
# → accessible at http://localhost:9090
```
