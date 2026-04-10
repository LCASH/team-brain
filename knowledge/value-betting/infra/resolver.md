# Resolver

## Status: current
## Last verified: 2026-04-09 (updated with sharp CLV implementation)

> Auto-grades tracked picks and computes both soft and sharp CLV.

---

## What It Does

**Source:** `server/resolver.py` (~600 lines)

The resolver runs hourly (5-min initial delay), processing sports sequentially: **nba → mlb → nrl → afl**. For each sport:

1. Queries Supabase for unresolved picks by date (`get_unresolved_dates()`)
2. Fetches player stat results from OpticOdds player-results API (`_fetch_player_stats()`)
3. Fetches closing sharp odds from `trail_entries` table (`_fetch_closing_sharp_trails()`)
4. Matches results to tracked picks by player name + prop type
5. Grades each pick: **win**, **loss**, **push**, or **skipped** (no match)
6. Calculates **soft CLV** (Bet365 closing odds) and **sharp CLV** (devigged sharp book closing odds)
7. PATCHes results to `nba_tracked_picks`

---

## Two Types of CLV

### Soft CLV (`clv_pct`)
```python
clv_pct = (pick_odds / closing_odds - 1) * 100
```
Uses Bet365's own closing odds. **Problem:** Bet365 barely moves on props, so soft CLV is often 0.00%. This understates real edge.

### Sharp CLV (`sharp_clv_pct`) — added 2026-04-09
```python
sharp_clv_pct = (pick_odds * closing_true_prob - 1) * 100
```
Uses devigged sharp book closing true probability. **Why it matters:** Sharp books actually move on information. If our pick odds beat the sharp closing price, we had real edge.

**Implementation:**
1. `_fetch_closing_sharp_trails()` — batch queries `trail_entries` for the latest `trail_type='sharp'` entry per pick_id (chunks of 200)
2. `_compute_closing_true_prob()` — extracts sharp book odds from the `books` JSONB snapshot, devigs each book with multiplicative method, returns simple average true probability across all sharp books
3. Uses `calculate_clv_from_probs()` from `ev_scanner/clv.py`

**First data (Apr 8):** 109/1000 resolved picks had sharp trail data (~11% coverage). Avg sharp CLV: +8.9% vs soft CLV +1.79%. Confirms soft CLV severely understates edge.

**Coverage gap:** Only ~11% of picks have sharp closing data because trail_entries only records changes — if sharp odds don't change between tracking and game start, no closing snapshot exists.

---

## Dead Infrastructure Warning

`ev_scanner/clv.py` contains `fetch_sharp_closing_odds_batch()` and `fetch_closing_odds_batch()` that query `nba_odds_history` table. **This table is not written to by any active code.** The working data source for closing odds is `trail_entries` with `trail_type='sharp'`.

---

## Resolution States

| Result | Meaning |
|--------|---------|
| `win` | Player exceeded the line on an Over bet, or fell short on an Under bet |
| `loss` | Opposite of win |
| `push` | Player landed exactly on the line |
| `null` | Unresolved — game not finished, or player not matched |

---

## Player Name Matching — Known Gap

The resolver matches players by name between our tracked picks (from scrapers) and OpticOdds player-results API. **This is the biggest source of data loss.**

**Apr 8 stats:** 2,004/3,829 picks (52%) skipped due to `skip_no_player`. Includes:
- Players from unplayed games (expected — 3 games that evening)
- Players who DID play but name didn't match (normalization issue)

**Investigation needed:** Compare name formats between tracker sources and OpticOdds results.

---

## Operational Notes

### Multi-Sport Processing
Sports run sequentially: nba → mlb → nrl → afl. The `last_result` field in health endpoint **only shows the last sport processed**. An AFL error in `last_result` does NOT mean NBA failed — it just ran last and errored.

### Manual Trigger
```
GET http://170.64.213.223:8802/api/v1/resolve?date=2026-04-08
```
Useful when auto-resolver missed picks or after fixing an error. Can take 30-90 seconds for large date sets.

### API Key Dependency
The resolver calls OpticOdds fixtures API to get player stats. This requires a valid `OPTICODDS_API_KEY` in the VPS `.env` at `/opt/value-betting/.env`. If the key expires or is rotated locally, the VPS key must also be updated — otherwise you get 401 errors blocking all resolution across all sports.

### NRL Fallback
NRL resolution has a fallback to NRL.com for try data when OpticOdds is missing it.

---

## Analytics

**Source:** `server/analytics.py`

Once picks are resolved, the results endpoint provides:
- Win/loss/push breakdown by theory, side, prop type, EV bucket, timing, book
- Cumulative P/L by date
- ROI per theory
- Risk metrics (max drawdown, streaks)

Endpoint: `GET /api/v1/results?sport=nba`

---

## Related Pages
- [[tracker]] — What creates tracked picks
- [[opticodds]] — Source of player results
- [[dashboard]] — Where results are displayed
- [[database]] — Schema for tracked_picks, trail_entries
- [[calibration]] — How resolution data improves the model
