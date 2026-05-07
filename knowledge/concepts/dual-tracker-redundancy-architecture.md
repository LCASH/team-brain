---
title: "Dual-Tracker Redundancy Architecture"
aliases: [dual-tracker, mini-pc-vps-redundancy, tracker-dedup, supabase-dual-write]
tags: [value-betting, architecture, redundancy, supabase, operations]
sources:
  - "daily/lcash/2026-05-02.md"
created: 2026-05-02
updated: 2026-05-02
---

# Dual-Tracker Redundancy Architecture

The value betting scanner operates two independent trackers — one on the mini PC (inside sport servers on ports 8800/8803) and one on the VPS (relay tracker at 170.64.213.223:8802) — both writing to the same Supabase database. This is a deliberate redundancy design, not a misconfiguration. Picks use deterministic SHA256 IDs based on `(sport|player|prop|side|line|date|soft_book)` with Supabase `on_conflict=id` upsert semantics, preventing duplicates when both trackers process the same market. The VPS tracker is the primary source feeding the dashboard, while the mini PC tracker provides direct Supabase writes that survive VPS outages.

## Key Points

- **Two independent trackers by design**: mini PC tracker (inside sport servers 8800, 8803) + VPS tracker (relay at port 8802) both write to Supabase
- **Deduplication via deterministic SHA256 IDs**: pick ID = hash of `(sport|player|prop|side|line|date|soft_book)`, upserted with `on_conflict=id` — same market always produces same ID regardless of which tracker evaluates it
- **Odds freshness enforced at gate**: soft book odds must be ≤300s old, sharp books ≤600s old; stale odds are silently skipped by the tracker before EV computation
- **VPS is primary dashboard source**: dashboard at 170.64.213.223:8802 shows all sources (mini PC OpticOdds/Bet365 + VPS SSE/prediction markets) deduplicated per book with `captured_at` timestamp
- **Mini PC keeps picks flowing during VPS outages**: direct Supabase writes from mini PC bypass the VPS entirely — dashboard is inaccessible but picks are still tracked
- System remained operational on 2026-05-02 when mini PC trackers stalled (NBA 383s lag, MLB 0 cycles) because VPS relay was actively feeding odds

## Details

### Architecture

The dual-tracker architecture emerged from the scanner's multi-environment deployment:

| Component | Mini PC | VPS |
|-----------|---------|-----|
| Tracker location | Inside sport servers (8800 NBA, 8803 MLB) | Relay tracker on port 8802 |
| Data source | Local scrapers (Bet365 CDP, OpticOdds REST) | Push payloads from mini PC + SSE from OpticOdds |
| Write target | Supabase (direct) | Supabase (direct) |
| Dashboard role | None (no web interface) | Primary — serves dashboard, SSE streams |
| Failure impact | Loses scraper-originated data | Loses dashboard + SSE + relay tracking |

Both trackers independently evaluate markets against configured theories, compute EV, and write picks to the same Supabase tables. The deterministic pick ID ensures that when both trackers evaluate the same market and trigger a pick, only one row exists in the database — the upsert semantics handle the dedup transparently.

### Why Not a Single Tracker?

A single tracker (either on mini PC or VPS) would be simpler but creates a single point of failure. The dual-tracker design was validated on 2026-05-02 when the mini PC's NBA tracker lagged 383 seconds and MLB tracker showed 0 cycles — but the dashboard continued showing data because the VPS relay tracker was operational with fresh odds from SSE streams and push payloads.

The VPS tracker also covers data sources that the mini PC tracker cannot access directly: SSE-streamed odds from OpticOdds for prediction markets and niche leagues. The mini PC tracker covers Bet365 game scraper data that arrives locally before being pushed to the VPS. Together, they provide broader coverage than either could alone.

### Deduplication Mechanics

The pick ID hash includes `soft_book_id`, meaning the same player+prop+side+line+date generates separate rows per soft book — this is intentional for per-book performance analysis (see [[concepts/pick-dedup-multi-theory-limitation]]). The dedup operates at the individual book level, not the market level.

When both trackers process the same market at slightly different times, the upsert behavior is:
1. First tracker writes the pick with its computed `triggered_ev` and `triggered_at` timestamp
2. Second tracker generates the same pick ID, attempts upsert
3. Supabase `on_conflict=id` updates the row — last writer wins for non-ID columns
4. Trail entries (Phase B) use the pick ID as a foreign key, so both trackers' trail writes accumulate correctly

The "last writer wins" behavior is acceptable because both trackers compute EV from the same theory configurations and similar (though not identical) odds data. The triggered_ev values should be close; any difference reflects timing rather than methodology.

### Freshness Gates

Both trackers enforce identical freshness gates to prevent stale data from producing phantom picks:
- Soft book odds: ≤300 seconds old (`MAX_SOFT_ODDS_AGE_S`)
- Sharp book odds: ≤600 seconds old (`MAX_SHARP_ODDS_AGE_S`)

These gates operate independently on each tracker. A market with fresh odds on the VPS but stale odds on the mini PC will produce a pick from the VPS tracker only — the mini PC tracker silently skips it. This means the `sharp_count` column in the picks table can vary depending on which tracker wrote the row, reflecting the data freshness at that specific tracker's evaluation time.

### Dashboard Data Union

The dashboard displays a union of all data sources, deduplicated per book with `captured_at` timestamps showing the freshness of each source. The user sees odds from OpticOdds (via both mini PC REST polling and VPS SSE), Bet365 game scraper (via mini PC only), and prediction markets (via VPS SSE). The dedup layer ensures that the same market from the same book appears once, with the most recent `captured_at` timestamp.

## Related Concepts

- [[concepts/pick-dedup-multi-theory-limitation]] - The deterministic pick ID architecture that enables dual-tracker dedup; soft_book_id in the hash is by design for per-book analysis
- [[concepts/value-betting-operational-assessment]] - Weakness #6 (no redundancy): the dual-tracker partially addresses this by providing write-path redundancy, though the VPS remains a single point of failure for dashboard access
- [[concepts/vps-sse-cascade-silent-crash]] - When the VPS crashes, the dashboard dies but mini PC picks continue to Supabase — the dual-tracker's redundancy value is realized during VPS outages
- [[concepts/push-worker-orphan-accumulation]] - Push workers feed data from mini PC to VPS; push worker death creates a data gap on the VPS tracker while the mini PC tracker continues independently
- [[connections/operational-compound-failures]] - The dual-tracker reduces the blast radius of individual component failures; mini PC tracker stalling doesn't zero out picks because VPS tracker compensates

## Sources

- [[daily/lcash/2026-05-02.md]] - Dual-tracker architecture confirmed as intentional design; mini PC NBA 383s lag + MLB 0 cycles while VPS relay actively feeding dashboard; dedup via SHA256 pick IDs with on_conflict=id upsert; freshness gates: soft ≤300s, sharp ≤600s; dashboard shows union of all sources; user concern about "different trackers in different places" resolved (Session 08:21)
