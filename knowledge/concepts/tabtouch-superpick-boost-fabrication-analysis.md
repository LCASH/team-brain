---
title: "TabTouch SuperPick Boost Fabrication Analysis"
aliases: [superpick-fabrication, tabtouch-boost-exploit, propose-vs-commit-validation, detect-and-bet-pipeline, superpick-token-pool]
tags: [superwin, tabtouch, reverse-engineering, security-research, racing, boost-mechanics]
sources:
  - "daily/lcash/2026-05-22.md"
created: 2026-05-22
updated: 2026-05-22
---

# TabTouch SuperPick Boost Fabrication Analysis

On 2026-05-22, lcash built a full reverse-engineering validation lab to test whether TabTouch SuperPick boosts could be fabricated via payload injection. The propose (quote) endpoint echoes boost template data broadly — injecting `specialSeq: 6248` on a runner with no natural SuperPick offer returned HTTP 200 with `priceIncrease.win: 0.5` applied. However, the commit (bet placement) endpoint returned **HTTP 412 ("Selected SuperPick is unavailable or invalid")** — the server is hardened at the money step. The key signal is `maxStake`: legitimate accounts return `maxStake: 250.0`, ineligible returns `maxStake: 0`. Fabrication is dead; the viable production strategy is **detect-and-bet**: poll `hasSpecialOffer`, fetch eligible runners, EV calc against Betfair, commit on accounts with `BetsAvailable > 0`.

## Key Points

- **Propose endpoint is non-authoritative**: echoes boost template data for any runner without checking token eligibility — `specialSeq` injection returns HTTP 200 with Win Boost applied
- **Commit endpoint is hardened**: returns HTTP 412 when `maxStake=0` or token pool empty (`Tokens: []`); `maxStake` in propose response is the eligibility flag
- **Boost tiers scale with live horse price**: price 20+ → +5.0 boost (+500% on $0.50), price 8–20 → +1.0, price 2–8 → +0.5, price 1–2 → +0.1 — server ignores submitted price
- **Two promo classes**: price-altering/propose-time (SuperPick, Win Boost via `specialSeq`) and settlement bonus/post-bet (Profit Plus, Money Back — invisible at propose)
- **Architecture split**: Racing FOB → TABtouch native .NET (`/api/betting/fob/propose/racing-single`); Sport → Kambi (`coupon/validate.json` / `coupon/place.json`) — completely separate stacks
- **Token economics**: ~26 boosted bets per account per weekend from bonus tokens (TokenId 13475-13481 with 5 bets each); tokens fire R1-5 only (R6+ returns null); cross-venue within token code type
- **Revenue potential**: ~$4,800/week from racing (10 bowlers × 320 bets × $100 × 15% EV), ~$7-9k/week total with Kambi sport side

## Details

### The Validation Lab

A complete local validation lab was built at `~/Documents/tabtouch-lab/` with four components: a poller (30s cycle against TABtouch APIs), a 4-tab HTML dashboard, a `capture.js` CDP traffic interceptor (with `--intercept` mode for MITM editing), and a `manifest.js` for API endpoint documentation. The lab used AdsPower browser profiles for authenticated session management, with CDP `Runtime.evaluate` for in-page fetch calls that inherit cookies/auth context.

Two test accounts were used: `k14s0yyq` (no SuperPick tokens, used for fabrication baseline) and `k135xnt1` (Raelene Cooper — active tokens, used for legitimate flow capture).

### Fabrication Test Results

Three fabrication vectors were tested:

| Vector | Propose Result | Commit Result | Assessment |
|--------|---------------|---------------|------------|
| Token stripped (no specialSeq) | Normal odds | — | Baseline |
| Cross-race token injection (specialSeq from another race) | Win Boost applied, `maxStake: 0` | HTTP 412 | **Blocked** |
| Fully fabricated boost (specialSeq on ineligible account) | Win Boost applied, `maxStake: 0` | HTTP 412 | **Blocked** |
| Legitimate SuperPick (k135 with tokens) | Win Boost applied, `maxStake: 250.0` | HTTP 200, `totalReward: 0.20` | **Works** |

The propose endpoint is fundamentally a quoting service — it calculates what the boosted price WOULD be without checking whether the user is eligible to receive it. This makes it useful for reconnaissance (mapping boost economics per runner and price tier) but useless for exploitation. The commit endpoint validates the token pool server-side before processing the bet.

### Boost Tier Discovery

The propose endpoint revealed a precise boost tier structure that scales with the horse's live price:

| Live Horse Price | Boost Amount | % on $0.50 Stake | EV Significance |
|-----------------|-------------|-------------------|-----------------|
| $20+ | +5.0 | +1000% | **Highest EV — target outsiders** |
| $8–$20 | +1.0 | +200% | Strong edge |
| $2–$8 | +0.5 | +100% | Moderate edge |
| $1–$2 | +0.1 | +20% | Marginal |

