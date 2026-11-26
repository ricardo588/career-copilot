# Install with Hermes Agent

Versión en español: [docs/es/INSTALL.md](es/INSTALL.md).

This page documents the **Hermes-specific adapter**. Career Copilot's portable core also supports Claude Code and OpenClaw, while ChatGPT receives guidance only; select the appropriate host in [AGENT-HOSTS.md](AGENT-HOSTS.md) before following any command here. Each person gets a separate private workspace; the repository contains no candidate data.

## Marketplace plugin package (0.16.0 release candidate)

The root `plugin.json` is a portable Agent Plugins v1, skill-only package that directly reuses `skills/career-copilot/`. It is distinct from the complete-profile instructions below. It has no plugin code, tools, hooks, MCP server, service, credentials, provider configuration, telemetry, dependencies, or install-time network behavior.

It is locally validated but not catalog-admitted, approved, or discoverable. Do not run `hermes plugins install career-copilot` as though it were a current catalog name. After a separately authorized release and catalog admission, the reviewed lifecycle will be:

```bash
hermes plugins install career-copilot
hermes plugins enable career-copilot
hermes plugins disable career-copilot
hermes plugins remove career-copilot
```

Portable packages install disabled. Enabling exposes a plugin-namespaced skill in a new session; it does not start a service or create a workspace. Removing it deletes only the installed package, never a user-selected candidate workspace. Read [Marketplace package details](PLUGIN_MARKETPLACE.md) before choosing this route.

## Quick links for end users

| Method | File | Best for |
|--------|------|----------|
| **One-liner (Linux/macOS/WSL)** | [`install.sh`](../install.sh) | Users comfortable with Terminal |
| **Double-click (macOS)** | [`Install_Career_Copilot.command`](../Install_Career_Copilot.command) | Zero-terminal experience |
| **Step-by-step guide** | [`QUICKSTART_NONTECH.md`](../QUICKSTART_NONTECH.md) | Anyone who wants to read first |

## Prerequisites

- Hermes Agent 0.20.0 or newer
- Python 3.11 or newer
- Git
- Access to the public distribution repository
- A configured model provider in Hermes

Verify:

```bash
hermes --version
python3 --version
git --version
```

## 1. Obtain the repository

The repository is public. Clone it directly or install from GitHub without credentials:

```bash
git clone https://github.com/ricardo588/career-copilot.git
```

## 2. Install an isolated profile

From a local clone:

```bash
hermes profile install /path/to/career-copilot --name my-career-copilot --alias
```

Or from a GitHub repository the installer can access:

```bash
hermes profile install ricardo588/career-copilot --name my-career-copilot --alias
```

The installer validates `distribution.yaml` and copies only distribution-owned files.

## 3. Configure Hermes

```bash
hermes -p my-career-copilot setup
hermes -p my-career-copilot config migrate
hermes -p my-career-copilot skills list
```

Confirm that `career-copilot` is enabled.

## 4. Create a private workspace

Choose a directory outside the cloned repository and outside the Hermes profile directory.

```bash
SKILL_DIR="$HOME/.hermes/profiles/my-career-copilot/skills/career-copilot"
WORKSPACE="$HOME/Documents/CareerCopilot"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" start
```

The bootstrap does not overwrite existing files. Onboarding checkpoints to a hidden JSON file and creates backups before finalizing `profile.yaml` or `rules.yaml`.

## 5. Start the assistant

```bash
hermes -p my-career-copilot chat -s career-copilot
```

Suggested first message:

> Continue my Career Copilot onboarding. First ask whether I already have a CV; if I do, extract supported information locally and ask me to confirm or correct it. Then ask one short section at a time for anything missing, checkpoint every confirmed answer, and keep the default draft-only mode.

`draft_only` blocks external actions. Other users may explicitly opt in to `confirm_each_external`; each exact action and destination still needs fresh confirmation. For a profile that must never change modes, initialize onboarding with `start --lock-draft-only`.

## 6. Verify isolation

- Generated candidate state exists only under the chosen workspace. A source CV may remain at its user-chosen local path and must never be copied into the clone or installed profile.
- No CV, contact, compensation data or credentials appear in the clone.
- `git status --short` remains clean after using the assistant.
- External integrations remain disabled until configured locally.

## Updating

Update the source clone, review release notes, then reinstall into a disposable profile before replacing a working profile.

```bash
git pull --ff-only
hermes profile install . --name career-copilot-upgrade-test
hermes -p career-copilot-upgrade-test skills list
```

For 0.9.1, no private-data migration is required. Existing onboarding checkpoints gain empty `search.target_companies` and `search.selected_job_portals` lists when resumed; existing workspaces and local CSV trackers remain compatible. Portal suggestions are local, transparent coverage heuristics based only on declared roles and eligible geography, not live market rankings. Gmail evidence, idempotency-ledger and adapter audit directories are created only when an optional adapter command is run in a user-selected private workspace. Optional Obsidian Kanban projection never scans or migrates a vault; it requires an explicit vault, board-relative Markdown path, lane and reviewed artifact. The 0.7 onboarding checkpoint migration to schema 5 remains applicable to profiles that predate it; do not add compensation columns manually—see
`skills/career-copilot/references/tracker-compensation-migration.md`.

Never use a personal profile export as an upgrade or distribution mechanism.
