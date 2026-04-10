# Dashboard

## Status: current
## Last verified: 2026-04-09 (updated with P0-P3 fixes)

> Static HTML frontend with client-side devig, served from VPS.

---

## Architecture

**Source:** `dashboard/index.html` (~100KB)

Single static HTML file served by the VPS at `http://170.64.213.223:8802/`. Receives live updates via SSE. Does **client-side devig calculation** — re-computes true probabilities and EV from raw odds using same algorithms as server.

---

## Features

### Stats Bar
- Soft book count, OpticOdds count, total markets, +EV picks
- Active theories count, performance badge (W/L + ROI)

### EV Picks Table
- Sortable by EV%, confidence, weighted EV, player, prop
- **True odds column** (purple) — primary theory's devigged true odds for sanity checking
- Click to expand per-theory breakdown

### Sharp Detail Panel
- Click sharp count → expands per-book breakdown per theory
- Shows **Over and Under odds** for each sharp book (both sides for devig verification)
- Devigged prob, adjusted prob, interpolation method, weight
- Empty-state message when no sharp data available

### Theory Editor
- Create/edit theories in dashboard
- Book weight defaults to **0** for absent books (not 1.0 — prevents including unintended books)

### Results Tab
- Multi-sport selector, W/L by theory/side/prop/EV bucket
- Cumulative P/L chart, auto-loads on first visit

---

## Key Bug Fix: Weight Fallback (2026-04-09)

`computeTrueProb()` was iterating ALL 8 `SHARP_IDS` regardless of theory config. Absent books got weight 1.0, so Calibrated (4 books) was actually using 7. **Dashboard-only bug** — server tracker was already correct.

**Fix:** Extract `theoryIds` from weight keys, iterate only those. Added `if (w <= 0) continue` guard. Theory editor now saves weight 0 as "exclude" (not 1.0).

---

## Data Flow

```
Mini PC (scrapers) → Push Worker → VPS SSE → Dashboard (client-side devig)
```

After dashboard code changes, push to VPS:
```bash
curl -X POST http://170.64.213.223:8802/push/dashboard --data-binary @dashboard/index.html -H "Content-Type: text/html"
```

---

## Related Pages
- [[server]] — Serves the dashboard and SSE stream
- [[theories]] — Weight config affects client-side devig
- [[calibration]] — Comparison tab is the calibration feedback loop
