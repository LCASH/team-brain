---
title: "bet365 WS PM Live Delta Confirmation"
aliases: [pm-delta-live, empty-ack-dormant, horse-race-ws-probe, pm-subscribe-live-streaming, v4-pm-primary-architecture]
tags: [value-betting, bet365, websocket, reverse-engineering, architecture, streaming]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 WS PM Live Delta Confirmation

On 2026-05-07 (Session 23:32), lcash ran a horse race probe that captured **real PM-format U-deltas** with full odds and odds history in every push — the first confirmed instance of PM subscriptions delivering real-time data on the bet365 platform. This reinterprets the `EMPTY` ack observed across all prior tests (NBA, MLB, NRL, Tennis): EMPTY means "buffer dormant, nothing has changed yet," NOT "subscribe rejected or unsupported." Pre-game sports props return EMPTY because prices aren't moving hours before tipoff — not because PM streaming is disabled. The architecture decision shifted from "HTTP primary, WS supplemental" to "PM subscriptions as primary for volatile/live markets, HTTP polling demoted to safety net."

## Key Points

- **Horse race probe captured real PM U-deltas** — `DO=` (decimal odds), `OD=` (fractional), `OH=` (last 3 prices = line movement history baked into every push)
- **EMPTY reinterpreted**: "buffer dormant, nothing has changed" — NOT "subscribe refused." Pre-game stable lines return EMPTY because there are literally no price changes to push
- **Same PA streams via BOTH PM and BS channels simultaneously** when betslip-added — PM is page-level, BS is betslip-specific, both deliver deltas independently
- **Pre-game EMPTY is expected behavior**, not a WS limitation — testing against volatile markets (horse racing with active trading) was the essential methodological correction
- **v4 architecture revised**: PM subscriptions as **primary** odds source for volatile/live markets; HTTP polling demoted to safety net only (was previously the reverse)
- **Complete delta payload decoded**: `\x15PM{FI}-{PA_ID}\x01U|DO={decimal};OD={fractional};OH={price_history};|` — OH field contains last 3 prices, enabling line movement detection without trail storage
- Prior 4-sport injection verdict (Session 20:56) was **technically correct but contextually misleading** — all 4 sports were pre-game with static lines, so EMPTY was the correct response, not evidence of streaming failure

## Details

### The Horse Race Breakthrough

All prior WS probes (Sessions 18:40, 19:20, 19:51, 20:23, 20:56, 21:27, 22:27, 22:57) tested against pre-game sports fixtures hours before tipoff. These markets have stable lines that don't move — sharps haven't started active trading, and the CDN-cached prices are effectively frozen. Every probe returned EMPTY acks, leading to the conclusion that PM subscriptions can't deliver deltas.

The horse race probe on Session 23:32 tested against a **live horse race** (FI=194196581) with active betting and price volatility. The result was immediate: real `\x15`-prefixed U-delta frames containing full odds data. The PM subscription format (`PM{FI}-{PA_ID}`) worked identically to all prior tests — the only variable was market volatility.

This resolves a month-long investigation (April 15 through May 7) into bet365's WS streaming architecture. The protocol has always worked; the test methodology was flawed because pre-game sports markets don't produce price changes.

### Delta Payload Format

The confirmed delta payload structure for live PM updates:

```
\x15PM{fixture_id}-{participant_id}\x01U|DO={decimal_odds};OD={fractional_odds};OH={odds_history};|
```

| Field | Description | Example |
|-------|-------------|---------|
| `DO=` | Decimal odds | `DO=3.40` |
| `OD=` | Fractional odds | `OD=12/5` |
| `OH=` | Last 3 price snapshots (movement history) | `OH=3.50,3.40,3.20` |

The `OH=` (Odds History) field is architecturally significant — it embeds the last 3 prices into every delta push, enabling line movement detection directly from WS frames without needing separate trail storage or historical queries. A consumer receiving `OH=3.50,3.40,3.20` can immediately tell the odds are trending down.

### EMPTY Ack Reinterpretation

The `\x14` (EMPTY) response to PM subscriptions was previously interpreted across multiple sessions as:
- Session 20:23: "subscribe registered" (correct but incomplete)
- Session 20:56: "EMPTY ack does NOT mean data will follow" (technically correct for pre-game)
- Session 22:27: "no buffered state for pre-game" (correct mechanism, wrong conclusion)

The corrected interpretation: EMPTY means **the server's price buffer for this PA has no pending changes**. For pre-game markets where lines are static, the buffer is permanently empty until trading begins. For live/volatile markets, the buffer fills as prices move, and deltas push immediately.

