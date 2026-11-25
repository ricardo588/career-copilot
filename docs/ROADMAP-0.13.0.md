# Career Copilot 0.13.0 — Private Relationship Evidence and Interview Readiness

Spanish version: [docs/es/ROADMAP-0.13.0.md](es/ROADMAP-0.13.0.md).

## Goal

Extend the existing private story-bank, interview-brief and debrief capabilities with guided STAR capture/confirmation and interview intake. The LinkedIn-export importer was explicitly deferred from this release because its private-filesystem concurrency boundary needs a separate design.

## Confirmed scope

1. **LinkedIn connections export to Human Path:** deferred; no connections-export input or Human Path artifact ships in `v0.13.0`. The pre-existing vacancy-export importer remains a separate, local vacancy-discovery feature and is not this initiative.
2. **STAR guided experience:** guide capture and explicit confirmation over the existing story bank; do not replace its schema, persist candidate data, or invent evidence.
3. **Interview intake:** collect confirmed interview logistics and evidence gaps before reusing the existing requirement matrix, interviewer research and brief generator.
4. **Debrief:** treat the existing read-only debrief as delivered; only add an optional, confirmable suggestion to improve a story when supported by the debrief facts.

## Non-negotiable boundaries

- No LinkedIn connections-export integration, API, scraping, browser, cookies, login, network request or process launch.
- No tracker, Sheets, Obsidian, calendar, email or message mutation.
- No fixture or documentation may contain a real connection export, contact, identifier or profile URL.

## Initial acceptance gates

- STAR and interview workflows preserve the existing distinction among facts, inference, unknowns and drafts.
- The full synthetic test suite, bundle validation, privacy scan, path-security regressions and an independent audit pass before release.
