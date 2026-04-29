---
title: "News Agent Classifier Vocabulary Gaps"
aliases: [classifier-misclassification, roster-transaction-gap, stale-team-mapping, sport-detection-default-bug, live-roster-injection]
tags: [value-betting, news-pipeline, ai-agent, classifier, bug, data-quality]
sources:
  - "daily/lcash/2026-04-29.md"
created: 2026-04-29
updated: 2026-04-29
---

# News Agent Classifier Vocabulary Gaps

The news agent pipeline's Haiku classifier (Stage 1) had multiple vocabulary and configuration gaps that caused misclassification of non-actionable events, stale team mapping from LLM training data, and a critical sport detection bug. On 2026-04-29, three distinct failure patterns were identified and fixed: (1) roster transactions (outrighted/DFA/optioned) misclassified as game-day status changes, (2) KD mapped to Phoenix Suns (old team) instead of Houston Rockets despite the tweet explicitly naming the Rockets, and (3) `--sport default="nba"` silently breaking MLB auto-detection via Python's `or` short-circuit.

## Key Points

- **Roster transaction vocabulary gap**: Cubs outrighting Scott Kingery classified as `[scratched]` — the classifier prompt lacked BLOCK rules for waiver/DFA/outright/option-to-minors roster moves, coaching changes, and MLB debuts
- **Stale team mapping**: KD tweet explicitly said "Rockets" but classifier mapped KD to Phoenix Suns from stale training data; fix: inject live player rosters from VPS odds API into classifier prompt + "trust team name in tweet over your knowledge" rule
- **Sport detection default bug**: `--sport default="nba"` is truthy, so `sport or _detect_sport_from_source()` short-circuits — auto-detection never ran, every MLB tweet processed as NBA, fetching NBA markets for MLB players → 0 picks
- **Silent early-exit paths**: Three paths after PASSED Discord message (dedup, no-odds, analysis-0-picks) — only the last posted to Discord, making debugging impossible when pipeline went quiet
- **Injured players absent from roster**: Classifier must NOT block tweets about players missing from the live roster — they're missing BECAUSE they're injured
- Each misclassification burned $0.20-0.65 in Stage 2 compute (Sonnet analyst) for structurally un-pickable news

## Details

### Roster Transaction Misclassification

The Haiku classifier's event type schema was designed for game-day status changes: `injury_out`, `injury_questionable`, `scratched`, `return`, `il_placement`, `pitching_change`. When the classifier encountered "Cubs Outright Scott Kingery" — a 40-man roster transaction — it had no matching category and force-fit the tweet into `scratched` (the closest available label for "player removed from active status").

The PASSED tweet flowed through to Stage 2 (Sonnet analyst), which attempted to fetch odds for Scott Kingery and found none — a silent early exit with no Discord notification explaining why. The operator saw PASSED in Discord but no subsequent picks or explanation, making the pipeline appear broken rather than correctly filtering a non-actionable event.

Similarly, Travis Bazzana's MLB debut was labeled `[return]` and Don Mattingly's firing was labeled `[signing]` — the classifier consistently force-fits unrecognized event types into the nearest available schema category.

The fix added explicit BLOCK rules to the classifier's SYSTEM_PROMPT:
- Waiver/DFA/outright/option-to-minors roster transactions
- Coaching/manager hiring and firing
- MLB debuts and first call-ups
- Fringe call-ups from minors

Veteran IL activations and recalls of established players still PASS through — they have active prop markets and can generate valid picks.

### Stale Training Data Team Mapping

When KD's tweet about being ruled out was processed, the classifier extracted `team: "Phoenix Suns"` despite the tweet explicitly containing "Rockets." The Haiku model's training data includes KD's long tenure with the Suns (2023-2025), and this association overrode the explicit text context. This is a fundamental LLM limitation: stale training data creates strong priors that can override explicit context, especially for well-known player-team associations.

The two-part fix:
1. **Prompt engineering**: Added "trust the team name mentioned in the tweet over your prior knowledge" as an explicit instruction rule
2. **Live roster injection**: The classifier prompt now includes a live player roster fetched from the VPS odds API (commit `f57f557`). The roster shows current team-player associations, grounding the classifier in actual current data rather than training data

A subtle edge case: injured players (the exact players the news agent is designed to detect) won't appear in the live odds roster because sportsbooks remove their prop markets when they're ruled out. The classifier must not treat "player not in roster" as a blocking signal — the absence IS the signal.

