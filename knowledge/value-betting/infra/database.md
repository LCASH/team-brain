# Database

## Status: current
## Last verified: 2026-04-09 (added sharp_clv_pct, dead infrastructure note)

> Supabase PostgreSQL schema for the VB Scanner.

---

## Project

**Supabase ref:** `gpvyyyirrswmfirfwyli` (ap-southeast-2)
**Client:** `ev_scanner/db.py` (~7.8KB) — minimal httpx ORM, upsert-only pattern

---

## Core Tables

All tables use a `sport` column for multi-sport filtering.

| Table | Purpose | Write Pattern |
|-------|---------|--------------|
| `nba_tracked_picks` | Live picks with current odds, results, CLV | Upsert per cycle + resolver PATCH |
| `trail_entries` | Append-only odds changes | INSERT only (~200 bytes each) |
| `nba_ev_picks` | Historical EV picks snapshot | Upsert per cycle |
| `nba_optimization_runs` | Theory configs + Brier/log-loss | Manual / calibrator |
| `nba_calibration` | Our values vs BetIQ comparison | Pipeline (90-day retention) |
| `nba_game_results` | Player stats from OpticOdds | Resolver |
| `nba_resolved_picks` | Picks with outcomes + CLV | Resolver |
| `nba_player_mapping` | OpticOdds player ID lookup | CLV tracker |
| `nba_closing_odds` | Best closing prices per market | Resolver |
| `nba_backtest_runs` | Historical backtest results | Calibrator |

---

## Key Design Decisions

### Upsert-only pattern
The DB client uses `Prefer: resolution=merge-duplicates` for batch writes. No deletes in the pipeline — old data ages out via retention policies.

### Denormalized scalars on tracked_picks
`opening_odds`, `current_odds`, `current_line`, `sharp_hash` are scalar columns on `nba_tracked_picks` instead of requiring a join to trail_entries. This enables fast reads for the dashboard.

### Trail I/O optimization
Each odds change is a cheap INSERT to `trail_entries` rather than a JSONB patch on the parent pick. Reduces Supabase disk I/O by 90-95%.

### Sport column
All tables include a `sport` column (e.g., "nba", "mlb") so all 4 sports share the same tables. Queries filter by sport.

---

## Dead Infrastructure

**`nba_odds_history`** — This table exists but **no active code writes to it**. The functions in `ev_scanner/clv.py` (`fetch_sharp_closing_odds_batch()`, `fetch_closing_odds_batch()`) query this table, but they are never called. The working data source for closing odds is `trail_entries` with `trail_type='sharp'`.

---

## Migrations

Located in `supabase/migrations/`:
- `000_bootstrap_all.sql` — Create public schema + policies
- `001_full_schema.sql` — All tables
- `010_lean_tracked_picks.sql` — Scalar columns optimization
- `012_trail_entries.sql` — Append-only trail table
- `016_sharp_clv.sql` — Add `sharp_clv_pct FLOAT` to nba_tracked_picks (2026-04-09)

---

## RLS

Tables have Row Level Security policies. The pipeline uses the service role key for writes. Dashboard reads use the anon key.

---

## Related Pages
- [[tracker]] — Writes to tracked_picks and trail_entries
- [[resolver]] — Writes to resolved_picks and game_results
- [[calibration]] — Reads/writes optimization_runs
- [[deployment]] — Where the DB is accessed from
