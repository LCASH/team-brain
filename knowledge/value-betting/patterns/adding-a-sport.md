# Pattern: Adding a New Sport

> How to add a new sport to the VB Scanner pipeline.

---

## Steps

### 1. Sport Config
Add a new entry in `ev_scanner/sport_config.py`:
- Sport key (e.g., "nhl")
- OpticOdds league ID and market type mappings
- Sharp book weights (may differ from NBA — research which books are sharp for this sport)
- Interpolation betas per prop type
- Resolver windows (how long before a pick is "stale")

### 2. Market Maps
Map OpticOdds market names to internal prop types. Each sport has different player stat categories.

### 3. Server Port
Assign a new port (convention: 8800 + sport index). Add to the push worker's relay list.

### 4. Direct Scrapers (optional)
If AU bookies have this sport, add scraper functions in `direct_scrapers.py`.

### 5. Bet365 Scraper (optional)
If Bet365 has player props for this sport, add a game scraper (consider Betstamp as primary source instead).

### 6. Database
No schema changes needed — all tables use the `sport` column. Just start writing with the new sport key.

### 7. Theory
Create initial theories in `nba_optimization_runs` with `sport = "new_sport"`. Start conservative (high min_ev, high min_confidence) and tune from there.

### 8. Deploy
Add the new server process to the mini PC. Update deploy script.

---

## Existing Examples
- NRL and AFL were added as OpticOdds-only sports (no Bet365 scraper). Simplest path.
- MLB required a non-headless Chrome scraper due to Cloudflare. Most complex.

---

## Gotchas
- Sharp book landscape differs by sport. Don't assume NBA weights work for other sports.
- Some sports have very different prop types (e.g., cricket has balls faced, overs bowled).
- OpticOdds coverage varies by sport and league.
