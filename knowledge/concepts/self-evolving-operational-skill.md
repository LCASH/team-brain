---
title: "Self-Evolving Operational Skill"
aliases: [checkup-skill, self-updating-skill, operational-runbook-skill]
tags: [operations, claude-code, skills, monitoring, value-betting]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-15
---

# Self-Evolving Operational Skill

A pattern for Claude Code skills that function as operational runbooks and self-update after each execution. The `/checkup` skill for the value betting scanner covers all 5 sport servers, data integrity checks, and known fixes, and evolves its own known-fix database, expected baselines, and changelog after each run. This turns operational knowledge from ephemeral (remembered by individuals) into persistent (encoded in the skill).

## Key Points

- The `/checkup` skill is a comprehensive health check covering all 5 sport servers (NBA, NRL, AFL, MLB, VPS), data integrity, and known failure patterns
- After each run, the skill updates itself: new known-fine states, resolved issues, updated baselines, and changelog entries
- The skill file lives in `.claude/skills/checkup.md` which is gitignored — changes stay local to the workspace
- Includes win-rate calibration by EV bucket (Check 10), tracker silence explanations, and known states like `idle_no_fixtures` and `stale` for off-hours workers
- The pattern transforms operational knowledge from "things someone remembers" into "executable, evolving documentation"

## Details

### The Pattern

Traditional operational runbooks are static documents that decay as systems change. The self-evolving skill pattern addresses this by making the runbook executable (it runs checks and produces a report) and self-modifying (it incorporates findings from each run into its own definition). When a new failure pattern is discovered and resolved, the skill adds it to its known-fix database. When a previously unknown state is determined to be benign, the skill adds it to its known-fine states. Each update includes a changelog entry, creating an audit trail of operational learning.

This creates a feedback loop: the skill runs, discovers an issue, the operator debugs and fixes it, the operator updates the skill with the fix, and future runs recognize the pattern automatically. Over time, the skill accumulates the team's operational knowledge, reducing the debugging burden on experienced operators and enabling less-experienced team members to perform health checks.

### Implementation: /checkup

The value betting scanner's `/checkup` skill was created on 2026-04-13 during a session where recurring data quality issues (poisoned picks from alt-line mismatches) highlighted the need for systematic health checking. The skill covers:

1. **Server connectivity** — checks all 5 sport servers are reachable and responding
2. **Scraper health** — verifies expected scraper counts per sport, flags missing workers
3. **Data integrity** — checks for poisoned picks (triggered_ev > 50%), orphaned trail entries, fixture name deduplication
4. **Tracker status** — verifies tracker is cycling (last_run_age < 60s) even when idle (no games in window)
5. **Win-rate calibration** — compares observed win rates by EV bucket against expected calibration (Check 10)
6. **Known-fine states** — recognizes `idle_no_fixtures` for bet365_mlb_game, `stale` for off-hours workers, tracker silence during non-game windows
7. **Known fixes** — documents resolved issues (e.g., recurring high-EV contamination marked RESOLVED after interpolation fix)

The skill was updated during Session 22:50 with 6 additions: Check 10 (calibration), 3 new known-fine states, updated known fix entry for the alt-line mismatch issue (marked RESOLVED), tracker silence explanation, and changelog entries.

### Gitignore Consideration

The skill file lives at `.claude/skills/checkup.md`, and `.claude/` is gitignored in the value betting scanner repository. This means skill updates stay local to the workspace and are not pushed to git. This is a deliberate tradeoff: the skill evolves based on the operator's local experience and doesn't create merge conflicts across team members. The downside is that operational knowledge captured in the skill is not shared across the team — each developer would maintain their own version.

### Comparison to Static Monitoring

The self-evolving skill pattern complements rather than replaces static monitoring (cron scripts, webhooks). Static monitoring runs automatically on a schedule and alerts on thresholds. The skill is invoked on demand by a developer and provides contextual analysis — it knows what's normal for the current time of day, which issues were recently fixed, and what the expected baselines are. The combination of automated alerts (for detecting problems) and the skill (for diagnosing them) covers both detection and resolution.

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - The assessment that identified monitoring gaps, motivating this skill
- [[concepts/worker-status-observability]] - The status system whose values the skill interprets
- [[concepts/alt-line-mismatch-poisoned-picks]] - A known-fix entry in the skill (marked RESOLVED)
- [[concepts/silent-worker-authentication-failure]] - A failure pattern the skill helps diagnose

## Sources

- [[daily/lcash/2026-04-13.md]] - Created /checkup skill covering 5 servers, data integrity, known fixes, auto-evolves after each run (Session 16:31). Updated with Check 10 (calibration), 3 known-fine states, resolved high-EV fix, tracker silence explanation, changelog (Session 22:50). `.claude/` is gitignored — stays local (Session 22:50)
