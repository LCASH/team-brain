---
title: "Pick ID Float/Int Hashing Bug"
aliases: [pick-id-hash-bug, line-type-coercion, float-int-hash-mismatch, trail-collection-break]
tags: [value-betting, bug, data-quality, trail-data, tracker]
sources:
  - "daily/lcash/2026-04-17.md"
created: 2026-04-17
updated: 2026-04-17
---

# Pick ID Float/Int Hashing Bug

The value betting scanner's `_generate_pick_id()` function uses `f"{line}"` to include the line value in the deterministic pick UUID. Python's `f"{0}"` produces `"0"` (int) while `f"{0.0}"` produces `"0.0"` (float). Phase A stores picks with `float(line)` in the hash, but Phase B reads the line from the market dict as an int — producing a different hash. This mismatch means Phase B trail collection never finds the pick, silently breaking trail capture for every moneyline pick (line=0) and any pick with a whole-number line.

## Key Points

- `_generate_pick_id()` uses `f"{line}"` which produces `"0"` for int but `"0.0"` for float — different strings, different UUIDs
- Phase A (pick creation) stores picks using `float(line)` in the hash; Phase B (trail collection) reads line from market dict as int → hash mismatch → 0 trails
- Silently broke trail collection for ALL moneyline picks (line=0) and any pick with whole-number lines (e.g., line=5 vs 5.0)
- Only 5 of 50 prediction market picks had trails despite Phase B running — the 5 had non-integer lines that survived the type coercion
- Fix: always `float(line)` in the hash function, ensuring consistent type coercion regardless of input source
- The bug was invisible because trail collection failures are silent — no errors, no warnings, just missing trail rows

## Details

### The Mechanism

The pick ID is a deterministic UUID derived from `(player, prop, side, line, game_date, soft_book)`. The `line` component is formatted as a string via Python's f-string interpolation: `f"{line}"`. This produces different output depending on the Python type of the `line` variable:

- `f"{0.0}"` → `"0.0"` (float representation)
- `f"{0}"` → `"0"` (int representation)
- `f"{5.0}"` → `"5.0"` (float)
- `f"{5}"` → `"5"` (int)

Phase A (pick creation in the tracker's evaluation loop) receives the line value from OpticOdds data, which passes through `float(line)` coercion before hashing. Phase B (trail collection on subsequent tracker cycles) reads the line value from the market dictionary, where it may be stored as an integer (e.g., moneyline markets where line=0, or player props with whole-number lines like "Points Over 25").

The same market produces two different pick IDs depending on which phase computes the hash. Phase B looks up the pick ID it just generated, finds no match in the database (because Phase A stored it under a different ID), and silently skips trail writing. No error is raised because a missing pick ID is a valid state — it simply means "this market doesn't have a tracked pick yet."

### Discovery

The bug was discovered on 2026-04-17 when lcash investigated why only 5 of 50 prediction market picks had trail data despite Phase B running correctly. The Pinnacle prediction-market pipeline had been deployed with trail capture SOFT_IDS fixed (see [[concepts/trail-capture-soft-ids-gap]]), so the pipeline should have been writing trails. The 5 picks that did have trails all had fractional line values (e.g., 2.5, 7.5) — values that remain floats through both phases. The 45 picks without trails all had whole-number or zero lines where the int/float divergence occurs.

### Scope of Impact

The bug affected every moneyline pick (line=0 is universal for moneylines) and any player prop or game-line pick where the line is a whole number. This is a significant fraction of all picks:

- **Moneyline markets**: 100% affected (line is always 0)
- **Spread markets**: Partially affected (Run Line -1.5 → not affected; Puck Line -1 → affected)
- **Player props**: Partially affected (Points Over 25 → affected; Rebounds Over 7.5 → not affected)
- **Game totals**: Partially affected (Total Runs Over 8 → affected; Total Over 8.5 → not affected)

For the Pinnacle prediction-market pipeline specifically, game-line markets (moneyline, spread) were the primary expansion targets, making this bug particularly destructive to the newest and most strategically important data collection effort.

### Prevention Pattern

The fix — always `float(line)` in the hash function — ensures type consistency regardless of input source. A more robust pattern would be to canonicalize all hash inputs through explicit type conversion functions rather than relying on f-string interpolation of potentially heterogeneous types. Any hash-based deduplication system where the same logical value can arrive as different Python types is vulnerable to this class of bug.

This is a specific instance of the broader "silent type coercion" failure pattern: Python's dynamic typing means `0 == 0.0` evaluates to `True`, but `f"{0}" == f"{0.0}"` evaluates to `False`. Code that mixes equality checks with string formatting can behave differently depending on which path is taken.

## Related Concepts

- [[concepts/trail-capture-soft-ids-gap]] - The SOFT_IDS gap was fixed first, but this bug independently prevented trails from being written even after that fix
- [[concepts/pick-dedup-multi-theory-limitation]] - The pick ID architecture whose hash function contains this bug; soft_book_id in the hash is by design, but type inconsistency in line formatting is a bug
- [[concepts/dd-td-resolver-bias]] - Another case where OpticOdds data encoding assumptions produced silently wrong results
- [[concepts/silent-worker-authentication-failure]] - Same failure signature: zero output, zero errors, silent data loss
- [[connections/silent-type-coercion-data-corruption]] - The broader pattern of type assumption bugs producing plausible but wrong output

## Sources

- [[daily/lcash/2026-04-17.md]] - Only 5/50 prediction market picks had trails; `_generate_pick_id()` uses `f"{line}"` producing "0" for int vs "0.0" for float; Phase A stores with float(line), Phase B reads as int; silently broke ALL moneyline trail collection; fix: always float(line) in hash (Session 16:09)
