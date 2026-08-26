---
name: career-copilot
description: Use when managing a private, profile-driven job search.
version: 0.2.0
author: Career Copilot contributors
metadata:
  hermes:
    tags: [career, jobs, applications, interviews, privacy]
    config:
      - key: career_copilot.workspace
        description: Private directory for candidate profile, rules and tracker
        default: "~/Documents/CareerCopilot"
        prompt: Private Career Copilot workspace path
      - key: career_copilot.storage_backend
        description: Storage backend; local is the safe default
        default: "local"
        prompt: Career Copilot storage backend
      - key: career_copilot.default_language
        description: Response language or auto
        default: "auto"
        prompt: Default response language
---

# Career Copilot

Use this skill to run a structured job search from each user's private candidate profile. Never assume the candidate resembles the skill author or another user.

## When to use

- Initialize, resume or update the candidate profile and search rules.
- Evaluate vacancies against verified evidence and constraints.
- Deduplicate and maintain a private application tracker.
- Reconcile recruiter or ATS evidence with pipeline state.
- Prepare networking, application, follow-up and interview drafts.
- Use optional Google Sheets, Gmail or Obsidian adapters.

## Startup

1. Resolve the injected `career_copilot.workspace` setting.
2. Confirm the workspace is outside this skill/profile and any Git repository.
3. Check for `profile.yaml`, `rules.yaml` and `tracker.csv`.
4. If missing, read `references/onboarding.md` and bootstrap with:

   `python3 ${HERMES_SKILL_DIR}/scripts/bootstrap_workspace.py --workspace <configured-path>`

5. Read only the minimum private files needed for the current task.
6. Never copy private workspace content into this skill directory or distribution repository.

## Conversational onboarding

1. Start or resume the checkpoint:

   `python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <configured-path> start`

2. Ask one short phase at a time. Do not ask for passwords, tokens, government IDs or payment data.
3. Store each approved answer with `answer --field <field> --json-value '<valid-json>'`.
4. Re-run `status` after each phase. Do not repeat sensitive values unnecessarily.
5. Finalize only when `missing` is empty:

   `python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <configured-path> finalize`

6. Read back only completion status and paths unless the user asks to inspect values.

Full field order, resume behavior and edge cases are in `references/onboarding.md`.

## Core workflow

1. Establish the task: onboard, evaluate, search, track, reconcile, draft, prepare or summarize.
2. Load candidate facts and constraints from the private workspace.
3. Verify live vacancy/process evidence before changing state.
4. Apply `references/evaluation.md` and local rules.
5. Deduplicate and update using `references/tracker-schema.md`.
6. Apply `references/privacy-and-actions.md` before any external action.
7. Verify every state write by reading it back.
8. Separate confirmed facts, interpretation, unknowns, changes and next action.

For deterministic local evaluation/tracking/brief generation, use:

`python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py --profile <profile> --rules <rules> --vacancy <vacancy-json> --as-of <YYYY-MM-DD> [--tracker <csv>] [--brief <md>]`

The script supports the workflow; it does not replace current-source verification.

## Optional adapters

Read `references/adapters.md` before use.

- Google Sheets: explicit range; updates are dry-run-first and require `--apply`.
- Gmail: search/read plus dry-run-first mark-read; sending is intentionally unsupported.
- Obsidian: scoped local Markdown writes; rejects paths outside the configured vault.
- Every mutation must pass readback verification.
- Never store adapter credentials or IDs in the distributable repository.

## Default operating principles

- Quality over volume.
- Official employer or ATS source over aggregators when available.
- Canonical job ID/URL before title-text dedupe.
- A tracker write is not an application submission.
- Passive waiting is context, not automatically a task.
- Never fabricate missing candidate evidence to improve fit.
- Do not send, apply, publish, modify public profiles or contact people without explicit approval for that exact action.

## Synthetic verification

Run the bundled no-account demo when validating a new installation:

`python3 ${HERMES_SKILL_DIR}/scripts/run_synthetic_demo.py --output-dir <temporary-directory>`

See `references/demo.md` for pass criteria.

## References

- `references/onboarding.md` — checkpointed private onboarding.
- `references/workflow.md` — end-to-end operating flows.
- `references/evaluation.md` — qualitative fit decision.
- `references/tracker-schema.md` — local tracker and state rules.
- `references/privacy-and-actions.md` — privacy and authorization model.
- `references/adapters.md` — optional integration safety contract.
- `references/demo.md` — synthetic end-to-end verification.

## Verification

- Candidate-specific conclusions came from local profile/rules, not author defaults.
- Vacancy/process facts were verified from a current source when accessible.
- No duplicate tracker record was created.
- Any state write was read back.
- External actions were not claimed without execution evidence.
- No private data was written inside the skill or distribution repository.
