---
title: "Parlay EV Calculation"
aliases: [parlay-expected-value, boosted-parlay-ev, parlay-true-odds]
tags: [betting, mathematics, expected-value, parlays]
sources:
  - "daily/carts00/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Parlay EV Calculation

A method for calculating the true expected value (EV) of a parlay bet, particularly useful for evaluating whether sportsbook "boosts" or promotions actually offer positive expected value. The core technique involves computing each leg's true odds independently, multiplying them to get the combined true odds, and comparing against the offered (boosted) odds.

## Key Points

- True combined odds for a parlay equal the product of each leg's individual true odds (assuming independence)
- A boosted parlay is only +EV if the boosted odds exceed the true combined odds
- Sportsbooks frequently offer "boosts" that appear generous but are still -EV when calculated against true odds
- The percentage EV is calculated as: `(boosted_odds - true_odds) / true_odds × 100`
- A negative EV% means the boost does not overcome the built-in margin, even with the promotion applied

## Details

Parlay bets combine multiple independent selections into a single wager, where all legs must win for the bet to pay out. The true odds of a parlay are the product of each leg's true probability expressed as decimal odds. Sportsbooks often offer "boosted" parlays with enhanced payouts as promotions, but these boosts may not be sufficient to make the bet +EV.

The calculation method follows these steps: (1) determine the true odds for each leg using sharp book prices or a devigging model, (2) multiply all leg odds together to get the true combined decimal odds, (3) compare the result against the boosted decimal odds offered by the sportsbook. If the true combined odds are higher than the boosted odds, the bet is -EV despite the boost.

A concrete example from carts00's analysis of a golf parlay illustrates the method: Scottie Scheffler Top 10 at true odds 1.83, Bryson DeChambeau Top 10 at true odds 2.96, and Rory McIlroy Top 20 at true odds 1.73. The true combined odds are 1.83 × 2.96 × 1.73 = 9.37. The sportsbook offered boosted odds of 7.75, which included a stated 50% winnings boost. Since 7.75 < 9.37, the bet was -17.3% EV — the boost was insufficient to overcome the margin. This demonstrates that even aggressive-sounding promotions can be -EV when the underlying parlay has high combined true odds.

This method assumes leg independence. In practice, correlated legs (e.g., two golfers from the same group, or same-game parlays) require correlation adjustments that make the true odds calculation more complex.

## Related Concepts

- [[concepts/claude-code-skills-directory]] - Discovered in the same session during TAKEOVER app analysis work
- [[concepts/team-knowledge-base-architecture]] - The system that enables cross-team sharing of domain insights like this

## Sources

- [[daily/carts00/2026-04-10.md]] - carts00 calculated true odds for a golf parlay: Scottie (1.83) × Bryson (2.96) × Rory (1.73) = 9.37 true odds vs 7.75 boosted → -17.3% EV
