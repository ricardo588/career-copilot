# Explicit public acquisition and action drafts

## Boundary

`vacancy_acquisition.py` supports only two explicit, public, GET-only ATS feeds:

- `greenhouse_public_board` — `https://boards-api.greenhouse.io/v1/boards/<board-token>/jobs`
- `lever_public_postings` — `https://api.lever.co/v0/postings/<site>?mode=json`

The candidate or operator supplies the board/site identifier and company label for one request. Identifiers accept only letters, digits, `_` and `-`; Career Copilot never discovers identifiers, searches across companies, authenticates, uses browser automation, scrapes rendered pages, follows application URLs, or submits an application.

Both normalizers emit the documented private-import shape (`source`, `company`, `role`, `location`, `canonical_url`, `work_mode`, `employment_type`, `external_job_id`) plus a dated freshness basis. Before writing a report, Greenhouse accepts only HTTPS hosted pages matching `boards.greenhouse.io/<board>/jobs/<id>`; Lever accepts only HTTPS hosted pages matching `jobs.lever.co/<site>/<posting-id>` or `jobs.eu.lever.co/<site>/<posting-id>`. Other schemes, hosts, malformed paths and application URLs are rejected. The Greenhouse normalizer retains provider `updated_at` as `source_updated_on`, never as a posting date; the Lever normalizer maps `createdAt` to `date_posted` and never retains `applyUrl`. The output is a private acquisition report, not a verified match, tracker row or application authorization. Import that report only after selecting its source in private rules and applying normal freshness/canonical-URL validation.

## Run one explicit read

```bash
python3 ${HERMES_SKILL_DIR}/scripts/vacancy_acquisition.py \
  --adapter greenhouse_public_board \
  --source-identifier <candidate-confirmed-board-token> \
  --company '<candidate-confirmed-company-label>' \
  --as-of <YYYY-MM-DD> \
  --output <private-acquisition.json>
```

The command performs one outbound `GET` only when invoked. It has no credential input, no write endpoint and no application path. Keep both input identifiers and output under the private workspace, outside Git.

## Catalog freshness audit

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <private-workspace> catalog-audit \
  --as-of <YYYY-MM-DD> --max-age-days 90
```

The audit validates every local evidence URL/date/scope and returns entries due for a human re-check. It opens no URL and refreshes no claim. A human must re-check an official source before changing the catalog date or scope.

## External actions

`propose_external_action()` creates a deterministic plan for `tracker_write`, `application`, `message` or `contact`. A plan is always `draft_only` and has `external_actions: 0`; its hash binds action, target and payload. It has no executor.

Existing optional Google Sheets and local Obsidian executors remain separate. They require a private workspace, `confirm_each_external`, an exact reviewed hash, current target read and verified readback. Gmail remains limited to explicit-message triage and mark-read; Career Copilot has no send-message, application or contact executor. A target-company or Human Path research record never grants contact authorization.

## Sources

- Greenhouse Job Board API: https://docs.greenhouse.io/job-board.html
- Lever Postings API: https://github.com/lever/postings-api
