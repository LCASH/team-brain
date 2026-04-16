---
title: "DD/TD Resolver Bias and Opacity"
aliases: [double-double-resolver, triple-double-resolver, dd-td-over-bias, opticodds-encoded-stats]
tags: [value-betting, resolver, data-quality, bias, opticodds]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# DD/TD Resolver Bias and Opacity

The value betting scanner's Double Double (DD) and Triple Double (TD) resolution trusts OpticOdds' `player_double_double` stat entirely — no local verification against individual stat lines (points, rebounds, assists, steals, blocks). The `actual_stat` values from OpticOdds are opaque encoded floats (e.g., `1.402040003`), not clean 0/1 binary. Despite the encoding, the `> 0.5` comparison produces correct results. However, DD/TD shows a striking bias: Over has a 100% win rate (106-0) while Under has a 0% win rate (0-10), even after deduplication.

## Key Points

- The resolver uses OpticOdds' `player_double_double` stat directly — it does NOT compute DD/TD from individual stats (points, rebounds, assists, steals, blocks)
- `actual_stat` values are non-binary encoded floats (e.g., `1.402040003`) — opaque encoding, but the `> 0.5` comparison produces correct win/loss results
- DD/TD Over: **100% win rate** (106 wins, 0 losses); DD/TD Under: **0% win rate** (0 wins, 10 losses) — pattern holds after deduplication
- 768 total resolved DD/TD picks collapse to only 291 unique `(player, prop, side, game)` combos — **62% are duplicates** from soft_book_id in the pick hash
- No verification layer exists: if OpticOdds returns a wrong DD/TD value, the resolver has no cross-check mechanism

## Details

### Opaque Encoding

OpticOdds provides player prop resolution data via its `player_double_double` stat field. Conventional expectation is that a Double Double stat would be binary — `1` (achieved) or `0` (not achieved). Instead, OpticOdds returns encoded float values like `1.402040003`. These values appear to encode additional information beyond the binary outcome (possibly indicating which stat categories were involved, e.g., points+rebounds vs. points+assists), but the encoding scheme is undocumented and opaque.

The scanner's resolver simply checks `actual_stat > 0.5` — values above 0.5 count as "achieved" (Over wins), values below as "not achieved" (Under wins). This works correctly for resolution purposes because the encoding consistently produces values >1.0 for achieved Double Doubles and presumably <0.5 for not achieved. But the opacity means the resolver cannot extract which stat categories contributed to the Double Double, limiting diagnostic capability.

### The Over/Under Asymmetry

The 100% Over / 0% Under split across 116 deduplicated picks (106 Over wins, 10 Under losses) is extreme and warrants investigation across several hypotheses:

1. **Sampling bias:** The scanner may be systematically selecting DD Over picks because of how odds are structured — books typically offer more attractive odds on Over (which bettors prefer), creating apparent +EV that the scanner triggers on. Under picks may be less frequently triggered due to less favorable odds structure.

2. **Resolution methodology:** If OpticOdds has any systematic error in DD/TD resolution (e.g., counting steals+blocks combinations differently than some books), it could affect one side more than the other.

3. **Market structure:** DD Over bets have bounded downside (the player either gets a DD or doesn't) but the probability may be genuinely higher than the implied odds suggest for star players who consistently approach double-double stat lines. DD Under is the reverse — it may be correctly priced or even -EV when the scanner identifies it as +EV.

4. **Small sample on Under:** Only 10 deduplicated Under picks is too small for confident statistical conclusions. The 0% rate could be genuine bias or random variance at this scale.

### Pick Deduplication Inflation

The pick ID hash at `server/tracker.py:88-91` includes `soft_book_id`, so the same player+prop+game generates separate pick IDs per soft book. For DD/TD picks available across 3-4 soft books (Sportsbet, Neds, Ladbrokes AU, PointsBet AU) and triggered by multiple theories, a single market event becomes 4-6 rows in the database. This inflates apparent pick counts by approximately 2.6x (768 raw → 291 unique).

For betting execution tracking (where per-book picks are needed to know which book to bet at), the current design is correct. For performance analysis (win rate, ROI by prop type), the inflation distorts metrics. The fix belongs in the analytics layer (`server/analytics.py`), not the tracker — deduplication at query time by `(player, prop, side, game)` before calculating aggregate statistics.

### Potential Verification

An optional verification layer (~15 lines of code) could cross-check OpticOdds' DD/TD resolution against individual stat lines: pull points, rebounds, assists for the same player+game, count categories ≥10, and compare against the `player_double_double` result. This would catch edge cases where the stat provider disagrees with individual stat lines (e.g., a player with 10 points, 10 rebounds, 0 assists counted as a DD via points+rebounds, but the stat provider encoding is ambiguous about steals+blocks contributions).

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - DD/TD resolution depends entirely on OpticOdds with zero cross-check — amplifies the single-provider risk
- [[concepts/pick-dedup-multi-theory-limitation]] - The pick dedup architecture that produces the 2.6x inflation; soft_book_id inclusion is by design
- [[concepts/one-sided-consensus-structural-bias]] - Another Over/Under asymmetry (951:13) from a different root cause (structural method bug vs. market structure)
- [[concepts/value-betting-theory-system]] - DD/TD theories should potentially exclude Under based on this 0% historical rate

## Sources

- [[daily/lcash/2026-04-16.md]] - DD/TD resolver uses OpticOdds `player_double_double` stat (encoded floats like 1.402040003, not binary); DD Over 106-0 (100% WR), DD Under 0-10 (0% WR); 768 picks → 291 unique (62% duplicates from soft_book_id in hash); no verification layer exists; dedup fix belongs in analytics.py (Session 14:45)
