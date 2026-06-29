# Infrastructure Cost Optimisation Agent

An agentic FinOps tool that pulls **AWS or GCP** cost and utilisation data, runs
a **LangGraph** agent to detect cost-saving opportunities, validates each one
through an **LLM (Claude)** that assesses feasibility and risk, and surfaces the
approved recommendations in a **React** dashboard. Pick the cloud provider per
run from a dropdown in the UI.

It ships with a deterministic **mock data mode** so the entire pipeline runs
end-to-end with no cloud or Anthropic credentials.

## What it detects

The detectors are cloud-neutral: they operate on a normalized resource model
(`compute` / `disk` / `snapshot`) so the same logic serves both AWS and GCP.

| Detector | Fires when | AWS / GCP resources | Savings estimate |
|---|---|---|---|
| **Idle Compute** | A running instance averages CPU below the idle threshold over the lookback window | EC2 / Compute Engine VM | Full on-demand monthly cost of the instance |
| **Unattached Disk** | A disk is in the `available` state (attached to nothing) | EBS volume / Persistent Disk | Monthly storage cost for the disk |
| **Old Snapshots** | A snapshot is older than the retention threshold | EBS / PD snapshot | Monthly snapshot storage cost |

Each finding is then reviewed by the LLM validator (Claude, via the Anthropic
SDK), which assesses feasibility and risk and returns `approve` / `needs_review`
/ `reject` plus reasoning and risk factors. With no `ANTHROPIC_API_KEY` set, a
deterministic heuristic stands in so the app still runs end-to-end.

> **Validator performance:** validator calls are sequential in the MVP (~5–15s
> for 10–20 findings on Sonnet). A future improvement is to fan them out with
> `asyncio.gather` over the Anthropic async client. Estimated cost is well under
> $0.05 per run for ~15 findings on `claude-sonnet-4-6`.

## Architecture

```
React UI (Vite)  ──HTTP──►  FastAPI
   (provider: aws|gcp)      └─ LangGraph agent:
                                 ingest
                                   ├─► detect_idle_compute    ┐
                                   ├─► detect_unattached_disk ├─► aggregate ─► validate (LLM) ─► SQLite
                                   └─► detect_old_snapshots   ┘
                            └─ Cloud layer: CloudClient protocol
                                 ├─ AWS  (boto3 + deterministic mock)
                                 └─ GCP  (mock; real SDK client stubbed)
```

A `CloudClient` protocol (`app/cloud/base.py`) normalizes each provider's
resources into the same shapes, so the detectors stay provider-agnostic. The
provider is chosen per run and tags every finding. GCP currently runs on mock
data — `RealGcpClient` is a stub for a future google-cloud SDK integration.

The three detectors run as a parallel LangGraph superstep and merge their
findings into shared state via a list reducer. `aggregate` is the fan-in
barrier; `validate` orders findings by savings and runs the LLM review.

## Quick start (Docker)

```bash
docker compose up --build
```

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs

Runs in mock mode by default. To enable the real Claude validator, export
`ANTHROPIC_API_KEY` before starting (otherwise a deterministic heuristic
validator is used).

## Quick start (local)

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

Click **Run Analysis** in the UI. The frontend triggers a run, polls its status,
and renders the recommendations with their validator verdicts.

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust as needed:

| Variable | Default | Purpose |
|---|---|---|
| `MOCK_CLOUD` | `true` | Use deterministic mock data instead of real cloud APIs |
| `CLOUD_PROVIDER` | `aws` | Default provider when a request omits one (`aws` \| `gcp`) |
| `ANTHROPIC_API_KEY` | _empty_ | Enables the Claude-backed validator; falls back to a heuristic if unset |
| `VALIDATOR_MODEL` | `claude-sonnet-4-6` | Model used by the LLM validator |
| `AWS_REGION` | `us-east-1` | Region for boto3 calls |
| `GCP_REGION` | `us-central1` | Region for GCP calls |
| `GCP_PROJECT_ID` | _empty_ | GCP project (used once the real GCP client is wired up) |
| `DATABASE_URL` | `sqlite:///./app.db` | Storage |
| `LOG_LEVEL` | `INFO` | Root log level |
| `IDLE_CPU_PERCENT_THRESHOLD` | `5.0` | Idle compute CPU cutoff |
| `IDLE_LOOKBACK_DAYS` | `14` | CPU-metrics lookback window |
| `SNAPSHOT_AGE_DAYS_THRESHOLD` | `180` | Old-snapshot cutoff |

The provider is selected **per run** from the dashboard dropdown (or the
`provider` field in the `POST /api/analysis/run` body); `CLOUD_PROVIDER` is only
the fallback default.

### Real AWS mode

Set `MOCK_CLOUD=false` (with `CLOUD_PROVIDER=aws`) and provide credentials via
the standard boto3 chain (env vars, shared config, or an instance role). The
agent then uses:

- `ec2:DescribeInstances`, `ec2:DescribeVolumes`, `ec2:DescribeSnapshots`
- `cloudwatch:GetMetricStatistics` (CPU utilisation)

A read-only IAM policy is sufficient — the tool only *surfaces* recommendations;
it never modifies or deletes resources.

### Real GCP mode

Not yet implemented. `RealGcpClient` is a stub that raises `NotImplementedError`;
run GCP analyses with `MOCK_CLOUD=true`. Wiring it up means implementing the
`CloudClient` methods over `google-cloud-compute` and `google-cloud-monitoring`.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + mock mode |
| `GET` | `/api/health` | Mode + LLM status |
| `POST` | `/api/analysis/run` | Trigger an analysis run — optional JSON body `{ "provider": "aws"\|"gcp", "region"?: string }` (returns `run_id`, runs in background) |
| `GET` | `/api/analysis/{run_id}` | Run status + recommendation count |
| `GET` | `/api/runs` | Recent runs |
| `GET` | `/api/recommendations?run_id=` | Recommendations (optionally filtered by run) |

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest
```

Covers each detector against mock data, the full graph integration, and the
API trigger → fetch flow.

## Conventions

- Money is stored as integer **cents**; the API also exposes a USD float.
- Timestamps are UTC ISO-8601 at the API boundary.
- Recommendation and run IDs are server-generated UUIDs; `run_id` is threaded
  through every log line.
- Recommendations are stored with `validation_status` defaulting to `pending`;
  the validator then sets `approve` / `needs_review` / `reject`. If the validator
  returns output that cannot be parsed into its schema, the finding falls back to
  `needs_review` and the raw output is retained.

## Out of scope (MVP)

Auth / multi-tenancy, automatic remediation, realtime updates, Reserved
Instance / Savings Plan analysis, and historical trend dashboards.
