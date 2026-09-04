# Tracker compensation migration plan

The current local tracker schema is version 0.3 and intentionally has no
compensation columns. Compensation evaluation is available in the pipeline but
remains non-mutating until this migration is explicitly adopted.

## Proposed version 0.4 columns

A future migration may add these optional columns after the existing tracker
contract has been backed up and validated:

- `compensation_state`
- `compensation_reason`
- `compensation_base`
- `compensation_currency`
- `compensation_employment_type`
- `compensation_periodicity`
- `compensation_last_verified`

`total` is deliberately excluded: it is private context, not a substitute for
base compensation. Candidate-approved exception details also stay outside the
tracker unless an explicit private retention rule is added.

## Required migration contract

1. Detect exactly the supported 0.3 header; reject unknown extra-column schemas.
2. Create a private backup before changing bytes.
3. Append columns only; preserve stable IDs, all existing rows, process status,
   Human Path fields, and independent freshness clocks.
4. Initialize every new cell blank; no current or historical vacancy is inferred
   to have a compensation result.
5. Atomically write the new 0.4 header and rows, then read back the exact header
   and row count.
6. A later tracker update can persist a compensation result only with tracker
   permission, a reviewed minimal diff, and readback verification.
7. A `below_floor` proposal must use the candidate terminal reason configured in
   the private profile. It must never use `rejected` or imply employer action.

No automated tracker migration is included in v0.7 Milestone C. This document
is the versioned gate for implementing one safely in release hardening.
