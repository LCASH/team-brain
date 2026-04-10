# Pattern: Full Pipeline Data Flow

> The complete cycle from odds scraping to pick resolution.

---

## Every 20 Seconds (Main Cycle)

```
1. SCRAPE
   ├── OpticOdds.scrape_cycle()        → ~24k odds from 40+ books
   ├── Bet365Game.scrape_cycle()       → ~2k odds via CDP (NBA only)
   ├── Betstamp WebSocket              → Bet365 odds (streaming)
   └── Direct scrapers                 → AU bookies (Sportsbet, Neds, etc.)

2. MATCH
   └── Market matcher                  → Group by {player}_{prop}_{side}
       (line deliberately ignored — interpolation handles differences)

3. DEVIG (per active theory)
   ├── For each market pair (Over/Under):
   │   ├── For each sharp book with data:
   │   │   ├── Run all 4 devig methods (mult, add, power, shin)
   │   │   └── If sharp_line != target_line: interpolate
   │   └── Weighted average across sharp books → true_odds
   └── Consensus fallback if no sharp books

4. EVALUATE
   ├── EV% = (book_odds / true_odds - 1) × 100
   ├── Confidence = sum of per-book scores (max 5.0)
   ├── Weighted EV = EV% × (confidence / 5.0)
   └── Check theory thresholds: min_ev, min_confidence, min_weighted_ev

5. TRACK (picks that pass)
   ├── Upsert to nba_tracked_picks (scalar columns)
   ├── Append to trail_entries (~200 byte INSERT)
   └── Update in-memory state (dirty flag)

6. OUTPUT
   ├── Write dashboard/data.json (~1.2MB)
   ├── SSE stream to connected dashboards
   └── Upsert to nba_ev_picks (Supabase)
```

## Every 30 Minutes (Resolution)

```
7. RESOLVE
   ├── Fetch player results from OpticOdds
   ├── Match to tracked picks by player + prop
   ├── Grade: hit / miss / push / unresolvable
   ├── Calculate CLV for each pick
   └── Write to nba_resolved_picks

8. ANALYTICS
   ├── Win/loss/push by theory, side, prop, EV bucket
   ├── Cumulative P/L chart
   └── ROI per theory
```

## Every 24 Hours (Maintenance)

```
9. CLEANUP
   └── Prune trail_entries older than 365 days
```

---

## Key Properties

- **Per-market resilience:** One corrupt market doesn't crash the cycle
- **Theory parallelism:** All active theories evaluate every market simultaneously
- **Append-only trails:** No JSONB patches, just cheap INSERTs
- **Read-only dashboard:** Frontend never writes to DB
- **Decoupled state:** FastAPI request loop reads independently from scraper loop