The server determines the boost amount from the live price, ignoring any price submitted by the client. This means the boost is always economically consistent — you cannot submit a higher price to inflate the boost.

### Two Promo Classes

TABtouch operates two structurally different promotion types:

**Price-altering (propose-time):** SuperPick and Win Boost modify the proposed price via `specialSeq` in the request body and `specialOffers[0].elements[0].priceIncrease.win` in the response. These are detectable at propose time and are the exploitable edge.

**Settlement bonus (post-bet):** Profit Plus and Money Back are invisible at propose time (`specialSeq: null`, `specialOffers: []` in propose response). They apply as refunds or bonus credits after race settlement. Profit Plus for example is a "Friday Thoroughbred SRM 50% Profit Plus" — a post-settlement rebate, not a price alteration.

### Architecture: Racing vs Sport

TABtouch's betting infrastructure has two completely separate stacks:

| Surface | Stack | Auth | Boost Mechanism |
|---------|-------|------|-----------------|
| Racing FOB | TABtouch native .NET | Session cookies via CDP | `specialSeq` in propose body |
| Sport | Kambi white-label | Kambi JWT + CSRF | `rewardInfo.validRewards` + `groupRewardId` |

Kambi sport boosts (PowerPlay) use `groupRewardId` created server-side at validate time — the client doesn't assert the boost ID. This makes Kambi sport boosts likely NOT fabricable (unlike racing where `specialSeq` is client-asserted but server-validated at commit). The Kambi investigation was deferred (~$13 spent on captures) since TABtouch racing SuperPicks are the actionable edge.

### Money Back EV Analysis

A formal EV model compared Money Back vs Win Boost across price points. The decision rule: `Money Back > Win Boost ⟺ P_2/P_w > Δ` where `P_2` is the probability of placing 2nd and `P_w` is the probability of winning. Money Back dominates at ≤$4 runners (where the refund probability is high), Win Boost dominates at ≥$10 (where the price uplift has more value). This was documented in `MONEY_BACK_EV_ANALYSIS.md`.

### Per-Runner vs Price-Tier Schema Mismatch

A critical finding for the SuperWin scanner: the existing boost table in Supabase is **price-keyed** (one boost amount per price tier, 70 entries), but live TABtouch data is **per-runner-keyed** — individual runners at the same price get different boost amounts. A $34 outlier received +17 while other $34 horses got +3. The per-runner variance is where approximately 95% of excess EV hides. The probe-and-upsert approach (measure median boost per price tier) accepts losing this outlier EV in exchange for zero scraper modifications.

### Production Strategy: Detect-and-Bet

The recommended production pipeline:
1. Poll `/api/raceinfo/nextraces` checking `hasSpecialOffer` (~5s interval)
2. Fetch eligible runners via `superpicksversion2` for accounts with `BetsAvailable > 0`
3. EV calc: `(boosted_price) / betfair_lay - 1`
4. CDP commit on AdsPower browser sessions (inherits auth)
5. Scale via multi-account (1 daily SuperPick token + 5 bonus tokens per account per weekend)

Target outsiders (price 20+) for maximum boost EV (+5.0 = strongest absolute edge).

## Related Concepts

- [[concepts/tabtouch-kambi-white-label-sports]] - Kambi sport boosts use `groupRewardId` (server-assigned) vs racing `specialSeq` (client-asserted, server-validated at commit); completely separate stacks
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal where detect-and-bet SuperPick picks would flow; same insert-only + BSP CLV pattern
- [[concepts/superwin-racing-profitability-dimensions]] - SuperPicks edge already documented at +38.6% ROI; this analysis reveals the per-runner variance and token economics that size the production opportunity
- [[concepts/betr-blueboost-racing-edge]] - BlueBoost uses `boost_field` criteria (per-runner from API); SuperPick uses lookup-table pattern but live data shows per-runner variance that the table misses
- [[concepts/bet365-in-browser-cdp-fetch-transport]] - Same CDP `Runtime.evaluate` pattern used for authenticated API calls in both bet365 and TABtouch labs

## Sources

- [[daily/lcash/2026-05-22.md]] - Full validation lab built at ~/Documents/tabtouch-lab/; Kambi brand `rwwawa` confirmed for AU; propose injection returns Win Boost applied but commit returns 412; `maxStake` is the eligibility signal (250.0 legitimate vs 0 fabricated); boost tiers: 20+→+5.0, 8-20→+1.0, 2-8→+0.5, 1-2→+0.1; two promo classes (price-altering vs settlement bonus); token economics ~26 bets/account/weekend; Money Back EV model; per-runner vs price-tier schema mismatch; revenue ~$4.8k/week racing + $2-4k sport; detect-and-bet production strategy; Kambi sport boosts likely NOT fabricable (Sessions 10:29, 10:50, 11:05, 11:08, 11:31, 12:21, 13:27, 14:30)
