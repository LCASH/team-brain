---
title: "Pick Creation vs Trail Recording Time Separation"
aliases: [pick-trail-split, early-pick-creation, max-hours-before-start-split, trail-timing-separation]
tags: [value-betting, architecture, tracker, trail-data, configuration]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# Pick Creation vs Trail Recording Time Separation

The value betting scanner previously used a single `max_hours_before_start` parameter to gate both pick creation and trail recording. This meant that picks from books posting early (like TAB threshold markets at 10+ hours before tipoff) were silently filtered out. On 2026-04-24, the architecture was split: picks are now stored at 24 hours before game (capturing early +EV from threshold props), while trails start recording at 3 hours before game (saving I/O by only tracking odds movement in the actionable betting window).

## Key Points

- Previously `max_hours_before_start=3` gated **everything** — both pick creation and trail recording
- TAB threshold markets are posted 10+ hours before tipoff but were invisible to the tracker because the 3h window excluded them
- Fix: pick creation at 24h before game (captures early +EV signals), trail recording at 3h before game (saves I/O, records odds movement that matters for backtesting)
- The 3h trail window is deliberate — odds movement 10+ hours out is noise; the meaningful movement happens in the hours before tipoff when sharp action arrives
- This was the non-obvious root cause of "zero TAB picks" despite data being present in VPS state and theories correctly configured

## Details

### The Problem

When TAB (book_id 908) was integrated on 2026-04-24, its threshold markets (e.g., "20+ Points", "10+ Rebounds") were visible in the VPS market state — 274 fresh markets with sharp overlap. Theory configurations included 908 as a soft book. `max_line_gap=4` was set to enable interpolation. Yet zero TAB picks appeared.

The root cause was `max_hours_before_start=3` on all NBA theories. This parameter was designed to prevent the tracker from evaluating markets too far from game time, where odds are less reliable and trails would accumulate unnecessary I/O. But it had the unintended effect of blanket-excluding any market more than 3 hours from tip-off — including TAB threshold markets that are posted 10+ hours before game time.

The parameter served two distinct purposes with conflicting requirements:
1. **Pick creation**: Should capture +EV signals whenever they appear, including early postings from books like TAB
2. **Trail recording**: Should only write trail entries close to game time, where odds movement reflects genuine market adjustment

### The Fix

Setting `max_hours_before_start=24` on standard theories decouples the timing:

- **Pick creation (24h)**: The tracker evaluates any market up to 24 hours before game time. If a TAB threshold market shows +EV at 10 hours out, the pick is created and stored in Supabase immediately.
- **Trail recording (3h)**: Phase B trail collection only writes entries for picks within 3 hours of game time. This preserves the original intent of not wasting I/O on early, noisy odds movement.

The 3-hour trail window aligns with the typical betting window — the period when a bettor would realistically act on a pick and when odds movement is most informative for backtesting and CLV analysis (see [[concepts/betting-window-roi-methodology]]).

### Implications for Other Books

TAB is the first soft book that posts threshold-style markets far in advance, but the architectural change benefits any future soft book with early market availability. Prediction markets (Kalshi, Polymarket) also post lines well before game time — the 24h window ensures these are captured at detection time rather than waiting until the 3h window.

The change affects all soft books evaluated by the theory (not just TAB), but since most soft books don't post lines more than a few hours before game time, the practical impact is limited to TAB threshold markets and prediction markets.

## Related Concepts

- [[concepts/tab-scraper-threshold-markets]] - The TAB integration that exposed the need for this timing separation
- [[concepts/value-betting-theory-system]] - The theory system where `max_hours_before_start` is configured per-theory via Supabase
- [[concepts/betting-window-roi-methodology]] - The 3h betting window analysis that defines the trail recording period
- [[concepts/trail-data-temporal-resolution]] - Trail data quality considerations that inform the 3h trail recording threshold
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - A parallel "silent filtering" pattern: time window filters and ACTIVE_SPORTS both silently excluded valid data

## Sources

- [[daily/lcash/2026-04-24.md]] - TAB threshold markets were silently filtered by `max_hours_before_start=3`; separated pick creation (24h) from trail recording (3h); set `max_hours_before_start=24` on standard theories so early threshold markets get evaluated; debugging order for "0 picks" established: data presence → theory soft_books → time window → max_line_gap (Session 14:09)
