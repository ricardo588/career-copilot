# Career Copilot 0.9.1 — Strategic Onboarding

Spanish version: [docs/es/ROADMAP-0.9.1.md](es/ROADMAP-0.9.1.md).

## Status

**Delivered:** v0.9.1 adds a private, resumable search-strategy phase to onboarding. It captures optional target companies and presents transparent job-portal coverage suggestions after declared roles and eligible geography are available.

## Delivered behavior

1. **Candidate-controlled targets:** `search.target_companies` stores a candidate-provided list in the private onboarding checkpoint and finalized private rules.
2. **Candidate-controlled portals:** `search.selected_job_portals` stores the candidate's chosen portal identifiers. The candidate may amend, add alternatives, or leave the list empty.
3. **Transparent suggestions:** `status` returns `portal_recommendations` with a portal ID, name and reason. The initial catalog covers LinkedIn and official company career sites, Mexico-focused coverage, and technology-role additions where applicable.
4. **Conservative upgrade:** existing checkpoints receive empty target-company and portal lists when resumed. No candidate data migration, tracker mutation or external request occurs.

## Safety boundaries

- Suggestions are local coverage heuristics derived only from declared roles and eligible geography. They are not a live market-performance ranking.
- A target-company name is candidate intent, not evidence of hiring, a verified company fact, or authorization to research or contact anyone.
- A selected portal is a private preference. v0.9.1 does not query portals, retrieve vacancies, submit applications, edit public profiles, contact people, or perform any external action.
- Existing `draft_only`, `confirm_each_external`, evidence, privacy and readback safeguards remain unchanged.

## Upgrade

No private-data migration is required. Resume onboarding normally; legacy checkpoints obtain empty `search.target_companies` and `search.selected_job_portals` lists. Existing profiles, rules and trackers remain compatible until onboarding is finalized again.

## Required manual pre-release verification

Before publishing, run the full unit suite, bundle validation, privacy scan, Git diff checks, the synthetic demo with zero external actions, and a disposable Hermes-profile installation. CI currently runs bundle validation and unit tests; the remaining checks are deliberate local release steps.

## Deferred

- Read-only vacancy discovery from user-selected portals.
- Source-dated, refreshable market-coverage evidence for regions beyond the initial catalog.
- Conversion of a target-company preference into an evidence-backed target-company research record.
- Any application, communication, public-profile or other external action.
