---
title: "Connection: First-Wins Merge from Multi-Source Iteration"
connects:
  - "concepts/resolver-adjacent-day-merge-bug"
  - "concepts/push-loop-diff-cache-phantom-freshness"
  - "concepts/bet365-same-book-alt-line-collision"
  - "concepts/market-key-cross-day-game-start-staleness"
sources:
  - "daily/lcash/2026-05-20.md"
created: 2026-05-20
updated: 2026-05-20
---

# Connection: First-Wins Merge from Multi-Source Iteration

## The Connection

Multiple independently discovered bugs in the value betting scanner share a root anti-pattern: iterating over multiple data sources (dates, alt-lines, market types) and merging results into a dictionary where the first occurrence wins. The iteration order silently determines which value is stored, and because the "wrong" value is structurally valid, no error is raised. The bugs produce plausible wrong output that passes all validation checks.

## Key Insight

The non-obvious insight is that **first-wins merge is safe when sources are independent and non-overlapping, but dangerous when sources can produce competing values for the same key.** The resolver's `dates_to_fetch = [day-1, target, day+1]` iterates three dates that can all contain stats for the same player (if they played consecutive days). The diff cache iterates alt-lines that map to the same `market_key` (because `market_key` drops `line`). In both cases, the dict key is shared across sources, and the first source to populate it determines the stored value — with no signal that a competing value exists.

The pattern is particularly dangerous because:
1. **Iteration order is an implementation detail** — reordering a list shouldn't change semantics, but in first-wins merge, it does
2. **The "wrong" value is structurally valid** — Salvador Perez's day-before stats (H=2) are real stats, just from the wrong game
3. **No duplicate key warning** — Python dicts silently ignore subsequent assignments to existing keys via `if key not in dict:` guards

## Evidence

Four documented instances of this anti-pattern in the scanner:

| Bug | Sources Iterated | Shared Key | Wrong Value Stored | Impact |
|-----|-----------------|------------|-------------------|--------|
| **Resolver dates_to_fetch** | [day-1, target, day+1] | Player name | Yesterday's stats | 16.4% wrong MLB results |
| **Diff cache alt-line flap** | Multiple alt-lines per player | `(fixture, market_key)` | Random alt-line odds | Phantom change_event firing |
| **bet365 alt-line collision** | 3 O/U lines per player | `market_key` (no line) | Random alt-line odds | +130% phantom EV |
| **game_start staleness** | Same player across days | `market_key` (no date) | First-ever observation date | 93% of markets filtered as "live" |

The resolver bug is the most severe because it corrupted final grading data (win/loss results) rather than intermediate state. The others affected real-time processing but not historical records.

## Prevention

Three approaches prevent first-wins merge bugs:

1. **Last-wins with explicit priority**: If multiple sources can produce values for the same key, explicitly define which source takes priority. The resolver fix uses `[target, day-1, day+1]` ordering so the target date's stats win — but this is fragile (a code change that reorders the list reintroduces the bug).

2. **Per-key source tracking**: Store which source provided each value. When a conflict is detected, apply domain-specific resolution logic rather than implicit ordering. The resolver's real fix — per-pick ET-date derivation — eliminates the multi-source ambiguity entirely.

3. **Unique keys that prevent collision**: The `market_key` bugs (diff cache, alt-line, game_start) share a root cause: the key doesn't include enough dimensions to be unique. Adding `line` and `game_date` to the key prevents the collision at the cost of more complex aggregation logic.

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - The most severe instance: 16.4% wrong MLB results from day-before stats winning over target-date stats
- [[concepts/push-loop-diff-cache-phantom-freshness]] - Diff cache Bug 1: alt-line flapping from missing `line` in key
- [[concepts/bet365-same-book-alt-line-collision]] - Same-book multi-line with last-write-wins producing phantom EV
- [[concepts/market-key-cross-day-game-start-staleness]] - game_start stuck on first observation from never-overwrite guard
- [[connections/market-key-dateless-design-recurring-bugs]] - The dateless/lineless key design that enables key collisions in three of the four instances
- [[connections/silent-type-coercion-data-corruption]] - The broader pattern of plausible wrong output with zero error signal

## Sources

- [[daily/lcash/2026-05-20.md]] - Resolver `dates_to_fetch` ordering bug: day-before stats win for consecutive-day players; 133/809 (16.4%) wrong actual_stat; first-wins merge identified as anti-pattern to grep for across codebase; at least one more instance at resolver.py:1391-1394 (Sessions 12:38, 13:34)
