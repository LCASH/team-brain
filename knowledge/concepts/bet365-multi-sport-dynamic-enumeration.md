---
title: "bet365 Multi-Sport Dynamic Enumeration"
aliases: [sport-enumeration, bet365-full-sport-scan, dynamic-crawler, sport-b-numbers, bet365-afl-nrl-props]
tags: [bet365, scraping, reverse-engineering, multi-sport, architecture, value-betting]
sources:
  - "daily/lcash/2026-05-06.md"
created: 2026-05-06
updated: 2026-05-07
---

# bet365 Multi-Sport Dynamic Enumeration

On 2026-05-06, lcash built a fully dynamic multi-sport event enumeration system for bet365 AU, successfully discovering 501 events across 25 of 38 sports with zero hardcoded competition or round IDs. The system uses a 3-phase discovery pattern: sport menu (stable B numbers) -> sport splash (seasonal competition IDs) -> competition listing (weekly round/event IDs). AFL player props were confirmed at ~200 markets per game via the bet builder endpoint, and NRL tryscorer markets at ~35 per game.

## Key Points

- **25/38 sports working**, 501 events, zero crashes — the remaining 13 use CDN binary format (`Api/1/Blob`) or racing-specific APIs
- Only **sport B numbers** (e.g., B18=NBA, B2488=AFL, B4740=NRL, B151=Esports) are stable long-term; competition IDs (C###) change seasonally, round IDs (E###) change weekly
- **3-phase dynamic discovery**: `allsportsmenu` → per-sport splash → competition/round IDs — no hardcoded C### or E### values needed
- **AFL bet builder**: ~200 prop markets per game — Disposals (5–35+, 10 milestones), Marks (2–8+), Goals (1–4+), Tackles, Hitouts, Clearances, First Goalscorer
- **NRL bet builder**: ~35 Tryscorer markets per game; uses simpler `S1` = player name directly (no roster-linking pass needed); `playercontentapi/playerprops` endpoint discovered with additional stat markets
- **Sport separator patterns**: ` v ` (AFL/NRL/Cricket), ` @ ` (NBA/MLB/Hockey), ` vs ` (Tennis)
- **SPA cache reset**: Navigate to `/HO/` between sports to force fresh API calls; `N1` suffix required for AFL/NRL round listings
- `getsplashpods` endpoint surfaces Ruby Union + Ice Hockey events that `splash` misses

## Details

### 3-Phase Discovery Architecture

The system discovers all events dynamically at runtime with no hardcoded values beyond sport B numbers (which are available from the `allsportsmenu` endpoint, making even those discoverable):

**Phase 1 — Sport Menu**: `leftnavcontentapi/allsportsmenu` returns all 60 sports with their B numbers, URL paths, and display names. This endpoint requires no NST token — just cookies. Stable long-term.

**Phase 2 — Sport Splash**: Navigate to `#/AS/B{id}/` which fires either `splashcontentapi/getsplashpods` or a sport-specific splash. The response contains all active competition IDs (e.g., IPL=C21129497 for cricket, which changes seasonally). Event IDs are discoverable from `gethomepageadditionalpods` via regex: `r'#AC#B(\d+)#C(\d+)#D\d+#E(\d+)#'`.

**Phase 3 — Competition Listing**: Navigate to the competition URL to discover round and event IDs. These change weekly (e.g., Round 10 NRL → Round 11). The listing response contains PA records with `PD` fields encoding the internal E values needed for game-page navigation.

### Sport-Specific Findings

**AFL Player Props (B2488)**:
- Bet builder endpoint (`betbuilderpregamecontentapi/wizard`) returns full prop suite
- Hierarchy: `CL|BL|PB` (not the NBA `CL|MA|PA` pattern) — player name in `BL` record, odds in `PB` children
- EV.NA key is `"Goalscorer"` (not `"Anytime Goal Scorer"` as initially assumed — exact key matching is critical)
- 55 disposal milestones, 42 mark milestones, 23 goal milestones, tackles, hitouts, clearances per game
- Correct game page path uses internal E ID from `PA.PD` field, not `PA.FI`
- D-code: AFL = D19/F19

**NRL Player Props (B4740)**:
- EV.NA key is `"Tryscorer"` (not `"Anytime Try Scorer"`)
- Simpler structure: `S1` = player name directly, `S2` = empty (no roster pass needed)
- 35 Anytime Tryscorer bets as `player_tries Over 0.5` per game
- D-code: NRL = D8/F8
- Second endpoint discovered: `playercontentapi/playerprops` (3 responses, ~205KB total) — may contain additional markets beyond tryscorer

**Esports (B151)**:
- All esports under single umbrella B=151
- Competitions: CDL (Call of Duty), LCK (LoL), CS2 (IEM Atlanta, PGL Astana), Dota2 (DreamLeague)
- No player props available — `betbuilderpregamecontentapi/wizard` not wired to B=151
- Match-level markets only: moneyline, map handicap, total maps
- Endpoint: `othersportsmatchbettingcontentapi/coupon` (routing rule o=840)
- Empty responses (200/0b) mean games outside betting window, not probe failure

**Tennis**: Uses ` vs ` separator (not ` v ` like AFL/NRL) — simple pattern fix enabled parsing.

**Cricket**: Requires navigating splash page to discover current competition IDs dynamically (IPL = C21129497, but changes seasonally).

**Ice Hockey/Boxing/Golf**: Use `/Api/1/Blob` (CDN binary JS format), not contentapi — different data delivery mechanism.

### WS Player Prop Streaming Validation

WebSocket streaming was confirmed for player props across multiple sports:

- WS frame format: `L{MG}-{PA}_30_0\x01U|OD={frac};HA={line};|` — `HA` field = O/U line value
- Full player names appear in WS snapshot: `NA=Austin Reaves (LA Lakers) - Over` — no HTTP coupon required for names
- `SU=1` = market suspended; `SU=0` = active (real-time suspension signaling)
- Tab I-values mapped per sport: NBA=I43 (Points), I45 (Threes); NRL=I6; AFL=I6; MLB=I5 (Pitcher), I3 (1st Inning); Soccer=I2/I3/I43
- Pre-game prop counts via HTTP coupon: NRL I6=60 PAs, AFL I6=384 PAs, NBA I43=187 PAs, NBA I45=126 PAs, MLB I5=22 PAs

### Routing Manifest

The 16KB `websiteroutingdatacontentapi/routingdata` manifest lists all 106 endpoints — could be parsed to make endpoint discovery self-healing against name changes. The routing rule (e.g., o=840 for `othersports`) determines which endpoint fires for which sport/competition combination.

## Related Concepts

- [[concepts/bet365-in-browser-cdp-fetch-transport]] - The CDP fetch transport that enables this enumeration; all API calls go through in-browser `Runtime.evaluate`
- [[concepts/spa-navigation-state-api-access]] - SPA cache reset via `/HO/` is required between sports; `N1` suffix for AFL/NRL round listings
- [[concepts/bet365-racing-data-protocol]] - The same `~VS~`/`~VT~` binary protocol format appears in sport enumeration responses
- [[connections/anti-scraping-driven-architecture]] - The enumeration works within the defense stack by using AdsPower as the session host
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS scraper that consumes enumerated event IDs for live streaming
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture that this enumeration system feeds into

## Sources

- [[daily/lcash/2026-05-06.md]] - 25/38 sports working, 501 events; 3-phase discovery (allsportsmenu → splash → listing); AFL ~200 props/game via bet builder with BL/PB hierarchy; NRL ~35 tryscorer via S1 direct structure; EV.NA keys: "Goalscorer" not "Anytime Goal Scorer", "Tryscorer" not "Anytime Try Scorer"; sport separators: v/@ /vs; SPA cache reset via /HO/; D-codes AFL=D19, NRL=D8; Cricket seasonal C### IDs; Ice Hockey/Boxing/Golf use Api/1/Blob; getsplashpods for Rugby Union/Ice Hockey (Sessions 01:36, 02:06, 02:45). Esports B=151: CDL/LCK/CS2/Dota2; no player props; match-level only; empty 200 = outside betting window (Sessions 09:53, 09:58). WS PA streaming confirmed: L{MG}-{PA}_30_0\x01U|OD=;HA=; format; full names in snapshot; SU=0/1 suspension; NRL I6=60 PAs, AFL I6=384 PAs (Session 12:39). NRL `playercontentapi/playerprops` discovered (Session 02:45)
