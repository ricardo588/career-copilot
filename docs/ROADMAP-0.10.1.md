# Career Copilot 0.10.1 — Portal Catalog Evidence

Spanish version: [docs/es/ROADMAP-0.10.1.md](es/ROADMAP-0.10.1.md).

## Status

**Delivered:** v0.10.1 adds a dated, source-linked evidence contract to each portal-coverage suggestion from onboarding.

## Delivered behavior

1. **Versioned suggestions:** every `portal_recommendations` entry includes `catalog_version` and `evidence_checked_on`, both set to catalog version `2026-09-07`.
2. **Narrow evidence:** every entry includes an HTTPS `evidence_url` and `evidence_scope`. The scope describes only its supported coverage category and explicitly rejects a market ranking.
3. **Complete local catalog:** the 11 currently suggested entries are documented with official-source links in [the portal catalog](../skills/career-copilot/references/portal-catalog.md), together with a Spanish counterpart and a maintenance rule.
4. **Safe baseline:** official company career sites and ATS remain a product safety recommendation for canonical-source verification, rather than a claim of market coverage.

## Safety boundaries

- v0.10.1 does not open, query, scrape, authenticate to, apply through, or otherwise act on LinkedIn, OCC, any other portal, company career site or ATS.
- The catalog does not claim real-time availability, volume, conversion, portal quality, candidate suitability, eligibility or ranking.
- Candidate-selected portals remain private workspace preferences. The evidence catalog contains public source URLs and no candidate data.
- `draft_only`, `confirm_each_external`, tracker, privacy and read-only vacancy-import safeguards remain unchanged.

## Upgrade

No private-data migration is required. Existing onboarding checkpoints and finalized profiles remain compatible because portal suggestions are derived status output. Clients that consume recommendation objects should preserve the new evidence fields.

## Required manual pre-release verification

Before publishing, run the full unit suite, bundle validation, privacy scan, Git diff checks, citation validation for both catalog references, the synthetic demo with zero external actions, and a disposable Hermes-profile installation. CI runs bundle validation and unit tests; the remaining checks are deliberate local release steps.

## Deferred

- Direct portal, ATS or company-site acquisition adapters.
- Source-specific export normalizers beyond the documented generic CSV contract.
- Broader, refreshed source-dated market-coverage evidence beyond this initial catalog.
- Automatic tracker writes, applications, messages, contacts or other external actions.
