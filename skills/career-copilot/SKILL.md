---
name: career-copilot
description: Use when managing a private, profile-driven job search.
version: 0.4.0
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
      - key: career_copilot.external_action_mode
        description: External action policy; draft_only is the safe default
        default: "draft_only"
        prompt: External action mode
      - key: career_copilot.external_action_mode_locked
        description: When true, draft_only cannot be changed through onboarding
        default: false
        prompt: Lock draft-only mode
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
4. Read the injected external-action settings before onboarding. Default to `draft_only` if missing or invalid.
5. If files are missing, read `references/onboarding.md` and bootstrap with:

   `python3 ${HERMES_SKILL_DIR}/scripts/bootstrap_workspace.py --workspace <configured-path>`

6. If `career_copilot.external_action_mode_locked` is true, initialize/resume onboarding with `start --lock-draft-only` and never offer a mode change.
7. Read only the minimum private files needed for the current task.
8. Never copy private workspace content into this skill directory or distribution repository.

## Conversational onboarding

1. Start or resume the checkpoint:

   `python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <configured-path> start`

2. Ask `documents.has_cv` first. If the user has a CV, read `references/cv-first-onboarding.md`, extract supported fields locally, show direct facts and inferences separately, and apply them only after explicit confirmation. Ask manually only for missing preferences and permissions.
3. Ask one short phase at a time. Do not ask for passwords, tokens, government IDs or payment data. The default mode is `draft_only`; `confirm_each_external` requires explicit user opt-in.
4. Store each approved manual answer with `answer --field <field> --json-value '<valid-json>'`.
5. Re-run `status` after each phase. Do not repeat sensitive values unnecessarily.
6. Finalize only when `missing` is empty:

   `python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <configured-path> finalize`

7. Read back only completion status and paths unless the user asks to inspect values.

Full field order, resume behavior and edge cases are in `references/onboarding.md`.

## Core workflow

1. Establish the task: onboard, evaluate, search, track, reconcile, draft, prepare or summarize.
2. Load candidate facts and constraints from the private workspace.
3. Verify live vacancy/process evidence before changing state.
4. Apply `references/evaluation.md` and local rules.
5. Deduplicate and update using `references/tracker-schema.md`.
6. For every viable vacancy, run the Human Path workflow in `references/human-path-and-interviewer-research.md`: check current trusted contacts, the exact recruiter/poster and the confirmed or likely hiring manager.
7. Apply `references/privacy-and-actions.md` before any external action. Human Path research is never authorization to contact.
8. Verify every state write by reading it back.
9. Separate confirmed facts, interpretation, unknowns, changes and next action.

For deterministic local evaluation/tracking/brief generation, use:

`python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py --profile <profile> --rules <rules> --vacancy <vacancy-json> --as-of <YYYY-MM-DD> [--human-path <private-json>] [--interviewer-research <private-json>] [--tracker <csv>] [--brief <md>]`

The script supports the workflow; it does not replace current-source verification.

## Optional adapters

Read `references/adapters.md` before use.

- Google Sheets: explicit range; updates are dry-run-first and require `--apply`, `--profile` and a `confirm_each_external` profile.
- Gmail: search/read plus dry-run-first mark-read; mutation requires `--profile`; sending is intentionally unsupported.
- Obsidian: scoped local Markdown writes; rejects paths outside the configured vault.
- Every mutation must pass readback verification.
- Never store adapter credentials or IDs in the distributable repository.

## Default operating principles

- Quality over volume.
- Official employer or ATS source over aggregators when available.
- Canonical job ID/URL before title-text dedupe.
- `draft_only` blocks every external action even if a user previously approved text or an `--apply` flag is supplied.
- `confirm_each_external` is an explicit opt-in and still requires fresh confirmation for the exact action and destination.
- A locked `draft_only` profile cannot be changed through onboarding or reset.
- A tracker write is not an application submission.
- Passive waiting is context, not automatically a task.
- Never fabricate missing candidate evidence to improve fit.
- Do not send, apply, publish, modify public profiles or contact people without explicit approval for that exact action.

## Human Path and interview-stage intelligence

- Human Path is part of vacancy evaluation, not an optional networking afterthought.
- A person is confirmed only with exact identity, current role/company relevance and a direct source URL; otherwise label the path unverified.
- Search candidate-owned contacts first, then the exact recruiter/poster, then the confirmed or likely hiring manager.
- When an interview is confirmed, reconcile the invitation and research every visible interviewer from current direct sources.
- Feed verified mandate, scope and operating language into the interview brief; keep likely priorities and questions labeled as hypotheses.
- Never infer personality, influence or preferences from title, credentials, photo or demographic characteristics.
- Research is read-only in every action mode.

## Synthetic verification

Run the bundled no-account demo when validating a new installation:

`python3 ${HERMES_SKILL_DIR}/scripts/run_synthetic_demo.py --output-dir <temporary-directory>`

See `references/demo.md` for pass criteria.

## References

- `references/onboarding.md` — checkpointed private onboarding.
- `references/cv-first-onboarding.md` — local CV extraction, proposal and confirmation workflow.
- `references/workflow.md` — end-to-end operating flows.
- `references/evaluation.md` — qualitative fit decision.
- `references/tracker-schema.md` — local tracker and state rules.
- `references/privacy-and-actions.md` — privacy and authorization model.
- `references/adapters.md` — optional integration safety contract.
- `references/demo.md` — synthetic end-to-end verification.
- `references/human-path-and-interviewer-research.md` — sourced Human Path and interviewer intelligence.

## Verification

- Candidate-specific conclusions came from local profile/rules, not author defaults.
- Vacancy/process facts were verified from a current source when accessible.
- No duplicate tracker record was created.
- Any state write was read back.
- External actions were not claimed without execution evidence.
- No private data was written inside the skill or distribution repository.
