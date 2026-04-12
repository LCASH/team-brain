---
title: "Cumulative vs Filtered Display Pattern"
aliases: [summary-vs-detail-filtering, cumulative-summary-cards, filter-scope-pattern]
tags: [ui, ux, dashboard, filtering, design-patterns]
sources:
  - "daily/carts00/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Cumulative vs Filtered Display Pattern

A UI pattern where summary/aggregate cards always display cumulative totals for their fixed time periods (Today, This Week, This Month, All Time) regardless of the active filter, while detail views (stats cards, data tables) respect the currently selected filter. This creates a two-tier information hierarchy: persistent context at the top, filtered detail below.

## Key Points

- Period summary cards (Today/Week/Month/All Time) show cumulative totals that never change with filter selection
- Stats cards and data tables below the summaries respond to the active time filter (Today/This week/This month/This year/All time)
- This separation prevents the disorienting UX of summary numbers changing when a user adjusts a detail filter
- The pattern is applied consistently across multiple analysis pages (5 pages in the TAKEOVER app)
- Default filter is "This week" — a deliberate choice balancing recency with enough data to be meaningful

## Details

When dashboards mix summary metrics with filterable detail views, a common design question is whether the summaries should respect the same filter as the details. The cumulative-vs-filtered pattern deliberately decouples them: summary cards serve as fixed reference points that provide context ("here's where you stand overall"), while the detail section below answers the user's specific query ("show me this week's data").

This pattern was implemented across all five analysis pages in the TAKEOVER-dev betting analysis app by carts00. Each page features period summary cards at the top (showing cumulative totals for Today, This Week, This Month, and All Time) with filter buttons below (Today/This week/This month/This year/All time) that control the stats cards and bets table. The deliberate asymmetry — summaries pinned, details filtered — means a user looking at "This month" detail data always sees their "All Time" total for context, reducing the need to toggle back and forth.

The decision to default all filters to "This week" rather than "Today" or "All time" reflects a practical tradeoff: "Today" often has too little data to show meaningful trends, while "All time" can be overwhelming. "This week" provides a recent-enough window that the data feels current while including enough volume for patterns to emerge.

## Related Concepts

- [[concepts/parlay-ev-calculation]] - Part of the same betting analysis domain in the TAKEOVER app
- [[concepts/team-knowledge-base-architecture]] - The system enabling cross-developer sharing of UI pattern decisions

## Sources

- [[daily/carts00/2026-04-10.md]] - carts00 implemented this pattern across 5 analysis pages: period summary cards always cumulative, stats cards and bets table respect the active filter; default filter set to "This week"
