---
title: "OpticOdds Critical Dependency"
aliases: [opticodds, opticodds-api, sharp-odds-provider]
tags: [value-betting, infrastructure, dependency, odds-data, single-point-of-failure]
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# OpticOdds Critical Dependency

OpticOdds is the sole external provider of sharp book odds data for the value betting scanner, making it a critical single point of failure. When the OpticOdds API key expired on 2026-04-12, all sharp book odds, Australian soft book odds, resolver statistics, and three of four sports (NRL, AFL, MLB) were completely non-functional. Only Bet365 scrapers (Betstamp + game scraper) for NBA continued operating. The subsequent decision to remove the Betstamp adapter entirely (see [[concepts/betstamp-bet365-scraper-migration]]) further concentrates this dependency.

## Key Points

- OpticOdds provides all sharp book odds used for devigging — without it, no true odds calculation is possible for any sport
- Australian soft book odds for NRL, AFL, and MLB are sourced exclusively through OpticOdds — these sports have zero odds data without it
- NBA is the only sport with partial resilience: the Bet365 game scraper provides soft book odds independently of OpticOdds (Betstamp adapter is being removed — see [[concepts/betstamp-bet365-scraper-migration]])
- The scanner runs across three environments: local development, a Windows mini PC (via Tailscale SSH at `100.67.233.95`), and a Linux VPS — all require synchronized key updates
- API keys are stored only in `.env` files, not hardcoded in source — a clean configuration practice that simplifies rotation

## Details

### Dependency Scope

The value betting scanner's architecture depends on OpticOdds for two critical data streams: sharp book odds (used as the "true odds" baseline for identifying value) and soft book odds for Australian-market sports. The devigging algorithm — which converts bookmaker odds into implied probabilities to find positive-EV opportunities — requires sharp book data as its reference point. Without this reference, even sports with independent soft book data (like NBA via Bet365 scrapers) cannot identify value bets because there is no "true odds" to compare against.

The three sports that run on the mini PC and VPS (NRL on port 8801, AFL on port 8802, MLB on port 8803) have no alternative odds sources and go completely dark during an OpticOdds outage. NBA (port 8800) retains soft book odds from Bet365 scrapers but loses its sharp reference data.

### Multi-Environment Key Rotation

When the OpticOdds key (`578d224d...307c`) expired, lcash replaced it with a new key (`97f35e23...18cbd`) across all three environments:

1. **Local** — updated `.env` in the development directory
2. **Mini PC (Windows)** — two separate installations: `value-betting-scanner-new/` and `value-betting-scanner-ms/`, accessed via Tailscale SSH. Windows SSH has operational gotchas: processes running under the SYSTEM account survive `taskkill` without the `/F` (force) flag, requiring `taskkill /F /PID <pid>` targeting the specific PID. Port mappings are NBA=8800, NRL=8801, AFL=8802, MLB=8803.
3. **VPS (Linux)** — standard `.env` update and service restart

Post-rotation health checks confirmed: NBA(8800) healthy, NRL(8801) degraded (no current fixtures — expected, not a bug), AFL(8802) healthy, MLB(8803) healthy, VPS(8802) healthy. The VPS tracker's insert/update activity on startup represents the initial data pass, not trail activity — trails only write when games are imminent.

### Architectural Implications

The single-provider dependency on OpticOdds represents a classic availability risk. The system has no fallback sharp odds provider, and adding one would require either a second API subscription or building a devigging model that can operate without a sharp reference (e.g., using wisdom-of-crowds across multiple soft books). The current architecture accepts this risk in exchange for the simplicity of a single data source.

### Dependency Deepening: Betstamp Removal

The planned removal of the Betstamp adapter (see [[concepts/betstamp-bet365-scraper-migration]]) further concentrates the dependency on OpticOdds. Betstamp provided an independent EV calculation (`betstamp_ev`) derived from its own true line — a cross-check against the OpticOdds-based devigging pipeline. With Betstamp's service discontinued and its adapter being removed, this independent signal is permanently lost. The system's data pipeline now flows through exactly two sources: OpticOdds (sharp + Australian soft books) and the in-house Bet365 game scraper (NBA soft books only). See [[connections/scraper-consolidation-provider-dependency]] for the full analysis.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - Bet365 scrapers are the only odds source independent of OpticOdds
- [[concepts/parlay-ev-calculation]] - EV calculations depend on true odds derived from sharp book data (via OpticOdds)
- [[concepts/betstamp-bet365-scraper-migration]] - Betstamp removal that deepens the single-provider dependency
- [[connections/scraper-consolidation-provider-dependency]] - Analysis of how scraper consolidation interacts with provider dependency

## Sources

- [[daily/lcash/2026-04-12.md]] - OpticOdds key expiry exposed full dependency scope: NRL/AFL/MLB 100% dependent, NBA partially resilient via Bet365 scrapers; key rotated across 3 environments; Windows `taskkill /F /PID` gotcha; port mappings documented (Session 20:15). Betstamp removal analysis confirmed deepening dependency (Session 21:15)
