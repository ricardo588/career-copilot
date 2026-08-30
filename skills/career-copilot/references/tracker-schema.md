# Local tracker schema

Version 0.3 uses `tracker.csv` in the private workspace.

## Columns

- `id`: stable local identity; never use a physical row number as identity.
- `company`, `role`, `location`
- `source`, `canonical_url`, `external_job_id`
- `date_posted`, `date_discovered`
- `vacancy_last_verified`: date of the explicit vacancy evaluation/refresh.
- `human_path_last_verified`: validated `retrieved_at` from the most recently supplied Human Path artifact.
- `status`, `fit_recommendation`, `priority`
- `next_action`, `next_action_date`
- `contact`, `human_path_status`, `recruiter`, `hiring_manager`, `interviewer`, `notes`

## Independent freshness clocks

Vacancy and Human Path freshness describe different evidence and must not share a timestamp.

- Every explicit vacancy evaluation updates `vacancy_last_verified` from `--as-of`.
- Human Path fields and `human_path_last_verified` change only when `--human-path` supplies a mapping with a valid, non-future `retrieved_at` date.
- A vacancy-only refresh preserves `contact`, `human_path_status`, `recruiter`, `hiring_manager`, `interviewer` and `human_path_last_verified`.
- Interviewer evidence changes only when an explicit interviewer-research artifact is supplied.
- Interviewer research is a separate artifact: an interviewer-only update does not advance `human_path_last_verified`.
- A new row without Human Path evidence leaves Human Path fields and freshness blank. Absence of an artifact is not `none_found`.
- An explicit Human Path artifact containing no confirmed or plausible people may record `none_found` and its validated retrieval date.

`human_path_status` is `confirmed`, `unverified` or `none_found`; blank means no Human Path artifact has been supplied for that row. Store a person as confirmed only when exact identity, current relevance and a direct source were verified in the private Human Path artifact.

Store only directly sourced interviewer identities in `interviewer`. Keep unsourced names and hypotheses in the private research artifact, not as tracker facts.

## Legacy migration

Version 0.2 had one ambiguous `last_verified` column. On the first tracker write with the 0.3 pipeline:

1. `last_verified` migrates to `vacancy_last_verified`.
2. `human_path_last_verified` remains blank; migration must not fabricate a Human Path verification date.
3. Stable IDs, rows, process status, next action and existing Human Path values are preserved.
4. The file is rewritten atomically with the 0.3 header before the requested refresh is applied.
5. A current-schema header with reordered columns is normalized safely; unsupported extra columns are rejected rather than discarded.

## Statuses

`identified`, `evaluating`, `application_prepared`, `applied`, `contact`, `recruiter_screen`, `interview`, `offer`, `withdrawn`, `rejected`, `discarded`.

`status` is process state. `fit_recommendation` is the latest `High`, `Medium`, `Low` or `Discard` evaluation. Reevaluation refreshes vacancy and fit fields but does not regress an advanced process status such as `applied` or `interview`.

## Read-only follow-up review

Run `scripts/pipeline.py --review-tracker <csv> --as-of <YYYY-MM-DD>` to derive follow-up signals without adding a persisted column.

- `follow_up_overdue` is true only when `next_action` is present, `next_action_date` is before `as_of`, and `status` is not `withdrawn`, `rejected` or `discarded`.
- A date equal to `as_of` is not overdue.
- Missing dates are `unknown`; malformed dates are `invalid`.
- The signal is neutral: it does not infer lack of response or change `status`, `next_action`, rows, headers or file metadata.
- `applied`, `contact`, `recruiter_screen` and `interview` remain confirmed process states.
- The input file must exist and have exactly the current header (in any order) or the supported legacy 0.2 header. Missing files and unknown/extra-column schemas fail closed without rewriting bytes.

The command emits one JSON object with:

- `read_only: true` and the explicit `as_of` date;
- `summary` with `rows`, `follow_up_overdue`, `unknown_dates` and `invalid_dates` counts;
- `items`, one per tracker row, preserving `id`, `company`, `role`, `status`, `next_action` and `next_action_date`;
- per-item `follow_up_overdue`, `next_action_date_state` (`valid`, `unknown` or `invalid`) and neutral `reason`.

## Dedupe

1. Exact external job ID.
2. Canonical URL after removing tracking parameters.
3. Normalized company plus near-identical role, followed by human review.

A repost is not automatically a new opportunity. Compare source ID, scope, location and current status before reopening or creating a record.

## Writes

- Snapshot the file before bulk repair.
- Locate records by stable ID and corroborating company/role.
- Update the smallest affected set.
- Write atomically where possible.
- Read back and verify identity, status, next action and every field intended to change.
- Never report a write as successful solely because a command exited without error.
