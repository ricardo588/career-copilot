# Career Copilot 0.10.0 — Private Vacancy Discovery

Spanish version: [docs/es/ROADMAP-0.10.0.md](es/ROADMAP-0.10.0.md).

## Scope

v0.10.0 extends strategic onboarding with two private, deterministic capabilities:

1. Portal coverage suggestions use the candidate's declared role family, seniority, industry, eligible geography, work mode and employment type.
2. An explicit local JSON vacancy export can produce a private, read-only shortlist.

## Delivered behavior

1. **Candidate-controlled recommendations:** onboarding asks optional industry and employment-type questions. `status` returns editable `portal_recommendations`, each with an ID, name and reason.
2. **Coverage, not a ranking:** the catalog includes baseline professional and official-source coverage plus conditional suggestions for Mexico, technology, creative roles or industries, remote work, contract or freelance work, and senior roles in the United States. These are local heuristics, not claims about live availability, portal quality or market performance.
3. **Explicit private import:** `vacancy_discovery.py` reads only the supplied local JSON export. It validates the selected source, freshness, canonical HTTP(S) URL and duplicate canonical URLs.
4. **Traceable context:** every private shortlist preserves the declared role, seniority, industry, geography, work-mode and employment-type context without silently declaring a vacancy a match.
5. **Safe handoff:** a shortlist is not a tracker write, verified vacancy, application authorization or external-action authorization. Every retained entry requires canonical-source verification before later evaluation or tracking.

## Safety boundaries

- v0.10.0 does not query LinkedIn, OCC, any other portal, company career site or ATS.
- No credential, browser session, scraping, API call, contact, application, public-profile edit or external request is introduced.
- Imports require an explicitly chosen private local file; reports must be outside Git repositories and are written with private permissions.
- Candidate-entered targets, selected portals and shortlist reports remain in the private workspace; repository tests use synthetic fixtures only.
- `draft_only`, `confirm_each_external`, evidence, privacy and tracker safeguards remain unchanged.

## Upgrade

No private-data migration is required. Existing profiles already support `target_industries` and `employment_types`; resumed onboarding now offers optional questions for those fields. Existing selected portals and target companies remain unchanged.

## Required manual pre-release verification

Before publishing, run the full unit suite, bundle validation, privacy scan, Git diff checks, the synthetic demo with zero external actions, and a disposable Hermes-profile installation. CI runs bundle validation and unit tests; the remaining checks are deliberate local release steps.

## Deferred

- Direct portal, ATS or company-site acquisition adapters.
- CSV import support and source-specific export normalizers.
- Current, source-dated market-coverage evidence beyond the local catalog.
- Automatic tracker writes, applications, messages, contacts or other external actions.
