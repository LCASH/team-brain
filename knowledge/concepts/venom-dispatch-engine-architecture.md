---
title: "Venom Dispatch Engine Architecture"
aliases: [venom-dispatch, venom-engine, pick-to-bookie-flow, venom-throughput, in-memory-counter-architecture]
tags: [superwin, takeover, architecture, automation, betting, venom]
sources:
  - "daily/lcash/2026-06-01.md"
created: 2026-06-01
updated: 2026-06-01
---

# Venom Dispatch Engine Architecture

On 2026-06-01, lcash documented the detailed end-to-end architecture of the Venom automated betting dispatch engine — the execution layer that receives edge picks from SuperWin and fires bets through prepared bookie sessions. The architecture uses in-memory counters for hit tracking (sub-microsecond lookups), a 3-layer cache consistency model (Realtime push ~100ms, pulsing watchdog every 30s, full reload on boot/disconnect), and batched Supabase INSERTs for bet logging. Theoretical throughput for 1000 accounts firing on one pick: ~400ms median, ~1s for 99th percentile.

## Key Points

- **End-to-end flow**: SuperWin pick → Venom cache lookup → eligibility check → bookie HTTP fire → bet log write — only ONE DB write in the hot path (bet_log INSERT after bookie confirms)
- **In-memory counter architecture**: Dict keyed by `(account_id, slug)`, per-key asyncio lock, seeded from `bet_log` on startup, 60s watchdog reconciliation — sub-microsecond lookups, zero race risk
- **3-layer cache consistency**: Realtime push ~100ms (Supabase subscription) → pulsing watchdog every 30s (reconciliation) → full reload on boot/disconnect
- **Settings are read-only from RAM**: `betting_accounts.settings` loaded into memory, never written to in the hot path — all mutation is operator-side via TAKEOVER UI
- **1-phone-per-account topology**: Sharing phones serializes bets and becomes the bottleneck; each account routes through unique phone/SIM/IP
- **Bookie HTTP latency (250-500ms) is the irreducible floor** — everything else is optimized away; Python GIL not a factor (asyncio dispatch is I/O-bound)
- **Batched INSERTs**: ~30-80ms for 1000 bet_log rows; avoids saturating Supabase connection pool
- **Real ceiling is detection tolerance, not throughput**: Personas, mug bets, and rotation matter more than raw dispatch speed

## Details

### The Hot Path

The Venom dispatch engine's hot path from pick arrival to bet placement:

1. **Pick arrives** from SuperWin via internal channel (SSE, webhook, or shared state)
2. **Cache lookup**: Check in-memory settings dict for all accounts with `venom_enabled=true` and edge slug enabled
3. **Eligibility filter**: Per-account checks — daily hit count < `max_hits_per_day`, cooldown timer expired, account not suspended
4. **Bookie HTTP fire**: Dispatch bet through the account's prepared session (cookie jar, proxy binding, session tokens)
5. **Bet log INSERT**: Single batched Supabase write with bet confirmation details

Only step 5 touches the database. Steps 1-4 operate entirely from in-memory state, making the dispatch latency dominated by step 4 (bookie HTTP roundtrip at 250-500ms).

### V2 Settings Schema

The v2 settings schema shipped on 2026-06-01 (commit `f120d0e`) consolidates all Venom eligibility into a single JSONB column on `betting_accounts`:

- **`venom_enabled`**: Master boolean switch — one toggle to pull an account from the entire pipeline
- **`defaults`** block: DRY configuration inherited by all edges (stake, cooldown, timing)
- **`edges`** map: Dynamic dict keyed by SuperWin slug; each entry can override any default field
- **Explicit opt-in**: Edges not listed in the `edges` map are NOT enabled (safe default for new SuperWin edges)

This replaced the v1 schema (which lasted only 1 day with zero real data) and eliminated the Phase 2 WarRoom preparer — settings IS the source of truth Venom reads directly, collapsing ~2 weeks of planned work into Phase 4.

### Throughput Analysis

For 1000 accounts firing on a single pick:

| Component | Latency | Constraint |
|-----------|---------|------------|
| In-memory eligibility check | <10ms total | CPU-bound, trivial |
| Bookie HTTP roundtrip | 250-500ms per account | I/O-bound, parallelized |
| Bet log batch INSERT | 30-80ms for 1000 rows | DB connection pool |
| **Total (1000 accounts)** | **~400ms median, ~1s p99** | Network I/O dominates |

Per-IP rate limits don't apply because each account routes through a unique phone/SIM/IP. The real ceiling isn't throughput — it's bookie detection tolerance (betting patterns, frequency, timing). DO droplet CPU only becomes a bottleneck at ~10,000+ concurrent dispatches.

### Phases 3-6 Handoff

User confirmed remaining phases (session refresher, Venom dispatcher, live deployment, bookie expansion) are Jay's domain. Handoff doc written at `~/.claude/plans/automated-betting/00-jay-handoff.md`. The v2 schema consolidation made Phase 2 (WarRoom preparer) mostly obsolete — dramatically simplifying Jay's starting point.

## Related Concepts

- [[concepts/automated-betting-pipeline-architecture]] - The parent pipeline architecture (SuperWin → WarRoom → Venom); this article details the Venom dispatch layer specifically
- [[concepts/superwin-edge-pick-backtesting]] - The edge detection output that feeds into Venom's dispatch pipeline
- [[concepts/mug-bet-qualifying-loss-edges]] - Mug bets for account sustainability; Venom's hit-counting and cooldown timers serve both edge bets and mug bets
- [[concepts/superwin-execution-gap-price-band-discipline]] - The execution gap analysis motivating automation; Venom eliminates manual price-band non-compliance

## Sources

- [[daily/lcash/2026-06-01.md]] - Phase 1 settings library + UI + DB schema shipped (commit 36a904a); v2 schema consolidated all gating into single JSONB column (commit f120d0e); in-memory counter architecture locked; 3-layer cache consistency; Venom throughput analysis: 400ms median for 1000 accounts; 1-phone-per-account topology; batched INSERTs; Phases 3-6 handed to Jay (Sessions 08:53, 11:50, 12:55, 14:00)
