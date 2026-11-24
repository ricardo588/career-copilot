---
name: career-copilot
description: Run Career Copilot from a private local workspace.
---

# Career Copilot

Use the portable core in this repository at `skills/career-copilot/`. Read its `SKILL.md` and the minimum linked reference needed for the task before operating.

## Boundaries

- Keep candidate data, CVs, contacts, compensation, credentials, IDs, messages and trackers in a user-owned workspace outside this repository and any Git repository.
- Default to `draft_only`. Do not send, apply, contact people, or mutate external systems.
- Execute local scripts only with explicit private input and output paths. Use synthetic fixtures for repository verification.
- Public acquisition remains explicit and read-only. Only Greenhouse and Lever have integrated public reads; other providers are coverage guidance only.

## Portable commands

From the repository root, invoke scripts with explicit paths:

```bash
python3 skills/career-copilot/scripts/onboarding.py --workspace <private-workspace> start
python3 skills/career-copilot/scripts/provider_selection.py --workspace <private-workspace> --profile <private-profile.json> --rules <private-rules.json> --output <private-selection.json>
```

Read `docs/ROADMAP-0.12.0.md` for portability and provider-selection limits. Do not claim local execution in hosts that cannot execute scripts.
