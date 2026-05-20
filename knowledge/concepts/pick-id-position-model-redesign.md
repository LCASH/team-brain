---
title: "Pick ID Position Model Redesign Analysis"
aliases: [position-model, pick-id-redesign, position-based-picks, line-move-duplicate-rows, pick-thread-id]
tags: [value-betting, architecture, design, pick-id, methodology]
sources:
  - "daily/lcash/2026-05-15.md"
created: 2026-05-15
updated: 2026-05-15
---

# Pick ID Position Model Redesign Analysis

On 2026-05-15, lcash performed a deep architecture analysis of whether to replace the current line-inclusive pick_id hash with a position-based model using OpticOdds external IDs (`fixture_id`, `market_id`, `player_id`). The current scheme hashes `(player, prop, side, line, game_date, soft_book_id)` — when a soft book's line moves (e.g., Over 19.5 → Over 20.5), a NEW pick row is created because the hash changes. This produces duplicate rows representing the same betting position with potentially conflicting results. Three options were crystallized: (a) full position model replacing line in pick_id, (b) additive approach keeping current pick_id and adding optic_* reference columns, (c) do nothing. Option B was assessed as ~80% benefit at ~30% cost.

## Key Points

- Current pick_id includes `line` → when a soft book moves its line, a new pick row is created for the same logical position (same player, prop, side, game, book)
- **264 NBA + 208 MLB conflicting result groups** exist from line-move duplicates — retroactive artifacts of the current scheme, not forward failures
- Position model would use `(fixture_id, market_id, player_id, soft_book_id)` from OpticOdds instead of `(player, prop, side, line, game_date, soft_book_id)` — one row per position regardless of line drift
- Milestone props (15+, 20+, 25+ Points) are **structurally different positions** from Over/Under and correctly treated as separate rows even under position model — they use `prop_type = "Points CO"` vs `"Points"`
- Line matching uses **full logit/Poisson interpolation**, not "closest line" — each sharp is independently interpolated to the soft's line, then weight-averaged per theory
- Mixed-theory compression is a real cost: if AltLine-V1 fires first at 2.5 and Pinnacle Only fires later at 3.5, only the first gets recorded as `triggered_by`
- `optic_player_id` flagged as "often empty for game-level markets" — needs empirical validation before relying on it in hash

## Details

### The Line-Move Duplicate Problem

The current `_generate_pick_id()` hashes `(player, prop, side, line, game_date, soft_book_id)`. When the engine evaluates a market where the soft book's line has changed since the last evaluation — for example, Sportsbet moves "Points Over 19.5" to "Points Over 20.5" — the hash changes, producing a new pick row. Both rows represent the same betting position (this player's points Over on this game via this book), but they have different `pick_id` values.

This creates two problems:

1. **Conflicting results**: The resolver grades each row independently. If the player scores 20 points, the Over 19.5 row wins but the Over 20.5 row loses — the same position produces both a win and a loss in the database.
2. **Analytics distortion**: Aggregate metrics (ROI, win rate, CLV) count duplicate rows as separate bets. A single position that generated 3 rows from line drift inflates sample sizes by 3x.

Investigation confirmed 264 NBA and 208 MLB groups with conflicting results from this mechanism.

### Three Options

**Option A — Full position model**: Replace `(player, prop, side, line, game_date, soft_book_id)` with `(fixture_id, market_id, player_id, soft_book_id)` from OpticOdds external IDs. One row per position, `opening_line` immutable, line drift captured in trail data. This is the cleanest architecture but touches every downstream consumer: resolver, audit, dashboard, backfill, analytics. Estimated as the highest-benefit, highest-cost option.

**Option B — Additive columns**: Keep the current pick_id, add `optic_fixture_id`, `optic_market_id`, `optic_player_id`, and `pick_thread_id` (a grouping key for line-move siblings) as reference columns. Downstream consumers optionally group by `pick_thread_id` for position-level analysis. Gets ~80% of the benefit (position-level analytics) at ~30% of the cost (no existing consumer changes, just new optional columns). Migration 036 would cover all new columns together.

