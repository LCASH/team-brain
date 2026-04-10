# Finding: First Sharp CLV Data

**Date:** 2026-04-09
**Context:** Sharp CLV wired into resolver via `016_sharp_clv.sql`. First batch of resolved picks with sharp closing odds.

---

## Results

From Apr 8 resolved picks (109 picks with sharp trail data out of ~1,000 total):

| Metric | Soft CLV | Sharp CLV |
|--------|----------|-----------|
| Average | +1.79% | +8.9% |

**Sharp CLV is ~5x higher than soft CLV on the same picks.**

---

## What This Confirms

1. **Soft CLV massively understates real edge** — Bet365 barely moves on props, so soft CLV hovers near 0. Sharp books actively adjust, so sharp CLV captures the real signal.
2. **The scanner IS finding genuine edge** — +8.9% sharp CLV means the market moved significantly in our direction after identification.
3. **Sharp CLV is the meaningful validation metric** — soft CLV was giving us a muted, almost useless signal.

## Limitations

- Only 109/1000 picks had sharp trail data (10.9% coverage). Most picks don't have enough sharp trail entries for closing odds calculation.
- Small sample — one day of data. Need weeks to draw real conclusions.
- Implementation uses multiplicative devig on closing sharp odds — could be refined.

## Next Steps

- Increase sharp trail coverage (more frequent sharp trail captures?)
- Wait for 500+ picks with sharp CLV to start bucketing by EV range and confidence
- Compare sharp CLV across prop types to validate devig accuracy per market

---

## Related Pages
- [[wiki/clv]] — CLV concepts, soft vs sharp distinction
- [[findings/2026-04-07-clv-1000-picks]] — Prior analysis using soft CLV only
