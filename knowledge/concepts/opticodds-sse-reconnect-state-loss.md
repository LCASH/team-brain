---
title: "OpticOdds SSE Reconnect State Loss"
aliases: [sse-reconnect-delta, sse-state-loss, sse-timeout-reconnect, rest-reseed-pattern]
tags: [value-betting, opticodds, sse, reliability, architecture, data-quality]
sources:
  - "daily/lcash/2026-05-05.md"
created: 2026-05-05
updated: 2026-05-05
---

# OpticOdds SSE Reconnect State Loss

OpticOdds SSE sessions timeout server-side every ~25-30 minutes. On reconnect, the SSE stream only sends deltas (markets that have changed), not a full snapshot. This means stable lines from sharp books like Pinnacle, DraftKings, and FanDuel — which rarely change between games — silently vanish from the local store after a reconnect because no delta is sent for them. Combined with the store's 60-second market pruning (markets not refreshed within 60s are considered stale and removed), sharp book data disappears entirely within minutes of a reconnect.

## Key Points

- OpticOdds SSE sessions timeout server-side every **~25-30 minutes**; reconnect delivers deltas only, not full state
- Stable lines (Pinnacle, DraftKings, FanDuel) that haven't changed since last snapshot are **never re-sent** after reconnect — they silently disappear from the store
- Store prunes markets not refreshed within 60 seconds, so any book that stops streaming (due to reconnect delta behavior) goes dark within a minute
- **Fix: REST polling as periodic reseed** — `_opticodds_rest_seed()` runs 30s after startup then every 5 minutes, doing a full `fixtures/odds` REST pull to repopulate the store regardless of SSE state
- The user caught this by challenging the claim that Pinnacle/sharp books "weren't ready yet" — they post lines well in advance; the real issue was SSE losing their data on reconnect
- SSE-only architecture is fragile for this use case; the hybrid SSE + periodic REST reseed is the correct pattern (same approach V2 used implicitly via REST pollers)

## Details

### The Discovery

On 2026-05-05 (Session 22:14), lcash was debugging why the V3 scanner showed zero sharp book coverage despite Pinnacle, DraftKings, and FanDuel being known to post NBA lines hours before game time. The initial explanation — "sharp books aren't ready yet" — was challenged by the user, who correctly pointed out that these books post well in advance.

Deeper investigation revealed the SSE stream was silently losing all state every 25-30 minutes. The OpticOdds SSE connection would work initially (first connection receives a full snapshot), but when the server-side timeout fired and the client reconnected, the new stream only contained markets that had changed since the last message. For sharp books pricing NBA player props, these lines are set hours before game time and rarely move — meaning the reconnect stream contained zero updates for Pinnacle, DraftKings, and FanDuel. Within 60 seconds of the reconnect, the store's staleness pruning removed all their data.

### The State Loss Mechanism

The failure chain:

1. **SSE connection established** — full snapshot delivered, all books populated in store
2. **25-30 minutes pass** — SSE connection open, deltas flowing for markets that change
3. **Server-side timeout** — OpticOdds drops the connection
4. **Client auto-reconnects** — new SSE stream opened
5. **Delta-only delivery** — only markets that changed since last message are sent; stable sharp lines are NOT re-sent
6. **60-second prune** — store removes markets not refreshed within 60s; sharp books (with no recent deltas) are pruned
7. **Sharp data gone** — tracker has zero sharp reference for devigging; all EV computation fails silently

This cycle repeats every ~25-30 minutes, creating a pattern where sharp books appear briefly after each reconnect snapshot (if the reconnect happens to deliver one) then vanish until the next reconnect.

### The REST Reseed Fix

The fix adds `_opticodds_rest_seed()` to the V3 startup: a periodic REST polling function that does a full `fixtures/odds` API call every 5 minutes (first call at 30 seconds after startup). This REST response always contains the complete current state — all books, all lines, regardless of whether they've changed recently. The REST seed repopulates the store with sharp book data that SSE reconnects would otherwise lose.

The 30-second initial delay ensures the REST seed runs quickly after startup, so sharp book coverage is populated before the first SSE timeout cycle. The 5-minute interval is chosen to be more frequent than the ~25-30 minute SSE timeout, guaranteeing that sharp data is never more than 5 minutes stale even if every SSE reconnect delivers only deltas.

### SSE vs REST: Complementary, Not Competing

This discovery clarifies the relationship between SSE and REST for OpticOdds data:

| Dimension | SSE | REST |
|-----------|-----|------|
| Latency | Sub-second for changed markets | 60-second polling interval |
| Completeness | Full on initial connect; delta-only on reconnect | Always full |
| Connection overhead | 1 persistent connection per sport | 1 HTTP request per poll cycle |
| Failure mode | State loss on reconnect | Polling gap if request fails |

The hybrid approach uses SSE for low-latency updates on actively changing markets and REST for guaranteed periodic completeness. This is architecturally equivalent to V2's approach where REST pollers ran alongside the SSE display stream, though V2 didn't have this explicit reasoning.

## Related Concepts

- [[concepts/opticodds-sse-streaming-scaling]] - The SSE streaming architecture that this reconnect behavior undermines; the 491-league scaling plan must account for periodic REST reseeds
- [[concepts/opticodds-tcp-drop-max-age-tuning]] - TCP drops cause a different failure mode (intermittent loss) vs SSE reconnect (systematic loss of stable lines); MAX_ODDS_AGE tuning addresses TCP drops, REST reseed addresses reconnect state loss
- [[concepts/opticodds-critical-dependency]] - A fifth dependency risk dimension: not just availability, bias, completeness, and scope, but SSE protocol behavior that silently degrades data quality
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture that incorporates REST reseed as a core component, not a workaround
- [[concepts/dashboard-pick-flashing-stale-odds]] - Pick flashing from stale data is the visible symptom; SSE state loss is one root cause pathway

## Sources

- [[daily/lcash/2026-05-05.md]] - User challenged claim that sharp books weren't ready; investigation revealed SSE sessions timeout every ~25-30 min server-side, reconnect only sends deltas; stable Pinnacle/DraftKings/FanDuel lines vanish after reconnect; store prunes after 60s; fix: `_opticodds_rest_seed()` runs at 30s then every 5 min; Bet365 captured_at went from 36,327s stale → 6s fresh after timestamp fix; SETUP_CONCURRENCY bumped 3→5 for MLB (Session 22:14)