**Option C — Do nothing**: Accept the duplicate rows as a known limitation, handle dedup at the analytics query layer (already partially implemented in `tdDedupeAndWindow()`). Zero cost, but the problem accumulates and distorts automated health checks.

### Position Model Tradeoffs

The full position model (Option A) has two non-obvious costs:

**Loss of discrete +EV crossing granularity**: Under the current scheme, each engine trigger at a new line creates its own row with its own `triggered_ev` and `triggered_at`. This granularity is useful for understanding when and how edge appears. Under the position model, subsequent triggers at new lines would be trail entries on the same row — recoverable from trail data but requiring different queries.

**Mixed-theory compression**: Under position model, `triggered_by` locks to the first theory that fires. If AltLine-V1 triggers at line 2.5 and Pinnacle Only triggers later at line 3.5, only AltLine-V1 is recorded. The `theory_evs` JSONB column (see [[concepts/pick-dedup-multi-theory-limitation]]) partially addresses this, but a `triggering_theories` array would be a more complete solution.

### Milestone Props Are Correctly Separate

A key clarification: milestone props (15+ Points, 20+ Points, 25+ Points) and standard Over/Under are **structurally different market types**, even though "20+ Points" and "Points Over 19.5" can represent the same underlying outcome. Milestones use `prop_type = "Points CO"` (see [[concepts/co-ou-parser-conflation-phantom-picks]]) and have no sharp pair for devigging. The position model would NOT collapse milestones into O/U rows — they remain separate positions with different `market_id` values in OpticOdds.

The engine does NOT interpolate from standard O/U lines down to milestone thresholds because small calibration errors at the median compound into large errors at the distribution tails — a mathematical limitation independent of the pick_id scheme.

### Validation Required Before Proceeding

Two empirical validations were identified before committing to Option A:

1. **OpticOdds ID stability**: Confirm that OpticOdds returns the same `(fixture_id, market_id, player_id)` tuple for a pick when the line moves between observations. If IDs change with line moves, the position model gains nothing.
2. **`optic_player_id` reliability**: Query last 7 days of OpticOdds responses to measure the null rate on player-prop rows. If `optic_player_id` is frequently empty (flagged as common for game-level markets), it cannot serve as a reliable hash component.

### `_build_sharp_snapshot()` Captures All Books

A related finding: the tracker's `_build_sharp_snapshot()` function captures odds from ALL books with data, not just the theory-whitelisted ones. This is architecturally correct for backtesting flexibility — replay scripts can re-evaluate any theory configuration against the full snapshot. The sharp_snapshot schema is `{book_id: {odds, under_odds, interp_prob, weight}}`, and true_prob is reconstructed as `Σ(weight × interp_prob) / Σ(weight)`.

## Related Concepts

- [[concepts/pick-dedup-multi-theory-limitation]] - The `triggered_by` limitation that the position model would inherit; `theory_evs` JSONB column partially addresses mixed-theory compression
- [[connections/market-key-dateless-design-recurring-bugs]] - The lineless market_key design causes collisions at the DataStore level; the line-inclusive pick_id causes duplicates at the persistence level — two opposite architectural choices, both with tradeoffs
- [[concepts/pick-id-float-int-hashing-bug]] - A prior pick_id hash bug (float vs int line) that broke trail collection; the position model would eliminate this class of bug entirely by removing line from the hash
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 9 (position consistency) found 4 duplicate position groups from VPS running old v1 pick_id hash; validates the need for the redesign

## Sources

- [[daily/lcash/2026-05-15.md]] - Deep architecture analysis of position-based pick_id; three options crystallized (full position model, additive columns, do nothing); 264 NBA + 208 MLB conflicting result groups; milestone props correctly separate; line matching uses full logit/Poisson interpolation not closest-line; `optic_player_id` often empty for game-level markets; `_build_sharp_snapshot()` captures all books for replay flexibility (Session 09:23)
