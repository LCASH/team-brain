---
title: "OpticOdds Critical Dependency"
aliases: [opticodds, opticodds-api, sharp-odds-provider]
tags: [value-betting, infrastructure, dependency, odds-data, single-point-of-failure]
sources:
  - "daily/lcash/2026-04-12.md"
  - "daily/lcash/2026-04-20.md"
  - "daily/lcash/2026-04-23.md"
  - "daily/lcash/2026-04-24.md"
created: 2026-04-12
updated: 2026-04-24
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

### Esports Coverage Gap (2026-04-20)

An OpticOdds esports audit on 2026-04-20 revealed significant coverage gaps: while 9 esports leagues are listed as available (CS2, Call of Duty, Dota 2, Kings of Glory, League of Legends, MLBB, Rainbow Six Siege, Rocket League, Valorant), only **League of Legends** has actual odds from any book (Pinnacle, Kalshi, Polymarket). The remaining 8 esports leagues have fixtures but zero odds entries from any bookmaker. This means the OpticOdds SSE streaming expansion (see [[concepts/opticodds-sse-streaming-scaling]]) will stream fixture events for these leagues but the scanner cannot evaluate them without odds data. Esports markets are thin across the industry — OpticOdds' gap reflects the broader market, not a provider-specific limitation.

### Data Completeness Without Quality Flags (2026-04-23)

A third dependency risk dimension was discovered on 2026-04-23, beyond availability (key expiry) and bias (no genuine sharps for AFL): **data completeness**. OpticOdds returned truncated player stats for Wembanyama (5 pts / 4 reb / 1 ast / 12 minutes — clearly partial Q1-Q2 data) with no flag indicating incompleteness. The API returned HTTP 200 with valid-looking JSON containing real numbers. The resolver graded the pick based on these incomplete stats, producing a silently wrong resolution.

This is a particularly insidious risk because, unlike an availability outage (immediately visible) or a bias issue (detectable through aggregate outcome analysis), partial data looks valid at the individual record level. There is no completeness flag, no partial-response indicator, and no mechanism to distinguish "player scored 5 points" (legitimate) from "only first-half stats were returned" (truncated). The system must build its own completeness heuristics (e.g., minutes-played sanity checks) because OpticOdds does not provide them. See [[concepts/opticodds-partial-stats-silent-misresolution]] for the full analysis.

### API Key Sport-Specific Scoping (2026-04-24)

A fourth dependency risk dimension was discovered on 2026-04-24: **API key scope**. The current OpticOdds API key only grants access to NBA basketball — not multi-sport. REST fixtures return empty for all non-basketball sports, SSE connections fail with 400 "not enabled for your API key" for all 22 non-basketball streams, and even other basketball leagues (NBL, EuroLeague, CBA) are inaccessible. This means the scanner is effectively **NBA-only** despite code and infrastructure supporting multi-sport operation.

The practical impact: MLB has 275 markets from the Bet365 game scraper but zero sharp book data — no EV calculation is possible. NRL and AFL mini PC servers are not running. The Pinnacle prediction-market pipeline, Crypto Edge strategy, and SSE streaming expansion are all NBA-only until the API key is upgraded.

The API key scope limitation interacts with the other dependency dimensions:
- **Availability** (key expiry): affects all sports equally
- **Bias** (no genuine sharps): affects AFL specifically
- **Completeness** (truncated stats): affects all sports
- **Scope** (key permissions): affects all non-NBA sports — the broadest impact of the four

See [[concepts/opticodds-api-key-sport-scoping]] for the full audit and `SSE_SPORTS` env var mitigation.

## Related Concepts

- [[concepts/opticodds-partial-stats-silent-misresolution]] - Truncated stat lines from OpticOdds causing silent mis-resolution; a third dependency risk beyond availability and bias
- [[concepts/bet365-racing-adapter-architecture]] - Bet365 scrapers are the only odds source independent of OpticOdds
- [[concepts/parlay-ev-calculation]] - EV calculations depend on true odds derived from sharp book data (via OpticOdds)
- [[concepts/betstamp-bet365-scraper-migration]] - Betstamp removal that deepens the single-provider dependency
- [[connections/scraper-consolidation-provider-dependency]] - Analysis of how scraper consolidation interacts with provider dependency
- [[concepts/opticodds-sse-streaming-scaling]] - SSE streaming expansion depends on OpticOdds having actual odds data per league, not just fixture listings
- [[concepts/opticodds-api-key-sport-scoping]] - API key scope limiting access to NBA-only; fourth dependency risk dimension beyond availability, bias, and completeness

## Sources

- [[daily/lcash/2026-04-12.md]] - OpticOdds key expiry exposed full dependency scope: NRL/AFL/MLB 100% dependent, NBA partially resilient via Bet365 scrapers; key rotated across 3 environments; Windows `taskkill /F /PID` gotcha; port mappings documented (Session 20:15). Betstamp removal analysis confirmed deepening dependency (Session 21:15)
- [[daily/lcash/2026-04-20.md]] - Esports coverage audit: 9 leagues listed but only League of Legends has odds from any book (Pinnacle, Kalshi, Polymarket); CS2, Valorant, Dota 2, CoD, and 4 others have fixtures but zero odds (Sessions 14:57, 16:29)
- [[daily/lcash/2026-04-23.md]] - Third dependency dimension: data completeness without quality flags. Wembanyama stats truncated (5 pts / 4 reb / 12 min) with no incompleteness indicator; resolver produced wrong grade from valid-looking partial data (Session 18:23)
- [[daily/lcash/2026-04-24.md]] - Fourth dependency dimension: API key sport-specific scoping. Key only covers NBA basketball; MLB/soccer/tennis/hockey/esports all return empty/400; NRL/AFL servers dead; MLB 275 markets from Bet365 only with zero sharps (Sessions 14:40, 15:47, 16:35)