### Sport Detection Default Bug

The `--sport` CLI argument defaulted to `"nba"` (a truthy string value). In the runner's sport resolution code:

```python
sport = args.sport or _detect_sport_from_source(tweet_source)
```

Since `"nba"` is truthy, the `or` expression short-circuits — `_detect_sport_from_source()` never executes. Every tweet from MLB sources (Jeff Passan, Ken Rosenthal, MLBTradeRumors) was processed as NBA, causing the pipeline to:
1. Fetch NBA markets (not MLB)
2. Build an NBA odds workspace
3. Attempt to find the MLB player in NBA data → 0 matches → 0 picks

The fix changed the default to `None`:
```python
sport = args.sport or _detect_sport_from_source(tweet_source)
# Now: None or _detect_sport_from_source() → auto-detection runs
```

This bug was particularly insidious because the pipeline produced no errors — it silently processed MLB news through the NBA pipeline, found no matching odds, and exited cleanly.

### Silent Early-Exit Paths

After the classifier posts a PASSED message to Discord, three early-exit paths can prevent picks from being generated:

1. **Dedup**: Event already processed → silent exit
2. **No-odds**: Team not in current odds cache → silent exit (fixed: now posts `:warning: NO ODDS` to Discord)
3. **Analysis-0-picks**: Stage 2 ran but generated no recommendations → posts to Discord

Only path 3 posted a notification. Paths 1 and 2 were silent, making the pipeline appear dead when it was actually working correctly. The no-odds path was the most common culprit — when a game has ended or the team isn't playing today, the odds cache has no entries.

### Discord Webhook as Primary Monitoring

All pipeline decision points now post to a Discord webhook:
- Tweet blocked by classifier → reason shown
- Tweet passed → event details shown
- No odds found → `:warning: NO ODDS for {team}` warning
- Stage 2 completed → pick count and details
- Stage 2 generated 0 picks → explanation

This eliminates the "pipeline went quiet" debugging problem — every tweet's journey through the pipeline is visible in Discord without checking logs.

### Stale `.pyc` Files

During deployment of classifier fixes, the agent kept running old code despite source file edits. Python's `__pycache__` directory cached the pre-fix `.pyc` bytecode. Must clear `__pycache__` on every deploy to ensure fresh code execution. This follows the pattern of stale deployment artifacts documented in [[concepts/configuration-drift-manual-launch]].

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The pipeline architecture whose Stage 1 classifier had these gaps; fixes deployed as commit `f57f557` with live roster injection
- [[concepts/news-driven-pre-sharp-ev-thesis]] - The strategic thesis depends on correct event classification — misclassified non-actionable events waste compute and miss actionable ones
- [[connections/sport-specific-news-intelligence-architecture]] - NBA vs MLB source hierarchies; the sport detection bug broke the auto-routing between these hierarchies
- [[connections/silent-type-coercion-data-corruption]] - The sport detection default bug (`"nba" or auto_detect()` short-circuit) is another instance of plausible wrong output with zero error signal
- [[concepts/twitter-x-api-scraping-constraints]] - Twitter rate limits make wasted classifier calls more costly — each misclassified tweet that reaches Stage 2 burns $0.65 of Sonnet compute
- [[concepts/configuration-drift-manual-launch]] - Stale `.pyc` files are a deployment artifact drift; `__pycache__` must be cleared on deploy

## Sources

- [[daily/lcash/2026-04-29.md]] - KD→Suns stale team mapping despite explicit "Rockets" in tweet; live roster injection from VPS odds API (commit f57f557); injured players absent from roster edge case (Session 09:57). Cubs outrighting Kingery classified as `[scratched]`; Bazzana debut as `[return]`; Mattingly firing as `[signing]`; BLOCK rules added for roster transactions, coaching changes, debuts (Sessions 14:21, 15:32). `--sport default="nba"` broke MLB auto-detection via `or` short-circuit; fix: default to `None` (Session 12:38). Three silent early-exit paths after PASSED; Discord webhook monitoring at every decision point; stale `.pyc` files caused deployment failures (Sessions 12:38, 15:32). `twitter_scraper.py:165-166` swallows all exceptions silently — GraphQL qid rotation would kill agent with zero indication (Session 15:32)
