# Hot Topics

> Active investigations, open questions, and current work streams.
> Move resolved items to the bottom with a date.

---

## Core Mission (as of 2026-04-08)

**Properly identify positive value bets with confidence that we'll be profitable long-term.**

This means the brain must carry sport-specific and market-specific context — each sport is different, and even within a sport each market (Points vs Assists vs Combos) behaves differently. The devig process and theory configs need to account for this. A theory that works for NBA Points may fail for NBA Assists or NRL Tries. The brain exists to prevent every Claude session from rediscovering this from scratch.

**Current focus:** NBA player props (most data, most calibration). Will expand to other sports but only with sport-specific calibration, not copy-pasted NBA configs.

**Key principle:** Don't filter out segments (like consensus picks, or low-confidence picks) before you have the data. Track everything, let the data tell you what's profitable. There could be a situation where consensus picks are actually very profitable but you'd never know if you excluded them upfront.

---

## Active

### Sharp Count is the Strongest Predictor of Edge Quality
**Status:** Validated finding from 1,000 pick analysis
**Context:** 5+ sharps at 2-6% EV = +2.25% CLV, 70.8% win rate. This is the strongest signal in the data.
**Warning:** High EV (6%+) with 5+ sharps shows NEGATIVE CLV (-1.03%) — these are likely **false positives** from stale or erroneous odds. The scanner needs to handle this.
**Action:** Sharp count should be a primary filter in the performance tracking system and surfaced prominently in the dashboard.
**Update 2026-04-09:** First sharp CLV data confirms this — avg sharp CLV +8.9% vs soft CLV +1.79% on Apr 8 resolved picks. Sharp CLV is the more meaningful validation metric.

### AU Books Outperform Bet365 by 3-5x on CLV
**Status:** Validated finding
**Context:** PointsBet, Ladbrokes, Neds all show significantly better CLV performance than Bet365. This suggests Bet365 is either sharper (harder to beat) or our Bet365 odds capture has timing issues.
**Implication:** The soft book target matters as much as the devig quality. May want to prioritize AU books over Bet365 for actual bet placement.

### Alt Line Theory — Phase 1 LIVE
**Status:** Phase 1 deployed, generating volume
**Context:** AltLine-V1 theory running with confidence decay model and safety ceiling. **219 picks tracked on Apr 8** (up from initial 3-10/day). BetIQ shows 3x more EV from alt lines than we find — gap likely from interpolation beta steepness.
**Early results (30d):** 565 picks, 47.1% WR, avg CLV +1.62%, avg EV 13.53%, ROI +39.9% (small sample, high variance)
**Phase 2:** CLV tracking by gap bucket (needs 2-3 weeks of data). Then beta optimization.
**Ref:** `docs/methodology/theories/alt_line_distribution_model.md` and `alt_line_implementation_status.md`

### Resolver Player Name Matching Gap
**Status:** ACTIVE — significant data loss
**Context:** Apr 8 resolution: 2,004/3,829 picks (52%) skipped due to `skip_no_player`. Players like Kuminga, Conley, Jayson Tatum not matching. Some are from unplayed games (expected), but many played and still didn't match.
**Impact:** Halves our resolution rate. Skipped picks get no result, no CLV, no ROI data.
**Investigation needed:** Compare player name formats between tracker (from scrapers) and OpticOdds player-results API. Likely a normalization issue (extra spaces, suffixes, etc.).

### Null Player Name Constraint Bug
**Status:** ACTIVE — non-blocking but indicates data quality issue
**Context:** Tracker batch updates failing with `null value in column "player_name" violates not-null constraint`. Seen in VPS logs Apr 8-9. Scraper is returning picks with null player data.
**Impact:** Some picks silently fail to insert. Not blocking the tracker loop (batch continues minus failed rows).
**Investigation needed:** Which scraper source produces null player_name? Likely Bet365 game scraper returning incomplete market data for certain prop types.

### Bet365 2.0 Missing Picks
**Status:** INVESTIGATION PENDING
**Context:** From `docs/scanner-issues-2026-04-08.md`. When comparing Betstamp Bet365 vs our direct scraper (Bet365 2.0), the direct scraper appears to miss picks that Betstamp captures.
**Investigation needed:** Side-by-side comparison on same slate — market count by prop type, identify which players/props are missing.

### Performance Tracking System — Design Phase
**Status:** Designing (see [[wiki/performance-tracking]])
**Context:** Segmented analysis system to answer "which picks are profitable?" across EV range × Confidence × Prop type × Sport. CLV as leading indicator (converges 100x faster than ROI). Track everything, filter later.
**Update 2026-04-09:** Sharp CLV now live (`sharp_clv_pct` column) — first real validation metric. Soft CLV understates edge significantly (often 0.00 because Bet365 barely moves on props).

### Multi-Sport Expansion
**Status:** Production (all 4 sports)
**Context:** NBA (8800), MLB (8803), NRL (8801), AFL (8802) all running on mini PC. VPS relay at 170.64.213.223:8802 aggregates all sports. NRL and AFL use OpticOdds only (no Bet365 game scraper). Push worker aggregates all sports.
**MLB docs:** Full context banking done in scanner repo (`docs/methodology/sports/mlb/`). Not yet calibrated.

---

## Resolved

### Sharp CLV Wired Into Resolver (resolved 2026-04-09)
Sharp closing CLV now computed during resolution. Uses `trail_entries` (trail_type='sharp') to get closing sharp book odds, devigs with multiplicative method, writes `sharp_clv_pct` to `nba_tracked_picks`. First data Apr 8: 109/1000 picks had sharp trail data, avg sharp CLV +8.9% vs soft CLV +1.79%. Confirms soft CLV severely understates real edge. Migration: `016_sharp_clv.sql`. Dead infrastructure note: `nba_odds_history` table and `clv.py` fetch functions are unused — trail_entries is the working data source.

### Sharp Book Weight Fallback Bug (resolved 2026-04-09)
Dashboard `computeTrueProb()` iterated ALL 8 `SHARP_IDS` regardless of theory config. Non-listed books got fallback weight 1.0, so Calibrated theory (meant to use 4 books) was actually using 7. **Root cause was dashboard-only** — server-side `tracker.py` already correctly extracted `theory_ids` from weights. Fix: extract `theoryIds` from weight keys, iterate only those. Also added `w <= 0` guards on both dashboard and server, changed theory editor defaults from 1.0 to 0 for absent books. Deployed to VPS.

### OpticOdds API Key Mismatch (resolved 2026-04-09)
VPS at `/opt/value-betting/.env` had expired API key (`2dcdf80c...`) while local `.env` had current key (`578d224d...`). Result: 401 Unauthorized on ALL fixture/player-results API calls, blocking resolution for all 4 sports for ~12+ hours. Odds scraping was unaffected (different endpoint/key?). Fix: updated VPS key, `systemctl restart value-betting`. **Lesson:** After rotating API keys, always update VPS `.env` too.

### Dashboard Improvements (resolved 2026-04-09)
- Added "True" odds column (purple) showing primary theory's devigged true odds
- Removed American odds display from all 3 table contexts (EV, Markets, Compare)
- Sharp detail panel now shows both Over and Under odds per book
- Empty-state message when no sharp data available for a pick

### Trail I/O Optimization (resolved 2026-03)
Odds changes moved from JSONB patches (20-100KB per update) to cheap INSERTs (~200 bytes) in `trail_entries` table. 90-95% reduction in Supabase disk I/O.

### Live Game Filter (resolved 2026-03-14)
OpticOdds `/fixtures/active` was returning live games alongside upcoming. Added `is_live: false` filter to exclude in-play markets.
