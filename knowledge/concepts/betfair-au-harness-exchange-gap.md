---
title: "Betfair AU Harness Exchange Coverage Gap"
aliases: [betfair-harness-gap, betfair-zero-harness, betfair-sportsbook-vs-exchange, au-harness-no-exchange]
tags: [superwin, racing, betfair, architecture, constraint, harness]
sources:
  - "daily/lcash/2026-05-20.md"
created: 2026-05-20
updated: 2026-05-20
---

# Betfair AU Harness Exchange Coverage Gap

On 2026-05-20, lcash confirmed that Betfair Exchange has **zero AU harness markets** in their API catalogue. Australian thoroughbred and greyhound racing have Exchange markets with lay prices, but harness racing does not. What appears as harness coverage on betfair.com.au is their separate **Sportsbook** (fixed-odds) product or results/form pages — not Exchange markets with tradeable lay prices. This is significant because AU harness is the SuperWin scanner's #1 edge (+39% ROI on 919 picks), and the scanner requires Betfair Exchange lay prices for EV calculation.

## Key Points

- **Zero AU harness Exchange markets** in Betfair API — confirmed via direct API catalogue query
- What appears as harness on betfair.com.au is the **Betfair Sportsbook** product (fixed odds), NOT the Exchange (lay prices)
- AU thoroughbred and greyhound Exchange markets exist and work; only harness is missing
- This means harness EV is calculated differently: bookie odds vs Betfair **Sportsbook** fixed odds (not Exchange lay), which has different pricing dynamics
- Betfair harness coverage is selective and volume-driven — smaller country meetings (Bathurst, Bendigo, Redcliffe) routinely excluded even for thoroughbreds
- Only 6 harness venues had Betfair coverage on the test day (Albion Park, Gloucester Park, Menangle, Port Pirie, Shepparton, Wagga)

## Details

### Sportsbook vs Exchange Products

Betfair operates two distinct products in Australia:

| Product | Type | Price Source | Available for Harness |
|---------|------|-------------|----------------------|
| **Exchange** | Peer-to-peer marketplace | Back/lay prices from other punters | **No** — zero harness markets |
| **Sportsbook** | Traditional fixed-odds | Betfair's own market-making team | Yes — harness odds available |

The Exchange is the product the SuperWin scanner uses for EV calculation: the lay price represents the market's view of fair value, and `bookie_odds / betfair_lay - 1` gives the EV estimate. Without Exchange markets, the scanner falls back to whatever Betfair price is available — which for harness means either no Betfair reference at all or the Sportsbook fixed-odds price (a fundamentally different pricing mechanism).

### Impact on SuperWin's Best Edge

AU harness racing is the scanner's most profitable segment at +39% ROI on 919 picks, generating 83% of total profit from only 21% of picks (see [[concepts/superwin-racing-profitability-dimensions]]). The absence of Exchange lay prices for harness means:

1. **EV calculation uses a different baseline** — Sportsbook odds instead of Exchange lay, or no Betfair reference at all
2. **Liquidity filtering is meaningless** — `total_matched` and `selection_matched` are Exchange concepts; Sportsbook has no equivalent
3. **CLV against BSP/LTP is impossible** — BSP (Betfair Starting Price) is an Exchange-only feature; harness picks have no BSP

The orange dots visible in the BookieView dashboard component for harness races correctly indicate "no Betfair market" — this is real data, not a display bug. Venue aliases in the database are correct; if Betfair ever adds Exchange harness markets, the resolver will match automatically.

### Selective Coverage Pattern

Even for thoroughbred racing where Betfair Exchange does operate, coverage is volume-driven. Smaller country meetings (Bathurst, Bendigo, Redcliffe) are routinely excluded — Betfair only runs Exchange markets where there's sufficient trading interest. On the test day, only 6 of ~12 harness venues had any Betfair presence (all Sportsbook, not Exchange).

## Related Concepts

- [[concepts/superwin-racing-profitability-dimensions]] - AU harness is the #1 edge at +39% ROI; the Exchange gap means this edge operates without the standard Betfair reference
- [[concepts/superwin-edge-pick-backtesting]] - CLV against BSP is the gold standard for racing backtesting; harness picks can never have BSP-based CLV
- [[concepts/superwin-mult-place-market-edge]] - THE MULT place edge also uses Betfair lay prices; harness MULT picks have the same Exchange gap
- [[connections/liquidity-efficiency-inverse-in-betting]] - The liquidity-efficiency relationship documented for thoroughbreds may not apply to harness if the pricing mechanism is fundamentally different

## Sources

- [[daily/lcash/2026-05-20.md]] - Betfair Exchange confirmed zero AU harness markets via API catalogue; what appears as harness on betfair.com.au is Sportsbook (fixed-odds) not Exchange; only 6 harness venues had Betfair coverage; orange dots in BookieView correctly indicate "no Betfair market"; venue aliases verified correct in DB (Sessions 08:29, 09:00)
