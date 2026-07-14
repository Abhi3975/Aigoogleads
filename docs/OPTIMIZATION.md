# Autonomous Optimization Engine

Continuously monitors Google Ads campaigns, analyzes performance, decides
optimizations, validates them against safety rules, executes the approved ones,
and records an explainable audit trail — running automatically in the background.

## The loop

```
Celery Beat (schedule)
   ├─ hourly        → fetch_all_metrics   → per-account metrics fetch + store
   ├─ every 6h      → run_all_optimizations → per-account optimization loop
   └─ daily 06:00   → generate_all_reports  → daily performance report + notification

Optimization loop (OptimizationEngine.run):
  Metrics collection ─▶ Analytics Agent ─▶ Recommendation Agent
        ─▶ Safety Decision Engine (validate + clamp)
        ─▶ Execution (Google Ads tools, if auto-execute)
        ─▶ OptimizationLog (audit + explanation) + Notifications
```

The Analytics and Recommendation steps reuse the M5 agents; execution reuses the
M5 Google Ads toolset. The **Safety Decision Engine** and **audit trail** are the
new layers.

## Safety Decision Engine (`services/safety.py`)

Pure, unit-tested. Validates each AI recommendation against the org's
`OptimizationPolicy`:

- **Confidence gate** — reject below `min_confidence`.
- **Budget** — clamp increases to `max_budget_increase_pct`, decreases to
  `max_budget_decrease_pct`.
- **Bid** — clamp change to `max_bid_change_pct`.
- **Pause** — require `min_clicks_required` clicks and `min_days_active` days.
- **Unsupported actions** — anything outside budget/pause/enable/bid is rejected
  for autonomous execution.

Only approved (and, if `auto_execute`, executed) actions touch Google Ads.

## New files

| Area | Files |
| --- | --- |
| Models | `models/metrics.py` (CampaignMetric, KeywordMetric, AdMetric, DailyPerformanceReport), `models/optimization.py` (OptimizationPolicy, OptimizationLog), `models/notification.py` |
| Services | `services/metrics.py`, `services/safety.py`, `services/optimization_engine.py`, `services/notification.py`, `services/email.py` |
| Worker | `worker/celery_app.py`, `worker/runtime.py`, `worker/jobs.py`, `worker/tasks.py` |
| Repos | `repositories/metrics.py`, `repositories/optimization.py`, `repositories/notification.py` |
| Schemas | `schemas/optimization.py`, `schemas/notification.py` |
| API | `api/v1/endpoints/optimization.py`, `api/v1/endpoints/notifications.py` |
| Tests | `tests/test_optimization.py` |

## API endpoints (under `/api/v1`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/organizations/{org}/optimization/policy` | member | Safety policy |
| PATCH | `/organizations/{org}/optimization/policy` | admin | Update rules / autonomy toggles |
| POST | `/organizations/{org}/optimization/run` | admin | Trigger the loop for an account |
| GET | `/organizations/{org}/optimization/logs` | member | Optimization audit trail |
| GET | `/organizations/{org}/notifications` | member | Notifications (`?unread`) |
| GET | `/organizations/{org}/notifications/unread-count` | member | Unread count |
| POST | `/organizations/{org}/notifications/{id}/read` | member | Mark read |
| POST | `/organizations/{org}/notifications/read-all` | member | Mark all read |

## Database changes

New tables: `campaign_metrics`, `keyword_metrics`, `ad_metrics`,
`daily_performance_reports`, `optimization_policies`, `optimization_logs`,
`notifications`. Migration: `*_add_optimization_and_metrics_tables.py`.

## Running the workers

Via Docker Compose (already wired): the `worker` and `beat` services run
`celery -A app.worker.celery_app worker` and `... beat`. Locally:

```bash
cd backend
uv run celery -A app.worker.celery_app worker --loglevel=INFO
uv run celery -A app.worker.celery_app beat --loglevel=INFO
```

Autonomous execution only runs for organizations that set
`OptimizationPolicy.enabled = true` (and `auto_execute = true` to apply changes);
otherwise the loop produces recommendations in `pending` state for review.

## Verification

`tests/test_optimization.py`: safety-engine unit tests (budget/bid clamping,
pause thresholds, confidence gate, unsupported actions), the full loop with fake
LLM + fake Google Ads client (applies a clamped budget change, rejects an unsafe
pause, writes audit logs + notifications), policy get/update, notification
read-flow, and target discovery respecting the `enabled` flag.
