# Local tracker schema

Version 0.2 uses `tracker.csv` in the private workspace.

## Columns

- `id`: stable local identity; never use a physical row number as identity.
- `company`, `role`, `location`
- `source`, `canonical_url`, `external_job_id`
- `date_posted`, `date_discovered`, `last_verified`
- `status`, `fit_recommendation`, `priority`
- `next_action`, `next_action_date`
- `contact`, `human_path_status`, `recruiter`, `hiring_manager`, `interviewer`, `notes`

`human_path_status` is `confirmed`, `unverified` or `none_found`. Store a person as confirmed only when exact identity, current relevance and a direct source were verified in the private Human Path artifact.

`status` is process state. `fit_recommendation` is the latest `High`, `Medium`, `Low` or `Discard` evaluation. Reevaluation refreshes vacancy, fit, priority, next action and Human Path fields but does not regress an advanced process status such as `applied` or `interview`.

Store only directly sourced interviewer identities in `interviewer`. Keep unsourced names and hypotheses in the private research artifact, not as tracker facts.

## Statuses

`identified`, `evaluating`, `application_prepared`, `applied`, `contact`, `recruiter_screen`, `interview`, `offer`, `withdrawn`, `rejected`, `discarded`.

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
- Read back and verify identity, status and next action.
- Never report a write as successful solely because a command exited without error.
