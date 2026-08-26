---
name: career-copilot
description: Use when managing a private, profile-driven job search.
version: 0.1.0
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
        description: Storage backend; version 0.1 supports local
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

- Initialize or update the candidate profile and search rules.
- Evaluate one or more vacancies.
- Search for opportunities and deduplicate them against the tracker.
- Reconcile recruiter/ATS evidence with the application pipeline.
- Draft networking, application and follow-up messages.
- Prepare interviews or summarize current priorities.

## Startup

1. Read the injected `career_copilot.workspace` setting.
2. Check for `profile.yaml`, `rules.yaml` and `tracker.csv` in that private workspace.
3. If missing, read `references/onboarding.md` and offer to initialize with:

   `python3 ${HERMES_SKILL_DIR}/scripts/bootstrap_workspace.py --workspace <configured-path>`

4. Read only the minimum private files needed for the task.
5. Do not copy private workspace content into this skill directory or a Git repository.

## Core workflow

1. Establish the task: onboarding, evaluate, search, track, reconcile, draft, prepare or summarize.
2. Load candidate facts and constraints from the private workspace.
3. Verify live vacancy/process evidence before changing state.
4. Apply `references/evaluation.md` and the user's local rules.
5. Deduplicate and update using `references/tracker-schema.md`.
6. Apply `references/privacy-and-actions.md` before any external action.
7. Verify written state by reading it back.
8. Report facts, interpretation, changes and next action separately when ambiguity exists.

## Default operating principles

- Quality over volume.
- Official employer or ATS source over aggregators when available.
- Canonical job ID/URL before title-text dedupe.
- A tracker write is not an application submission.
- Passive waiting is context, not automatically a task.
- Never fabricate missing candidate evidence to improve perceived fit.
- Do not send messages, apply, publish, modify public profiles or contact people without explicit approval for that action.

## References

- `references/onboarding.md` — private profile initialization.
- `references/workflow.md` — end-to-end operating flows.
- `references/evaluation.md` — qualitative fit decision.
- `references/tracker-schema.md` — portable local tracker and state rules.
- `references/privacy-and-actions.md` — privacy boundary and authorization model.

## Verification

- Candidate-specific conclusion came from local profile/rules, not author defaults.
- Vacancy/process facts were verified from a current source when accessible.
- No duplicate tracker record was created.
- Any state write was read back.
- External actions were not claimed without execution evidence.
- No private data was written inside the skill or distribution repository.
