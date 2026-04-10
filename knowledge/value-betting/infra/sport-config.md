# Sport Config

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Per-sport registry defining markets, sharp books, resolver windows, and interpolation betas.

---

## Source

`ev_scanner/sport_config.py` (~16KB)

---

## Supported Sports

| Sport | Key | Port | Data Sources | Status |
|-------|-----|------|-------------|--------|
| NBA | `nba` | 8800 | OpticOdds + Bet365 CDP + Betstamp | Production |
| MLB | `mlb` | 8803 | OpticOdds + Bet365 non-headless + Betstamp | Production |
| NRL | `nrl` | 8804 | OpticOdds only | Production |
| AFL | `afl` | 8805 | OpticOdds only | Production |

---

## What Each Config Defines

- **OpticOdds parameters:** Sport key, league ID, market type mappings
- **Market maps:** How OpticOdds market names map to our internal prop types
- **Sharp book weights:** Per-sport overrides (NBA props have different sharp landscape than AFL)
- **Interpolation betas:** Per-prop type logit/Poisson beta values
- **Resolver windows:** How long to wait before marking picks stale
- **Scraper config:** Which direct scrapers to run for this sport

---

## Adding a New Sport

See [[patterns/adding-a-sport]] for the full pattern.

---

## Related Pages
- [[opticodds]] — Data source configured per sport
- [[interpolation]] — Beta values defined per sport/prop
- [[devig-engine]] — Sharp weights differ per sport
