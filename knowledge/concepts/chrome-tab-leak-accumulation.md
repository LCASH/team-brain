---
title: "Chrome Tab Leak Accumulation"
aliases: [chrome-tab-leak, stale-tabs, tab-accumulation, chrome-tab-bloat]
tags: [value-betting, bet365, chrome, scraping, reliability, operations]
sources:
  - "daily/lcash/2026-04-27.md"
created: 2026-04-27
updated: 2026-04-27
---

# Chrome Tab Leak Accumulation

The bet365 game scrapers (both NBA and MLB) continuously open new Chrome tabs/pages without closing old ones. Over time this accumulates 51+ stale tabs, progressively degrading Chrome's performance until `page.goto()` calls timeout and the scrapers become non-functional. Both NBA and MLB scrapers are affected simultaneously because they share Chrome on port 9223. The fix is to kill Chrome entirely and let workers auto-relaunch — but the tab leak itself remains an unpatched code-level bug.

## Key Points

- Both bet365 NBA and MLB scrapers accumulate stale tabs — 51 stale tabs found during a single investigation
- Progressive degradation: Chrome bogs down gradually as tab count increases until navigation timeouts occur — unlike a crash (which auto-recovery handles), this is a slow death
- Both scrapers share Chrome on port 9223 (see [[concepts/bet365-shared-chrome-single-session]]), so tab bloat from one scraper affects the other
- Killing Chrome entirely (58 processes) and letting workers auto-recover is the current workaround — both workers recovered cleanly
- Chrome on port 9224 was found unresponsive — unclear if it should exist or is a leftover from before the shared-Chrome consolidation
- This failure mode is distinct from EPIPE/crash-recovery (see [[concepts/game-scraper-chrome-crash-recovery]]) — tabs accumulate during normal operation, not after crashes

## Details

### The Failure Mode

Unlike Chrome crashes (which produce immediate pipe breaks and trigger the auto-recovery mechanism), tab accumulation is a **gradual degradation** failure. Each scraper cycle opens a new page to navigate to a game, but old page references are not closed. Chrome maintains all tabs in memory, with each tab consuming 100-400 MB of RAM and contributing to CPU overhead from background JavaScript execution in the bet365 SPA.

At low tab counts (5-10), the performance impact is negligible. As tabs accumulate past 20-30, Chrome's internal page management begins to slow. By 51+ tabs, `page.goto()` calls consistently timeout because Chrome cannot allocate resources for a new page load while maintaining all existing tabs. The scraper's timeout handler logs a warning but continues retrying — each retry attempt also fails, and the scraper produces zero fresh data while consuming resources.

This is particularly dangerous because the auto-recovery mechanism (see [[concepts/game-scraper-chrome-crash-recovery]]) is designed for EPIPE/crash failures, not for gradual degradation. The Chrome process is alive, CDP connections are responsive, and the page object exists — the scraper appears "healthy" to process-level monitoring. Only the `0.0ms` scrape time diagnostic (from stale cached data) would catch this, and only if that metric is monitored.

### Shared Chrome Amplification

The consolidation to a shared Chrome on port 9223 (see [[concepts/bet365-shared-chrome-single-session]]) means tab leaks from either scraper affect both. The MLB scraper opening 8 tabs per rotation cycle without closing them accumulates 48+ tabs in a 6-rotation window. The NBA scraper's own tab usage on top of this pushes Chrome past its functional limit even faster. Prior to the shared-Chrome consolidation, each scraper's tab leak only affected its own Chrome instance.

### Current Workaround

Killing all Chrome processes (`taskkill /F /IM chrome.exe`) and letting both scrapers' auto-recovery mechanisms relaunch Chrome is the fastest remediation. Both NBA and MLB workers detected the dead Chrome and auto-recovered cleanly — confirming the auto-recovery mechanism works for externally-killed Chrome as well as EPIPE crashes.

### Root Cause

The scrapers use `context.new_page()` or `browser.new_page()` to create page objects for game navigation but never call `page.close()` on the previous page before creating a new one. The fix is to track the current page reference and close it before opening a new one. This is a straightforward code change in both `bet365_game_worker.py` (NBA) and the MLB scraper, but has not been deployed yet.

## Related Concepts

- [[concepts/game-scraper-chrome-crash-recovery]] - The crash auto-recovery mechanism (EPIPE → 5 failures → stop/start) that handles sudden Chrome death; tab leaks are a different failure class that this mechanism doesn't detect
- [[concepts/bet365-shared-chrome-single-session]] - Shared Chrome on port 9223 amplifies the tab leak impact across both scrapers
- [[connections/browser-automation-reliability-cost]] - Tab leaks add a sixth reliability dimension: progressive resource exhaustion during normal operation, not triggered by errors or crashes
- [[concepts/worker-status-observability]] - Tab count should be a health metric; scrapers report "streaming" while Chrome is drowning in stale tabs
- [[concepts/mlb-parallel-scraper-workers]] - The MLB scraper was reverted to N_WORKERS=1 partly because multiple workers opening pages in shared Chrome crashed the context; tab leaks compound this problem

## Sources

- [[daily/lcash/2026-04-27.md]] - Both bet365 NBA and MLB scrapers non-functional; Chrome had 51 stale tabs causing navigation timeouts; killed all 58 Chrome processes; both workers auto-recovered cleanly; tab leak is the root cause — workers open tabs without closing old ones; port 9224 Chrome unresponsive (leftover); tab count monitoring recommended for /vb health (Session 17:34)
