---
title: "News-Driven Pre-Sharp EV Thesis"
aliases: [beating-sharps-to-news, conviction-based-picks, pre-sharp-ev, news-ev-thesis, ahead-of-market]
tags: [value-betting, strategy, news-pipeline, methodology, ai-agent]
sources:
  - "daily/lcash/2026-04-25.md"
created: 2026-04-25
updated: 2026-04-25
---

# News-Driven Pre-Sharp EV Thesis

The news agent pipeline's core strategic thesis is **beating sharps to news** — generating picks that may show negative EV at the moment of creation but will become positive EV once sharp books (Pinnacle, Circa) adjust their lines in response to the same news event. This inverts the standard value betting approach (find current +EV → bet it) into a predictive one (predict future +EV from news → bet before lines move → resolver validates over time). The EV validation gate was explicitly removed on 2026-04-25, replacing it with conviction-based pick creation where the agent explains its reasoning and the resolver validates retroactively.

## Key Points

- Standard VB scanner finds picks that are **currently** +EV vs sharp lines; news agent finds picks that **will become** +EV once sharps reprice — fundamentally different time horizons
- The EV validation gate was **removed** — a pick showing -3% EV at detection time is valid if the agent explains it's "ahead of the market" and the line is expected to move
- Resolver validates the thesis over time: if news-driven picks consistently show positive CLV (closing line moved toward the bettor's price), the strategy is working even if individual picks look -EV at trigger time
- Pre-computed full sportsbook odds are written to the workspace (~48KB per game) so the Sonnet agent can reason about which markets will shift — it needs ALL odds, not just pre-filtered +EV
- Each pick stores `news_source`, `agent_id`, `ai_reasoning`, and `ai_impact_chain` to enable multi-agent A/B testing and audit trails
- Marcus Smart pick (2026-04-25) exemplifies the thesis: -EV at detection but agent predicted line movement from KD injury news before books fully adjusted

## Details

### The Strategic Inversion

The value betting scanner's standard pipeline finds current mispricings: soft book prices that deviate from sharp book "true odds." This works when sharp books have already priced in all available information and soft books lag. The news agent inverts this: it assumes that **sharp books haven't yet repriced** to reflect breaking news, and that the current soft book prices (which also haven't repriced) represent a window of opportunity.

The edge window is the time between the news event (e.g., "Kevin Durant questionable for Game 3") and full market adjustment. For high-profile NBA injuries, this window is typically 4-15 minutes based on tweet-timing analysis: Shams Charania breaks the news, FantasyLabs follows 4 minutes later, and sportsbooks begin adjusting 5-20 minutes after initial reports depending on the book's news monitoring speed.

A pick generated at minute 2 (before even FantasyLabs has reported) will show negative EV against current sharp lines because those lines haven't moved yet. But by minute 15, the sharp lines will have adjusted toward the news-implied price, and the bettor who acted at minute 2 has positive CLV — they got a price better than where the market eventually settled.

### Removing the EV Gate

The original news agent (2026-04-24) included an EV validation step: after the Sonnet analyst generated pick recommendations, the pipeline checked whether each pick showed positive EV against current sharp odds before storing it. This gate was counterproductive because:

1. **It defeated the thesis.** A pick that's +EV against current sharps is a standard VB scanner pick — no news intelligence needed. The news agent's value is precisely in picks that are NOT yet +EV because sharps haven't moved.
2. **It filtered out the best opportunities.** The largest line movements (and thus the most profitable pre-sharp bets) are on news events where sharps haven't adjusted at all — producing the most negative "current EV" but the highest potential CLV.
3. **The resolver validates retroactively.** If the thesis is wrong and news-driven picks consistently have negative CLV (the market doesn't move as predicted), the backtest data will show this clearly. The EV gate was premature optimization — filtering before having enough data to validate.

### Workspace Architecture

The Sonnet analyst receives a comprehensive workspace including:

1. **Full sportsbook odds** grouped by player (every prop, every book, Pinnacle true line, EV column) — ~48KB per game, 764 lines for a single NBA game
2. **Event classification** from Stage 1 (Haiku): event type, player, team, impact assessment
3. **Historical context** available via web search: Game 1/2 precedent data, season stats, injury history

The workspace format matters: the agent needs ALL odds per game (not just pre-filtered +EV) because it must reason about which markets will shift. For example, a KD injury affects not just his own player props but also Houston's spread, total, and other players' usage rates. Pre-filtering to +EV markets would hide the markets most likely to move.

Workspace trimming was critical for reliability: the initial 90KB workspace caused Sonnet to timeout at 300s. Trimming to 48KB (removing redundant formatting while keeping all odds data) allowed completion within the 600s timeout.

### Multi-Agent A/B Testing

Every pick stores `agent_id` (e.g., `news_v1_injury_out`, `news_v2_aggressive`) and `news_source`, enabling future comparison between agent versions. Each `subprocess.run()` call to the Claude CLI spawns a fresh session with no memory between events — good for isolation but adds ~30s startup overhead per event.

The data model supports running multiple agent versions in parallel on the same news events, comparing which agent configurations produce the best CLV outcomes. Fields stored per pick:

- `triggered_by`: `{agent_id}` (no `news_` double-prefix after fix)
- `ai_reasoning`: The agent's textual explanation for each pick
- `ai_impact_chain`: How the news event cascades to specific market movements
- `news_event_id`: Foreign key to `news_agent_events` table for event → pick tracing

### Validation Methodology

The thesis is validated by measuring CLV on news-driven picks against the closing sharp line. If picks consistently show positive sharp CLV — meaning the sharp market moved toward the bettor's price after the bet was placed — the agent is genuinely beating sharps to news. This is the same CLV methodology documented in [[concepts/sharp-clv-theory-ranking]], but applied to news-driven picks specifically.

A negative validation would be picks with zero or negative CLV, meaning the market did not move as the agent predicted. This would indicate either (a) the news events were already priced in by sharps before the agent detected them, or (b) the agent's impact analysis is wrong about how news affects specific markets.

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The pipeline architecture that implements this thesis; the thesis was originally implicit and was made explicit on 2026-04-25
- [[concepts/sharp-clv-theory-ranking]] - CLV as the validation metric for whether news-driven picks genuinely beat sharps; same methodology applied to a different edge source
- [[concepts/value-betting-theory-system]] - Standard theories find current mispricings; news theories predict future mispricings — a fundamentally different time horizon
- [[concepts/twitter-x-api-scraping-constraints]] - Twitter rate limits bound the achievable speed for news ingestion, directly affecting the edge window size
- [[connections/sport-specific-news-intelligence-architecture]] - NBA vs MLB news sourcing requires different source strategies, affecting which news events the agent can detect early

## Sources

- [[daily/lcash/2026-04-25.md]] - Core thesis articulated: "we're beating sharps to news, not reacting to current EV"; EV validation gate removed — conviction-based picks validated by resolver over time; workspace architecture: full odds per game (~48KB, 764 lines) grouped by player; 90KB→48KB trimming fixed Sonnet timeout; Marcus Smart pick exemplifies thesis (-EV now, ahead of market); `agent_id` + `news_source` for multi-agent A/B testing; each subprocess.run spawns fresh session (~30s overhead) (Sessions 08:32, 09:08). Seven flaws identified and ranked: EV mismatch, hardcoded CLI path, fake freshness check, fragile output parsing; Claude Code WebSearch works for real-time sports news ($0.05 Haiku, $0.15-0.30 Sonnet) (Session 08:32). DuckDuckGo instant answer API returns Wikipedia abstracts not real-time news — useless for breaking sports news (Session 08:32)
