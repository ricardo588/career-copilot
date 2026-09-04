# Career Copilot 0.7 — Operational Tracker design brief

## Status

**Approved scope:** tracker reconciliation and compensation policy.

This is a design and delivery plan, not an implementation promise. Version 0.7 must preserve Career Copilot's privacy-first boundary and its default `draft_only` external-action policy.

## Goal

Make the optional Google Sheets tracker integration safe enough for a live job-search workflow without embedding a candidate's data, credentials, exact tracker schema, or personal policies in the distribution.

The release adds deterministic reconciliation between a supplied tracker record and a configured Google Sheets backend, plus an executable compensation policy. It does **not** automate applications, messages, recruiter outreach, or scheduled external work.

## Non-goals

- No application submission, message sending, recruiter contact, public-profile action, or job-board login.
- No installed recurring jobs; future scheduling remains explicit opt-in.
- No hard-coded salary figures, target companies, status names, employer names, Sheet IDs, contacts, or candidate data.
- No mandatory Google account or Google Sheets setup for users who keep the local CSV tracker.
- No multi-surface transaction with Obsidian/Kanban in 0.7. Those integrations are candidates for a later release after the Sheet contract is proven.

## Accepted product decisions

1. **Backend:** Google Sheets is an optional first operational backend. The existing local CSV tracker remains supported.
2. **Scope:** v0.7 is tracker reconciliation plus compensation policy. Inbox orchestration, Obsidian/Kanban reconciliation, and scheduled jobs are deferred.
3. **Configuration:** statuses, priorities, business-ID requirements, networking phase gates, and compensation values are private profile/rules data, never distribution defaults tied to one candidate.
4. **Safety:** `draft_only` remains the default. Google writes require `confirm_each_external`, a concrete reviewed plan, and exact readback verification.
5. **Release process:** release as `0.7.0`, with an upgrade guide and a disposable-profile verification path.

## Architecture

### 1. Pure reconciliation core

Add a deterministic module with no network, `gws`, credentials, or filesystem mutation. It accepts:

- a normalized sheet snapshot: headers, rows, physical row numbers;
- configured schema mapping;
- an intended candidate record and requested operation;
- optional canonical identity fields: `external_job_id`, `canonical_url`, `company`, `role`.

It returns exactly one of:

- `create_plan`;
- `update_plan`;
- `duplicate_match`;
- `ambiguous_identity`;
- `integrity_failure`;
- `no_change`.

The core must resolve identity in this order:

1. exact external job/requisition ID;
2. canonical URL after removal of tracking parameters;
3. normalized company plus near-identical role, requiring human review before a merge.

It must never use a physical Sheet row as the record's business identity.

### 2. Sheet schema adapter

Add a private configuration mapping, for example:

```yaml
tracker:
  backend: google_sheets
  canonical_source: sheet
  sheet:
    spreadsheet_id_env: CAREER_COPILOT_SHEET_ID
    worksheet: Applications
    header_range: Applications!A1:Z1
    data_range: Applications!A2:Z
  fields:
    business_id: No
    company: Company
    role: Role
    status: Status
    priority: Priority
    canonical_url: Canonical URL
    external_job_id: External Job ID
    notes: Notes
  integrity:
    require_contiguous_business_ids: false
    reject_duplicate_business_ids: true
```

The configuration belongs in the user-owned workspace or profile. A repository template may contain only generic placeholder names.

The adapter flow is:

1. read the configured header and active data range;
2. normalize the snapshot and audit identity/integrity;
3. call the pure reconciliation core;
4. render an exact dry-run plan: target rows, fields, old values, new values, and unresolved risks;
5. require explicit confirmation for an external write;
6. write the smallest explicit range(s);
7. read back every changed range;
8. record minimal private audit events; report failure if any readback differs.

### 3. Business-ID integrity

When a profile enables contiguous business IDs, the core must report:

- record count and maximum business ID;
- missing IDs;
- duplicate IDs;
- rows adjacent to anomalies;
- whether the requested change is safe, ambiguous, or blocked.

A missing or duplicate ID is never permission to renumber the sheet. Recovery requires independently corroborated evidence and an explicit reviewed repair plan. v0.7 may detect and block on anomalies; automated reconstruction of displaced records is deliberately deferred until fixtures and a recovery contract exist.

### 4. Compensation policy

Extend private profile/rules data with structured policy values:

```yaml
compensation:
  enabled: true
  policies:
    - employment_type: payroll
      currency: MXN
      periodicity: monthly
      target_base: null
      floor_base: null
    - employment_type: contractor
      currency: USD
      periodicity: hourly
      target_base: null
      floor_base: null
  below_floor_terminal_status: withdrawn
  below_floor_reason: budget_below_floor
```

The evaluator must return one explicit state:

- `not_configured`;
- `unknown` (no disclosed compatible figure);
- `compatible`;
- `below_floor`;
- `exception_required`.

Rules:

