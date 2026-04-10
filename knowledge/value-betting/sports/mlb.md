# MLB

## Status: stub — research phase, not yet calibrated
## Last verified: 2026-04-09

> MLB player props — full context banking done, scanner running on port 8803, but no calibration data yet.

---

## Scanner Parameters
→ See `docs/methodology/sports/mlb/context.md` for sharp book rankings, biases, situational factors.
→ See `docs/methodology/sports/mlb/markets.md` for market-by-market breakdown.
→ See `docs/methodology/sports/mlb/data.md` for data pipeline and sources.

---

## Key Differences from NBA

- **Non-headless Chrome required** — Cloudflare blocks headless on bet365 for MLB
- **Pitcher props behave differently from batter props** — pitcher Ks are high-count (closer to NBA Points), batter hits/HR are low-count (closer to NBA Blocks)
- **Environmental factors matter more** — wind, temperature, altitude, park factors affect totals
- **Fewer data points** — MLB season overlap with NBA is limited, calibration sample will be smaller
- **Sharp book landscape differs** — Pinnacle and Circa may be sharper for MLB than NBA (game lines especially)

---

## Open Questions

- Which sharp books are actually sharp for MLB player props? (NBA findings can't be assumed)
- What interpolation betas are appropriate for pitcher Ks vs batter hits?
- Is the favourite-longshot bias stronger or weaker for MLB props?
- Are AU books as soft for MLB as they are for NBA?

---

## Related Pages
- [[sports/nba]] — Compare findings as MLB calibration data arrives
- [[wiki/devig-engine]] — Sport-specific devig considerations
