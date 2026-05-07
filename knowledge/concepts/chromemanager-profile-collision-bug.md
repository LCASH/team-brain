---
title: "ChromeManager Profile Name Collision Bug"
aliases: [profile-collision, cdp-profile-collision, chromemanager-kill-stale-bug, profile-name-default]
tags: [value-betting, bet365, chrome, bug, cdp, architecture]
sources:
  - "daily/lcash/2026-05-05.md"
created: 2026-05-05
updated: 2026-05-05
---

# ChromeManager Profile Name Collision Bug

Both the NBA and MLB `ChromeManager` instances defaulted to `profile_name="cdp_profile"`. When the MLB scraper called `kill_stale()` — which terminates Chrome processes matching the profile name string in their command line — it matched **both** Chrome instances and killed NBA's Chrome. This one-liner default had a disproportionately large blast radius: NBA's Chrome died, its scraper lost all game pages and CDP connections, and the NBA pipeline went dark with no obvious error pointing to MLB as the cause.

## Key Points

- **Root cause**: Both `ChromeManager` instances used `profile_name="cdp_profile"` as default — `kill_stale()` matched both Chrome processes by this shared string
- **Blast radius**: MLB calling `kill_stale()` killed NBA's Chrome — a cross-sport side effect from a shared default value
- **Fix**: Port-specific default profile names (`cdp_9223` for NBA, `cdp_9224` for MLB) — `kill_stale()` now only matches the intended Chrome instance
- **Discovery**: NBA Chrome kept dying on launch with no obvious error; traced through Playwright `pw.stop()` sending `Browser.close` (a separate bug) before identifying the shared profile name as the actual root cause
- This is a variant of the `_kill_stale_chrome()` path-matching issue documented in [[concepts/cdp-stale-connection-poisoning]] — same mechanism (string matching on Chrome command line) but caused by a shared default instead of a path format mismatch

## Details

### The Failure Mode

The V3 scanner runs two Chrome instances: NBA on port 9223 and MLB on port 9224, each managed by a separate `ChromeManager` instance. The `kill_stale()` method terminates any Chrome process whose command line contains the profile directory name — this is the "always fresh Chrome" pattern from [[concepts/cdp-stale-connection-poisoning]] that ensures clean state on worker start.

When both managers shared `profile_name="cdp_profile"`, the string `cdp_profile` appeared in both Chrome instances' command lines. MLB's `kill_stale()` found both processes, terminated both, and relaunched only MLB's Chrome. NBA's Chrome was collateral damage — killed without any indication in NBA's logs that MLB was the cause.

The NBA scraper then attempted to connect to its Chrome on port 9223, found nothing listening, and failed with a connection error. From the NBA scraper's perspective, Chrome had spontaneously died — identical in symptoms to a genuine Chrome crash (see [[concepts/game-scraper-chrome-crash-recovery]]).

### Why This Was Hard to Diagnose

The investigation traversed two false leads before reaching the root cause:

1. **Playwright `pw.stop()` bug**: Investigation discovered that `pw.stop()` sends `Browser.close` CDP command even on `connect_over_cdp` connections, killing all tabs. This was a real bug (fixed by not calling `pw.stop()` and keeping the Playwright instance alive at module level) but was not the primary cause of Chrome death.

2. **Login button selector not found**: The Playwright login flow's button selector wasn't matching, causing a hard failure. Fixed with a fallback polling loop (5-minute manual mode), but this was a symptom of Chrome being dead, not the cause.

Only after both red herrings were addressed did the pattern emerge: NBA Chrome died specifically when MLB was starting — every time, consistently. Inspecting what MLB's startup did differently led to `kill_stale()` and the shared profile name.

### The Fix

The fix is a one-liner: make `profile_name` default to `f"cdp_{port}"` instead of `"cdp_profile"`. NBA gets `cdp_9223`, MLB gets `cdp_9224`. Each `kill_stale()` now only matches its own Chrome instance. This follows the same principle as the path-matching fix in [[concepts/cdp-stale-connection-poisoning]] — the match string must be unique per Chrome instance.

### Broader Pattern: Shared Defaults in Multi-Instance Systems

This bug is an instance of a general anti-pattern: using identical default configuration values for multiple instances of the same component. When any instance-specific operation (like cleanup/kill) uses the shared value as a selector, it affects all instances instead of just the target. The fix is always the same: make instance-identifying configuration unique by default, derived from a distinguishing property (port, sport, process ID, etc.) rather than relying on operators to override defaults.

## Related Concepts

- [[concepts/cdp-stale-connection-poisoning]] - The `kill_stale()` mechanism that uses profile name matching; the profile collision is a new failure mode of the same cleanup pattern
- [[concepts/bet365-shared-chrome-single-session]] - The shared vs separate Chrome architecture; profile collision reinforces the importance of distinct per-sport Chrome identity
- [[concepts/v3-scanner-centralized-architecture]] - The V3 modular architecture where ChromeManager is a shared abstraction used by both sport scrapers
- [[connections/chrome-lifecycle-management-pattern]] - The unified lifecycle pattern that now includes "unique profile names per instance" as a fifth rule

## Sources

- [[daily/lcash/2026-05-05.md]] - NBA Chrome kept dying on launch; traced through pw.stop() Browser.close and login selector failures before identifying shared `profile_name="cdp_profile"` as root cause; MLB kill_stale() matched both Chrome instances; fix: port-specific defaults (`cdp_9223`, `cdp_9224`); one-liner bug with large blast radius (Session 18:25)