- Base compensation and total package are distinct fields.
- An undisclosed amount is `unknown`, never automatically compatible or incompatible.
- A `below_floor` outcome can propose the configured withdrawal/discard action, but does not write it without tracker permission and verification.
- Employer rejection and candidate withdrawal remain distinct terminal reasons.
- Currency conversion is out of scope unless an explicit, dated exchange-rate source contract is added later.

### 5. Configurable state and priority policy

Do not hard-code a candidate-specific pipeline. Add optional private configuration for:

- allowed status values;
- terminal states and reasons;
- valid state transitions;
- whether `High` priority requires a verified trusted company contact;
- optional phase at which networking recommendations may begin.

Default templates remain generic and conservative. A profile with no custom state policy retains existing Career Copilot statuses.

## Proposed file-level delivery plan

### Milestone A — contract and pure core

- `skills/career-copilot/scripts/tracker_reconciliation.py` — pure normalization, identity resolution, integrity audit, and plan generation.
- `skills/career-copilot/references/google-sheets-tracker-backend.md` — configuration and safety contract.
- `skills/career-copilot/templates/tracker-backend.template.yaml` — empty generic schema mapping.
- `tests/test_tracker_reconciliation.py` — fixtures and deterministic tests.

**Exit criteria:** core has no `gws` dependency; all decisions are reproducible from supplied data; ambiguity fails closed.

### Milestone B — gated Sheets integration

- Extend `scripts/adapters.py` or add a focused `scripts/tracker_backend.py` command.
- Reuse existing `confirm_each_external`, private audit logging, scoped writes, and readback verification.
- Add a `reconcile` dry-run command and a separately gated `apply` path.
- Add fake-runner tests for changed ranges, readback mismatch, bad headers, and blocked policies.

**Exit criteria:** a write cannot run under `draft_only`; every successful write returns an exact verified readback; no full-sheet rewrite is performed.

### Milestone C — compensation policy

- Extend `templates/candidate-profile.template.yaml` and onboarding validation.
- Add deterministic compensation evaluation to `pipeline.py`.
- Add explicit compensation fields/reason to tracker schema only through a versioned migration plan.
- Add test fixtures for payroll, contractor, unknown amount, below floor, and exception-required outcomes.

**Exit criteria:** the evaluator cannot silently treat unknown compensation as a match and cannot conflate a budget withdrawal with an employer rejection.

### Milestone D — documentation, migration, and release verification

- Update English and Spanish README, quickstart, privacy, adapters, and tracker-schema documentation.
- Add a migration guide from local CSV-only profiles and from existing Sheets.
- Add a synthetic end-to-end reconciliation demo with no account credentials.
- Run bundle validation, full unit suite, synthetic demo, and a disposable Hermes profile installation.

**Exit criteria:** repository stays free of private data; a new user can understand that Google Sheets is optional; an existing user can adopt the new backend without silent mutation.

## Required synthetic fixtures

Tests must include, at minimum:

1. exact external-job-ID duplicate;
2. canonical URL duplicate with tracking parameters removed;
3. same company/near-identical role requiring human review;
4. missing business ID;
5. duplicate business ID;
6. a physical-row shift while business identity remains intact;
7. blank or unknown columns;
8. unsupported extra columns;
9. readback mismatch after a narrowly scoped write;
10. attempted mutation in `draft_only`;
11. payroll amount below floor;
12. contractor rate below floor;
13. undisclosed compensation;
14. candidate-approved exception.

No fixture may use actual candidate, company, contact, tracker, compensation, Gmail, or spreadsheet data.

## Security and privacy acceptance criteria

- Credentials, Sheet IDs, vault paths, candidate details, messages, and spreadsheet rows remain outside the repository.
- Every Google mutation needs a private profile, private workspace, explicit apply intent, and readback verification.
- `draft_only` blocks every external write even when an apply flag is present.
- Audit records store minimal target references and plan hashes, not full messages or spreadsheet contents.
- All generated candidate artifacts retain private file permissions and must be rejected beneath Git/distribution directories.

## Deferred roadmap

### v0.8 candidates

- Transactional Gmail inbox triage: evidence → identity resolution → reconciliation → verified mark-read.
- Optional Obsidian/Kanban projection after a proven tracker update contract.
- Idempotent processed-message ledger.

### v0.9 candidates

- Explicit opt-in schedules/blueprints for search, triage, and weekly review.
- Source-plan policy (official ATS, recruiter firms, boards, validation source rules).
- Expanded interview dossier rendering, including optional mobile-first PDF output.

## Delivery governance

- Implement in a dedicated branch with small, reviewable commits.
- Keep implementation tasks separate from candidate-data operation.
- Test every write path with fake runners before an account-backed smoke test.
- Any live smoke test uses a disposable/private test sheet, never a candidate's production tracker.
- Publish only after a clean privacy scan, bundle validation, full test suite, synthetic demo, and isolated-profile installation verification.
