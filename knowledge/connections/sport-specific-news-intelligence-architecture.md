---
title: "Connection: Sport-Specific News Intelligence Architecture"
connects:
  - "concepts/news-agent-injury-pipeline"
  - "concepts/news-driven-pre-sharp-ev-thesis"
  - "concepts/twitter-x-api-scraping-constraints"
  - "concepts/podcast-pick-extraction-pipeline"
sources:
  - "daily/lcash/2026-04-25.md"
created: 2026-04-25
updated: 2026-04-25
---

# Connection: Sport-Specific News Intelligence Architecture

## The Connection

NBA and MLB have fundamentally different news-breaking hierarchies, requiring different source strategies for the news agent pipeline. NBA injury news is dominated by 2-3 national insiders (Shams Charania, Adrian Wojnarowski, Chris Haynes) who break stories across all teams. MLB injury news is broken by **team-specific beat writers** (Anthony DiComo for the Mets, Keegan Matheson for the Blue Jays) and transaction aggregators (MLB Trade Rumors), with national insiders (Jeff Passan, Ken Rosenthal) covering only the biggest stories after the beat writers have already reported.

## Key Insight

The non-obvious insight is that **the same source list architecture cannot serve both sports.** An NBA news agent with 6 Tier-1 national insiders covers 90%+ of line-moving news across all 30 teams. An MLB news agent with the same approach would miss the majority of actionable injury news because it is broken at the team level by local beat writers, not at the national level by insiders.

This has direct operational implications:

| Dimension | NBA | MLB |
|-----------|-----|-----|
| **Source count needed** | 6-10 national insiders | 30+ beat writers (1+ per team) + ~5 national |
| **Breaking speed** | Shams/Woj 4 min ahead of aggregators | Beat writers 10-30 min ahead of national insiders |
| **Discovery method** | Static list (small number of known insiders) | Crawl job needed (MLB.com reporter pages, team beat-writer indices) |
| **Rate limit pressure** | Low (10 accounts × 1 req/cycle) | High (35+ accounts × 1 req/cycle) |

The rate limit dimension is particularly important: Twitter/X's 50 requests per 15-minute window (see [[concepts/twitter-x-api-scraping-constraints]]) comfortably accommodates 10 NBA accounts but strains with 35+ MLB accounts. This may require a second Twitter auth token or staggered polling cycles for MLB.

## Evidence

Specific MLB injury news sourcing analysis from 2026-04-25:

- **Francisco Lindor (calf strain)**: Broken by Anthony DiComo (Mets beat, SNY/MLB.com)
- **Alejandro Kirk (thumb surgery)**: Broken by Keegan Matheson (Blue Jays beat, MLB.com)
- **Giancarlo Stanton (leg tightness)**: No single breaker — in-game injury covered simultaneously via AP wire and broadcast
- **Cade Horton (Tommy John)**: Broken by Sahadev Sharma (Cubs/The Athletic)
- **Justin Steele (60-day IL)**: Broken by MLB Trade Rumors (Franco/McDonald) — roster move, not injury

By contrast, the NBA injury speed analysis (SGA ankle, Wembanyama concussion) showed Shams Charania first on the initial report and FantasyLabs 4 minutes behind — national insiders dominate NBA breaking news with beat writers providing color/confirmation afterward.

## Architectural Implications

1. **The news agent's source config must be sport-parameterized.** NBA: small static list of national insiders. MLB: large dynamic list requiring periodic discovery via web crawling.
2. **Beat writer crawl job needed for MLB.** Scraping MLB.com reporter directory pages and team-specific beat-writer indices to build and maintain the per-team source list. This is a new pipeline component not needed for NBA.
3. **Transaction aggregators are MLB-specific.** MLB Trade Rumors breaks roster moves (IL placements, option exercises, DFA notices) that are line-moving events. NBA has no equivalent aggregator — roster moves are smaller in impact and broken by the same national insiders.
4. **In-game injuries have no "breaker."** For events like Stanton's leg tightness (discovered during a game), the news is simultaneous across all sources. The edge window for in-game injuries is near-zero, and the news agent should focus on pre-game/between-game injury disclosures where the time gap between breaker and market is meaningful.

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The pipeline architecture that must adapt to sport-specific source hierarchies
- [[concepts/news-driven-pre-sharp-ev-thesis]] - The thesis depends on fast news ingestion; MLB's beat-writer-dominated flow creates a larger but more distributed edge window
- [[concepts/twitter-x-api-scraping-constraints]] - Rate limits constrain how many MLB beat writers can be polled per cycle; may require multiple auth tokens
- [[concepts/podcast-pick-extraction-pipeline]] - The podcast pipeline also showed sport-specific differences: MLB podcasts produce breakeven ROI while NBA Action Network produced +58.6%, suggesting information flows differently across sports
