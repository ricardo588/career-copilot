# Career Copilot for Hermes

Reusable, privacy-first job-search operations for [Hermes Agent](https://hermes-agent.nousresearch.com/docs).

## Capabilities

- Resumable conversational onboarding with private checkpoints
- Candidate-specific vacancy evaluation using verified evidence
- Canonical deduplication and local CSV tracking
- Synthetic profile → vacancy → tracker → interview demo
- Optional dry-run-first Google Sheets, Gmail and Obsidian adapters
- Explicit guardrails for messages, applications and public actions
- Automated privacy, installation and functional tests

## Privacy model

The repository contains methodology, empty templates, deterministic scripts and synthetic fixtures only. Candidate CVs, contacts, compensation, emails, memories, sessions, credentials, IDs and live trackers belong in each installer's private workspace and are never committed.

Do not export a personal Hermes profile to distribute this project. Install the profile distribution contained here.

## Documentation

- [Installation](docs/INSTALL.md) — full CLI reference
- [Non-technical quickstart](QUICKSTART_NONTECH.md) — one-liner, macOS .command, step-by-step guide
- [Quickstart](docs/QUICKSTART.md) — developer quickstart
- [Synthetic demo](docs/DEMO.md)
- [Optional adapters](docs/ADAPTERS.md)
- [Privacy and threat model](docs/PRIVACY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Installers (for end users)

| Method | File | Best for |
|--------|------|----------|
| **One-liner (Linux/macOS/WSL)** | [`install.sh`](install.sh) | Users comfortable with Terminal |
| **Double-click (macOS)** | [`Install_Career_Copilot.command`](Install_Career_Copilot.command) | Zero-terminal experience |
| **Step-by-step guide** | [`QUICKSTART_NONTECH.md`](QUICKSTART_NONTECH.md) | Anyone who wants to read first |

All installers create an isolated Hermes profile, a private workspace (`~/Documents/CareerCopilot/` with `0700/0600` permissions), and start guided onboarding — no candidate data leaves the machine without explicit confirmation.

## Local development

Requirements: Hermes Agent 0.20.0+, Git and Python 3.11+.

```bash
python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
hermes profile install . --name career-copilot-test
```

Run the no-account end-to-end demo:

```bash
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir "$OUTPUT_DIR"
```

## Current status

Version 0.2.0 is a private pilot release. Google adapters require a separately installed and authenticated compatible `gws` CLI. The Gmail adapter intentionally does not send messages.

No redistribution license has been selected yet.
