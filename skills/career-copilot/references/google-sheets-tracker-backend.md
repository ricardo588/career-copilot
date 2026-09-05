# Google Sheets tracker reconciliation backend

Version 0.7 introduces a **pure planning core** at
`scripts/tracker_reconciliation.py`. It does not access Google, the filesystem,
or credentials. It turns a supplied tabular snapshot into a safe, deterministic
reconciliation decision.

`scripts/adapters.py sheets-reconcile` is the read-only B1 integration. It
reads one explicit A1 range, turns it into a snapshot, and returns the core plan.
It has no `--apply` option and cannot write a candidate tracker itself.

## Private configuration

Copy `templates/tracker-backend.template.yaml` into a candidate-owned workspace
and replace only the header mapping with that person's private Sheet schema.
Never commit spreadsheet IDs, worksheet names, values, credentials, candidate
records, or contact data.

The current template uses `spreadsheet_id_env`, so the secret identifier remains
in a local environment variable rather than a tracked configuration file.

## Snapshot contract

The planner consumes a mapping of this form:

```json
{
  "headers": ["No", "Company", "Role", "Canonical URL", "External Job ID"],
  "rows": [
    {
      "physical_row": 2,
      "values": {
        "No": "1",
        "Company": "Synthetic Example",
        "Role": "Program Director",
        "Canonical URL": "https://jobs.example.test/1",
        "External Job ID": "SYN-1"
      }
    }
  ]
}
```

`physical_row` is a Sheet location, not the tracker identity. The planner
resolves a record by exact external ID, then canonical URL, then a conservative
company-plus-near-identical-role heuristic that always requires human review.

Every header named by `fields` must exist exactly once. Extra Sheet columns are
allowed and preserved; a missing or duplicate mapped header fails closed.

## Decisions

The planner returns one `decision`:

- `create_plan` — a new record may be written to the explicitly supplied target
  physical row.
- `update_plan` — one existing stable record was resolved and only listed fields
  differ.
- `duplicate_match` — a create request already matches a stable existing record.
- `ambiguous_identity` — stable identities conflict or a near-role match needs
  human review.
- `integrity_failure` — the snapshot or requested plan is unsafe.
- `no_change` — no writable difference exists, or an update did not resolve a
  stable record.

The result includes `audit`, which reports business-ID health. It never
renumbers rows or silently repairs anomalies.

## Business-ID safety

When `business_id` is mapped, the audit reports maximum ID, missing IDs,
duplicates, invalid values, and their physical rows. The backend must supply only
candidate record rows; if a supplied record row has a blank business ID, it is an
invalid value and blocks planning. If duplicate IDs are rejected or contiguity is
enabled, an anomaly produces `integrity_failure` before identity matching or
planning.

A missing ID or duplicate is evidence of a problem, not permission to renumber.
Any repair must use independently corroborated evidence and a reviewed plan.

## Create safety

The planner deliberately refuses to guess an append position. A caller must
supply `create_physical_row` after determining an exact safe target. When a
business-ID field is mapped, an explicit intended business ID is also required.

## B2 Sheets write contract

`scripts/adapters.py sheets-reconcile-apply` is the gated B2 path. Its default
is still a dry run: it reads the explicit closed A1 snapshot range, runs the
planner, renders target cells with the underlying old/new changes, and returns
an `approval_sha256`.

An actual write requires all of the following:

1. exact repeat of the reviewed request plus `--apply`;
2. the dry-run `--approved-plan-sha256` in lowercase SHA-256 form;
3. a private profile whose `external_action_mode` is
   `confirm_each_external`;
4. a private non-repository workspace for audit logging;
5. a closed A1 rectangle with a worksheet name, beginning at the header row.

The apply invocation reads live data again and computes a fresh plan. It blocks
before a mutation if that plan's hash differs from the reviewed hash. For an
accepted current plan it writes only the changed individual cells, reads back
every written cell, and fails on a mismatch. It records append-only minimal
private audit lifecycle events (`attempted`, `applied`, `verified`, or
`blocked`/`failed`) using a plan hash rather than tracker content.

The approval hash is domain-separated and binds the private exact spreadsheet
ID plus the redacted write plan; the ID is never returned in output or placed in
the plan. A matching `no_change` plan returns a verified no-op before policy or
audit work because it performs no external mutation.

The minimal Sheets endpoint used here has no cross-cell transaction. If a later
narrow write fails, earlier completed cells can remain changed; each completed
cell is therefore audited as `applied` before the command reports failure. Do
not treat a failed invocation as an automatic rollback.

The B2 path cannot append speculatively, rewrite an entire row/sheet, renumber
business IDs, submit applications, or send outreach. `draft_only` blocks the
write even when an apply flag is present.