This distinction matters because it reframes the entire architecture: WS is not broken or limited for pre-game — it is **correctly idle** because there is nothing to stream. The system works as designed.

### PM vs BS Channel Behavior

When a PA is added to the betslip, both PM (page-level) and BS (betslip-specific) channels stream deltas simultaneously for that PA. The PM channel carries the standard delta format above. The BS channel (documented in [[concepts/bet365-ws-subscription-injection-viability]]) carries betslip-specific updates with the `BS{PA_ID}-{selection_ID}` topic format.

For the horse race probe, both channels delivered identical price data at the same moments — confirming they are redundant data paths rather than exclusive alternatives. The PM channel is the correct choice for scraper architecture because it doesn't require betslip interaction to activate.

### Architecture Revision: PM Primary

The Session 20:56 4-sport injection test led to the architecture decision: "HTTP primary (10-15s), WS supplemental." The horse race finding partially reverses this for volatile markets:

| Market State | Primary Source | Secondary Source |
|-------------|---------------|-----------------|
| **Pre-game (stable)** | HTTP polling (30s NBA, 60s MLB) | WS listener (captures whatever bet365 features) |
| **Near-tipoff (activating)** | PM subscriptions (sub-second) | HTTP polling (safety net) |
| **Live/in-play** | PM subscriptions (sub-second) | HTTP polling (safety net) |

The transition from "pre-game HTTP primary" to "live PM primary" should happen approximately 30-60 minutes before tipoff — the window when sharp action begins and prices start moving. This is one of the untested hypotheses documented in Session 22:57 that the horse race probe partially validates.

### Methodological Lesson

The most important lesson from the horse race probe is about test methodology: **testing WS streaming against stable pre-game markets is inherently misleading**. Zero deltas is the correct response for a market with zero price changes. The investigation consumed weeks because every test fixture was pre-game, creating a false negative pattern that was interpreted as a protocol limitation.

The correct test methodology for real-time streaming probes is to test against a market with known, active price movement — horse racing during a live race, in-play sports, or any market approaching its settlement time when sharp action intensifies.

### Remaining Validation

The horse race probe confirmed PM deltas work for volatile markets, but two validations remain:

1. **Near-tipoff sports test**: Run the probe against an NBA/MLB game during the 30-60 minute pre-tipoff window to confirm PM deltas activate for sports props specifically (not just horse racing)
2. **PA_ID namespace alignment**: The horse race probe used horse racing PA_IDs which may be in a different namespace than the sports wizard PA_IDs. If the disjoint PA_ID space issue (see [[concepts/bet365-ws-subscription-injection-viability]]) also applies to horse racing vs the PM subscribe format, per-game `page.goto` navigation (which captures live-trading PA_IDs) would be needed to obtain streamable PA_IDs

## Related Concepts

- [[concepts/bet365-ws-subscription-injection-viability]] - The protocol reversal that identified EMPTY ack semantics, 3 PA_ID namespaces, and the FI routing key — all recontextualized by the horse race finding
- [[concepts/bet365-ws-pre-game-prop-streaming-limitation]] - Pre-game EMPTY is confirmed as expected behavior (stable lines = no deltas), not a protocol limitation; the architecture decision shifts for near-tipoff/live markets
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native scraper architecture that should adopt PM subscriptions as primary for live/near-tipoff markets
- [[concepts/bet365-racing-data-protocol]] - The racing protocol whose PM format was confirmed to deliver live deltas; OH= (odds history) field is a new finding beyond the previously documented DO=/OD= fields
- [[concepts/bet365-ws-topic-authorization]] - April 15 render-state authorization finding is recontextualized: PM topics ARE authorized for page-rendered PAs, and they DO deliver deltas when the market is volatile
- [[connections/anti-scraping-driven-architecture]] - The defense stack's WS constraints are less restrictive than previously concluded: PM streaming works within the authenticated session for any market with active price movement

## Sources

- [[daily/lcash/2026-05-07.md]] - Betslip probe on MLB pre-game (TEX@NYY) returned EMPTY acks for all 7 PAs — confirmed pre-game dormancy. Horse race probe (FI=194196581) captured real PM U-deltas: DO=, OD=, OH= fields with line movement history; same PA streams via PM and BS simultaneously; EMPTY reinterpreted as "buffer dormant" not "refused." v4 architecture revised: PM primary for volatile markets, HTTP safety net. Testing against volatile markets (live horse racing) was the essential methodological correction that resolved the month-long WS investigation (Session 23:32)
