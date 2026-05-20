---
title: "Unverified Fix Deployment Anti-Pattern"
aliases: [deploy-without-verifying, third-party-fix-trust, confirm-before-deploy, b8steel-investigation]
tags: [value-betting, operations, methodology, anti-pattern, deployment]
sources:
  - "daily/lcash/2026-05-19.md"
created: 2026-05-19
updated: 2026-05-19
---

# Unverified Fix Deployment Anti-Pattern

On 2026-05-19, lcash deployed a dashboard fix (cross-val gate 5pp→10pp, commit `fb50b20`) based on b8steel's bug findings without independently verifying the claims. The user corrected this approach: b8steel's findings are hypotheses until independently reproduced, and "option B" for a fix shape does not mean "deploy it now." The incident codified a discipline: **theorize → test → verify** applies to other people's theories too, and deploy intent must be confirmed separately from fix-shape preference.

## Key Points

- **Deployed `fb50b20` to VPS + pushed to main** based on b8steel's claim that cross-val gate at 5pp was hiding picks — without independently checking whether 5pp was correct or 10pp would be better
- **User correction**: "b8steel's findings should NOT be taken as truth — need proper investigation plan to independently verify each claim before making changes"
- **The misread**: User said "B" meaning "investigate approach B (1-line fix)" — assistant interpreted as "ship approach B now." Deploy intent must be confirmed separately from approach preference
- **Broader principle**: When receiving bug reports from external contributors, treat them as hypotheses requiring independent reproduction, not as verified truths requiring immediate fixes
- **Multiple b8steel claims require systematic investigation**: cross-val gate, server weight fallback in `engine.py`, stacked filters (MAX_ODDS_AGE_S, prop_filter, candidates bypass, Pinnacle Only phantom picks)

## Details

### The Incident

b8steel submitted findings via GitHub identifying two potential engine bugs:

1. **Cross-val gate in `dashboard/index.html:2433-2445`**: Claims the 5pp delta threshold was hiding valid picks by rejecting markets where sharp-vs-soft devigged prices disagree by more than 5 percentage points
2. **Server weight fallback in `engine.py:269,280,308`**: Claims the weight lookup defaults to 1.0 instead of 0.0 when a sharp book isn't in the theory's configured weights, meaning unconfigured books receive full weight instead of being excluded

lcash reviewed both findings, chose "B" (the 1-line cross-val gate fix as the simpler approach), and shipped it — changing the threshold from 5pp to 10pp, deploying to VPS, and pushing to main as commit `fb50b20`. The user's reaction was immediate: the fix should not have been deployed because b8steel's claims were unverified hypotheses.

### Why This Matters

The cross-val gate was originally added as a defensive measure against devigging anomalies (see [[concepts/alt-line-mismatch-poisoned-picks]]). Widening it from 5pp to 10pp lets more picks through — which could be correct (recovering legitimate picks that 5pp hid) or harmful (passing through phantom-EV picks that 5pp correctly blocked). Without independent reproduction of the claim, the change is a coin flip on data quality.

The engine.py weight fallback is potentially more severe: if unconfigured sharp books receive weight 1.0, every theory's devig is contaminated by books that shouldn't be contributing. But this claim also hasn't been verified — the default might be intentional (fall back to equal-weight when no explicit weight is configured) rather than a bug.

### The Investigation Discipline

The incident established a clear methodology for handling external contributor findings:

1. **Receive claims** — document what was claimed, where, and by whom
2. **Independently reproduce** — write test cases or queries that demonstrate the claimed behavior from scratch
3. **Verify math** — confirm the mathematical impact (does the 5pp→10pp change actually improve or degrade outcomes?)
4. **Check git history** — understand why the original code was written (the 5pp threshold had a reason — see cross-validation gate in [[concepts/alt-line-mismatch-poisoned-picks]])
5. **Test fix behavior** — deploy to staging/local first, verify the fix produces expected changes in pick volume and EV distribution
6. **Only then deploy** — with clear understanding of impact and reversibility

### Outstanding B8steel Claims

A comprehensive investigation plan is needed covering all b8steel claims:

| Claim | Location | Status | Risk |
|-------|----------|--------|------|
| Cross-val gate hiding picks | `dashboard/index.html:2433-2445` | **Deployed without verification** (`fb50b20`) | May pass phantom-EV picks |
| Weight fallback defaults to 1.0 | `engine.py:269,280,308` | Not deployed | May contaminate all theory devigs |
| MAX_ODDS_AGE_S filter too aggressive | Engine staleness filter | Not investigated | May reject valid stable lines |
| Basic-A prop_filter excluding markets | Theory configuration | Not investigated | May be intentional |
| Aggressive Live exclusions | Theory configuration | Not investigated | May be intentional |
| Candidates bypass | Engine evaluation path | Not investigated | May be architecturally correct |
| Pinnacle Only phantom picks | Theory evaluation | Not investigated | May indicate theory misconfiguration |

### The Confirmation Bias Risk

The deployed fix was acknowledged in a sharable document for b8steel as having been shipped "WITHOUT independently reproducing bug claims first" — an honest disclosure about confirmation bias risk. When someone presents a coherent theory about a bug, the temptation is to accept the theory and ship the fix because the explanation sounds plausible. But plausible-sounding explanations are exactly what make "plausible wrong output" bugs dangerous (see [[connections/silent-type-coercion-data-corruption]]).

## Related Concepts

- [[concepts/alt-line-mismatch-poisoned-picks]] - The cross-validation gate was built to prevent phantom-EV from unreliable interpolation; widening it without verification risks re-enabling the original failure mode
- [[concepts/engine-consensus-fallback-ev-contamination]] - The consensus-fallback gate (separate from cross-val) was accepted as a modeling change in the same session; both represent engine-level changes that affect all downstream data
- [[concepts/deploy-syntax-validation-gap]] - A related deploy discipline issue: no pre-deploy syntax check. This article adds a new dimension: no pre-deploy claim verification
- [[connections/silent-type-coercion-data-corruption]] - The risk of confirmation bias: plausible-sounding bug theories can be wrong, and deploying based on them creates plausible wrong output

## Sources

- [[daily/lcash/2026-05-19.md]] - Pulled b8steel's two findings from GitHub; user said "B", assistant shipped cross-val gate 5pp→10pp to VPS + pushed to main as `fb50b20`; user corrected: findings are hypotheses, not truth; deploy intent must be confirmed separately from approach preference; b8steel's claims should be independently verified before changes; engine.py weight fallback NOT deployed — needs verification first; comprehensive investigation plan covering all claims needed (Session 11:05)
