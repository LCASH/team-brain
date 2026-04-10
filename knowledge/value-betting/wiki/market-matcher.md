# Market Matcher

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Groups odds from different bookmakers into matchable market pairs.

---

## How It Works

**Source:** `ev_scanner/market_matcher.py` (~3KB)

Markets are grouped by a composite key: `{player}_{prop}_{side}` — deliberately **ignoring the line**. This allows sharp books at line 26.5 to be paired with soft books at 25.5 (with [[interpolation]] bridging the gap).

---

## Matching Key

```
Key = f"{normalized_player_name}_{prop_type}_{over_or_under}"
Example: "lebron_james_points_over"
```

Within each group:
- All books offering this player/prop/side are collected
- Over + Under pairs are found for devigging
- Best sharp book data is selected per the theory's weights

---

## Known Limitation: Alt Lines

The current matcher deduplicates to one line per book per market. This means:
- If Bet365 offers LeBron Points at 24.5, 25.5, 26.5 (alt lines)
- Only one (typically the main line) is kept
- BetIQ evaluates each alt line independently and finds edge we miss

This is documented as an open gap in [[hot]].

---

## Related Pages
- [[devig-engine]] — Consumes matched market pairs
- [[interpolation]] — Handles line differences within matches
