# Build Log

## [2026-04-10T12:30:18+10:00] compile | daily/lcash/2026-04-10.md
- Source: daily/lcash/2026-04-10.md
- Developer: lcash
- Articles created: [[concepts/team-knowledge-base-architecture]], [[concepts/claude-code-hook-reliability]], [[concepts/stop-hook-periodic-capture]], [[concepts/setup-kb-skill]], [[concepts/local-compilation-strategy]], [[connections/hook-reliability-and-capture-architecture]]
- Articles updated: (none)

## [2026-04-12T20:15:29+10:00] compile | daily/carts00/2026-04-10.md
- Source: daily/carts00/2026-04-10.md
- Developer: carts00
- Articles created: [[concepts/claude-code-skills-directory]], [[concepts/parlay-ev-calculation]], [[concepts/cumulative-vs-filtered-display-pattern]], [[connections/onboarding-friction-real-world-validation]]
- Articles updated: [[concepts/setup-kb-skill]] (added carts00's real-world onboarding experience and friction points)

## [2026-04-12T20:18:49+10:00] compile | daily/lcash/2026-04-10.md (incremental)
- Source: daily/lcash/2026-04-10.md
- Developer: lcash
- Note: Incremental recompile — Test Session (12:30) was already compiled on 2026-04-10; this pass covers Session (14:10) content
- Articles created: [[concepts/project-context-tagging]]
- Articles updated: [[concepts/team-knowledge-base-architecture]] (added project context tagging as a feature)

## [2026-04-12T21:45:00+10:00] compile | daily/lcash/2026-04-11.md
- Source: daily/lcash/2026-04-11.md
- Developer: lcash
- Articles created: [[concepts/bet365-racing-data-protocol]], [[concepts/spa-navigation-state-api-access]], [[concepts/cdp-browser-data-interception]], [[concepts/bet365-racing-adapter-architecture]], [[concepts/browser-mediated-websocket-streaming]], [[connections/anti-scraping-driven-architecture]]
- Articles updated: (none)

## [2026-04-12T22:30:00+10:00] compile | daily/lcash/2026-04-12.md
- Source: daily/lcash/2026-04-12.md
- Developer: lcash
- Articles created: [[concepts/playwright-evaluate-uncancellable]], [[concepts/async-global-timeout-partial-results]], [[concepts/opticodds-critical-dependency]], [[connections/browser-automation-reliability-cost]]
- Articles updated: [[concepts/bet365-racing-adapter-architecture]] (added venue scanning reliability section: Toowoomba hang, global timeout pattern, stale session issues)

## [2026-04-12T23:45:00+10:00] compile | daily/lcash/2026-04-12.md (incremental)
- Source: daily/lcash/2026-04-12.md
- Developer: lcash
- Note: Incremental recompile — Sessions 15:37 and 20:15 were already compiled; this pass covers Session 21:15 content (betstamp removal, batch file drift)
- Articles created: [[concepts/betstamp-bet365-scraper-migration]], [[concepts/configuration-drift-manual-launch]], [[connections/scraper-consolidation-provider-dependency]]
- Articles updated: [[concepts/opticodds-critical-dependency]] (added betstamp removal deepening dependency analysis)

## [2026-04-13T00:15:00+10:00] compile | daily/lcash/2026-04-12.md (incremental)
- Source: daily/lcash/2026-04-12.md
- Developer: lcash
- Note: Incremental recompile — Sessions 15:37, 20:15, 21:15 were already compiled; this pass covers Session 21:51 content (silent auth failures, full system assessment) and remaining 21:15 detail
- Articles created: [[concepts/silent-worker-authentication-failure]], [[concepts/value-betting-operational-assessment]], [[connections/operational-compound-failures]]
- Articles updated: [[concepts/configuration-drift-manual-launch]] (added second drift layer: API keys missing from batch file, .env not loaded, two-phase debugging)

## [2026-04-15T22:03:56+10:00] compile | daily/lcash/2026-04-13.md
- Source: daily/lcash/2026-04-13.md
- Developer: lcash
- Articles created: [[concepts/value-betting-theory-system]], [[concepts/worker-status-observability]], [[concepts/self-evolving-operational-skill]], [[connections/push-latency-trail-quality-cascade]]
- Articles updated: [[concepts/bet365-racing-adapter-architecture]] (added discovery endpoint migration, end-to-end pipeline with constructor injection, first live price moves), [[concepts/bet365-racing-data-protocol]] (added binary framing section with control characters \x14/\x15/\x16/\x08/\x01), [[connections/browser-automation-reliability-cost]] (added browser scraper warmup latency: hours to recover after restart), [[connections/anti-scraping-driven-architecture]] (added 5th defense layer: cross-origin WS failure and closure-hidden instances forcing constructor injection)
- Note: 5 articles already existed from a prior partial compilation of this log (alt-line-mismatch-poisoned-picks, server-side-snapshot-cache, trail-data-temporal-resolution, fixture-name-canonicalization, websocket-constructor-injection) — added to index in this pass

## [2026-04-15T23:30:00+10:00] compile | daily/lcash/2026-04-14.md
- Source: daily/lcash/2026-04-14.md
- Developer: lcash
- Articles created: [[concepts/bet365-splash-timing-dependency]], [[concepts/bet365-websocket-cluster-topology]], [[concepts/bet365-mlb-lazy-subscribe-migration]], [[concepts/afl-circular-devig-trap]], [[concepts/one-sided-consensus-structural-bias]], [[concepts/pick-dedup-multi-theory-limitation]], [[connections/circular-devig-provider-dependency]]
- Articles updated: [[concepts/bet365-racing-adapter-architecture]] (added splash timing dependency, WS cluster selection, supervisor retry logic, new limitations), [[concepts/value-betting-theory-system]] (added theory proliferation audit, one_sided_consensus discovery, theory_evs column plan), [[connections/anti-scraping-driven-architecture]] (added VPS Cloudflare IP reputation evidence from DigitalOcean testing, raw-WS-as-ideal-path note), [[concepts/bet365-racing-data-protocol]] (added WS cluster topology section, in-band auth format, cluster data roles)

## [2026-04-16T00:15:00+10:00] compile | daily/lcash/2026-04-15.md
- Source: daily/lcash/2026-04-15.md
- Developer: lcash
- Articles created: [[concepts/bet365-ws-topic-authorization]], [[concepts/bet365-headless-detection]], [[concepts/odds-staleness-pipeline-diagnosis]], [[concepts/dashboard-client-server-ev-divergence]], [[connections/ws-viability-sport-rendering-divergence]]
- Articles updated: [[concepts/bet365-racing-adapter-architecture]] (added Dell server deployment section: headless detection, racecoupon HTTP runner map, Windows issues), [[concepts/value-betting-theory-system]] (added loadTheories() bug fix deployed, client-server EV divergence link), [[connections/anti-scraping-driven-architecture]] (added headless detection as 6th defense layer, WS topic authorization as streaming constraint)
