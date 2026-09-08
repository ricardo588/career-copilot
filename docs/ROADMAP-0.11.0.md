# Career Copilot 0.11.0 — Integrated Safe Acquisition Scope

Spanish version: [docs/es/ROADMAP-0.11.0.md](es/ROADMAP-0.11.0.md).

## Status

**Release target:** v0.11.0 integrates the deferred discovery, source-format, evidence-refresh and action-planning scope while preserving private ownership and explicit authorization. It becomes a published release only after the release tag is created.

## Delivered behavior

1. **Direct read-only acquisition:** an operator can invoke exactly one public Greenhouse Job Board or Lever Postings `GET` using a candidate-confirmed board/site identifier. No credentials, search, browser automation, scraping, application endpoint or mutation exists in this path.
2. **Source-specific normalizers:** documented Greenhouse and Lever JSON fields normalize to the existing private-vacancy contract. Greenhouse `updated_at` is preserved as `source_updated_on`, not asserted as a posting date; shortlist freshness labels that basis explicitly. The report remains subject to the selected-source, freshness and canonical-identity checks before shortlisting.
3. **Refreshable evidence governance:** `onboarding.py catalog-audit` checks local catalog URL/date/scope metadata against an explicit review date and reports entries due for a human re-check. It makes no network request.
4. **External-action scope:** deterministic application, message, contact and tracker-write plans are always drafts. Their approval hash binds target and payload, but they cannot execute. Existing Sheets/Obsidian executors retain their separate `confirm_each_external`, current-read and readback contracts.
5. **Target-company research:** the existing private registry remains the evidence-backed target-company route; candidate preference, current signals, Human Path freshness and contact authorization stay separate.

## Safety boundaries

- Direct acquisition is only an explicit public read initiated through the CLI. It does not run during onboarding, status, catalog audit, import, evaluation or demo.
- No code submits applications, sends messages, contacts people, modifies public profiles, or performs a tracker write through this scope.
- The product never places credentials, board/site identifiers, URLs selected by a candidate, acquisition reports or private action plans in the distribution repository.
- A catalog audit identifies stale evidence; it never treats an old source as a current availability claim.

## Upgrade

No private-data migration is required. Existing CSV/JSON imports, onboarding checkpoints and output consumers remain compatible. The new `evidence_checked_on` catalog field is additive. The direct acquisition report uses the same `vacancies` payload shape as the existing import path.

## Verification

Run focused acquisition/onboarding tests, the full suite, bundle and privacy validation, diff checks and the synthetic demo. The demo injects an in-memory Greenhouse response and reports `network_executed: false`; it does not contact a provider.

## Remaining extension rule

Adding another provider requires a separately verified public contract, fixture-backed normalizer, source URL allowlist, paired EN/ES documentation and the same explicit-read/no-mutation boundary. Adding an executor for any action requires a provider-specific authorization, current target read, exact approval hash, private audit and verified readback; it cannot be inferred from a plan.
