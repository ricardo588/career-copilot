# Google Sheets tracker reconciliation backend

Version 0.7 introduces a **pure planning core** at
`scripts/tracker_reconciliation.py`. It does not access Google, the filesystem,
or credentials. It turns a supplied tabular snapshot into a safe, deterministic
reconciliation decision.

The Google Sheets execution adapter is a later milestone. Until that exists,
this core must be used only to inspect a snapshot and produce a plan; it cannot
write a candidate tracker itself.

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

## Future Sheets adapter contract

The future Google adapter must:

1. read header and data snapshot;
2. run the planner in dry-run mode;
3. present exact target rows plus old/new values;
4. require `confirm_each_external` and explicit apply intent;
5. write only the approved ranges;
6. read back each changed range;
7. fail if readback differs;
8. record only a minimal private audit event.

`draft_only` must block the write even when an apply flag is present. Sending,
recruiter outreach, and applications are outside this backend's scope.
