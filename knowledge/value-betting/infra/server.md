# Server

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> FastAPI server providing SSE streaming, REST API, and background task management.

---

## Architecture

**Source:** `server/main.py` (~67KB), `server/state.py` (~12KB)

The server is a FastAPI application that:
1. Runs the scraping/devig pipeline as background tasks
2. Serves live picks via Server-Sent Events (SSE)
3. Provides REST endpoints for health checks, analytics, and control
4. Manages in-memory state (odds catalogue) decoupled from the pipeline loop

---

## Ports

| Sport | Port | Chrome CDP Port |
|-------|------|-----------------|
| NBA | 8800 | 9223 |
| MLB | 8803 | 9224 |
| NRL | 8804 | — (OpticOdds only) |
| AFL | 8805 | — (OpticOdds only) |

---

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/stream` | GET (SSE) | Live pick stream to dashboard |
| `/api/v1/health` | GET | Full health check (all layers) |
| `/api/v1/health/quick` | GET | Quick health (sources + tracker) |
| `/api/v1/health/data` | GET | 7-day data quality metrics |
| `/api/v1/picks` | GET | Current tracked picks |
| `/api/v1/results` | GET | Historical results + analytics |
| `/api/v1/theories` | GET | Active theories |

---

## State Management

`server/state.py` (AppState) holds the in-memory odds catalogue:
- **Event-driven dirty tracking:** When pipeline writes new odds, state is marked dirty
- **Decoupled:** FastAPI request loop reads state independently from scraper loop
- **No shared locks on hot paths:** Pipeline writes, server reads — minimal contention

---

## Background Task Lifecycle

Tasks (scraper cycles, resolver runs) are managed with a `_start_task` wrapper that:
- Tracks running tasks by name
- Provides a done callback for cleanup
- Logs task failures without crashing the server
- Enables graceful shutdown

---

## Relay Mode

When `RELAY_MODE=1`, the server aggregates picks from other sport servers instead of running its own pipeline. Used by the push worker (`server/ev_push_worker.py`) to combine all 4 sports into a single stream for the VPS.

---

## Related Pages
- [[dashboard]] — Frontend that consumes SSE
- [[deployment]] — Where the server runs
- [[tracker]] — Pick tracking subsystem
- [[resolver]] — Auto-resolution subsystem
