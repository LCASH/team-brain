# Tracker

## Status: current
## Last verified: 2026-04-09 (updated with weight guard details, disable-via-env)

> Records odds changes for tracked picks over time.

---

## What It Does

**Source:** `server/tracker.py` (~42KB)

When a pick passes a theory's thresholds, the tracker:
1. Records the initial odds snapshot to `nba_tracked_picks`
2. Appends every subsequent odds change to `trail_entries`
3. Maintains in-memory cache for fast lookups
4. Gates entry by active theories (pick must pass at least one)

---

## Trail Entries (Append-Only Pattern)

The key optimization: instead of updating a JSONB array on the tracked pick (20-100KB per update), each odds change is a cheap INSERT (~200 bytes) to the `trail_entries` table.

```
trail_entries:
  pick_id (FK to nba_tracked_picks)
  timestamp
  book_odds
  sharp_odds
  ev_pct
  confidence
```

**Impact:** 90-95% reduction in Supabase disk I/O. This was a critical fix — the old JSONB patch pattern was hitting Supabase write limits.

---

## Tracked Pick Columns

`nba_tracked_picks` has denormalized scalar columns for current state:
- `opening_odds` — first seen odds
- `current_odds` — latest soft book odds
- `current_line` — latest line
- `sharp_hash` — hash of sharp book consensus (for quick comparison)

These are updated on each cycle, providing quick reads without scanning trail_entries.

---

## Theory Gating

A pick enters tracking only when it passes at least one active theory's thresholds. Once tracked, it continues to be monitored even if it later falls below thresholds (to capture the full odds trail for analysis).

---

## Weight Guard (Fixed 2026-04-09)

The tracker calculates true probability using sharp book weights from each theory. Three calculation points in `tracker.py` (lines ~289, ~332, ~401) all apply the same guard:

```python
w = theory_weights.get(str(book_id), 0)  # absent book = weight 0
if w <= 0:
    continue
```

**Key change:** Default for absent books changed from `1.0` to `0`. Without this, a theory configured for 4 sharp books would actually include 7+ (every book with data got weight 1.0). The server tracker was already extracting theory IDs correctly (unlike the dashboard — see [[dashboard]] for that bug). The fix was ensuring the fallback value was `0` not `1.0`.

---

## Disable via Environment Variable

On the mini PC, the tracker and resolver can be disabled via:

```
DISABLE_TRACKER=1
DISABLE_RESOLVER=1
```

This allows the mini PC to run scrapers only (push worker sends data to VPS where tracking/resolving happens). Without this, the mini PC was running redundant tracker/resolver instances.

---

## Related Pages
- [[theories]] — What gates pick entry
- [[resolver]] — What grades tracked picks
- [[database]] — Table schema
