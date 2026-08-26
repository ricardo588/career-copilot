# Career Copilot for Hermes

Private alpha of a reusable, privacy-first job-search operating system for [Hermes Agent](https://hermes-agent.nousresearch.com/docs).

## What it provides

- Candidate-specific opportunity evaluation
- Search and source prioritization
- Deduplicated application tracking
- Recruiter and ATS email triage
- Networking and application drafts
- Interview preparation and follow-up
- Explicit guardrails for external actions

## Privacy model

The repository contains methodology, templates and validators only. Candidate CVs, contacts, compensation, emails, memories, sessions, credentials and live trackers belong in the installer's private workspace and are never committed.

Do not export a personal Hermes profile to distribute this project. Use the profile distribution contained in this repository.

## Local development

Requirements: Hermes Agent 0.20.0+, Git and Python 3.11+.

```bash
python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
hermes profile install . --name career-copilot-test --alias
```

## Candidate onboarding

After installing the distribution, load `/career-copilot` and ask to initialize the private workspace. The skill uses the configured `skills.config.career_copilot.workspace` path and creates local profile, rules and tracker files without overwriting existing data.

## Status

Version 0.1.0 is a private alpha. It intentionally uses a local YAML/CSV workspace first. Google Workspace, Obsidian and other integrations will be optional adapters.

No redistribution license has been selected yet.
