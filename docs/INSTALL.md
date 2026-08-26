# Installation for third parties

Career Copilot installs as an isolated Hermes profile. Each person gets a separate private workspace; the repository contains no candidate data.

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
- Access to the distribution repository during the private pilot
- A configured model provider in Hermes

Verify:

```bash
hermes --version
python3 --version
git --version
```

## 1. Obtain repository access

During the private pilot, the repository owner must invite the installer as a collaborator. Authenticate Git without copying tokens into the repository.

```bash
gh auth login
```

If `gh` is unavailable, use another Git credential flow supported by the installer’s operating system.

## 2. Install an isolated profile

From a local clone:

```bash
hermes profile install /path/to/career-copilot --name my-career-copilot --alias
```

Or from a GitHub repository the installer can access:

```bash
hermes profile install <OWNER>/career-copilot --name my-career-copilot --alias
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

> Continue my Career Copilot onboarding. Ask one short section at a time, checkpoint every answer, and never perform an external action without my explicit confirmation.

## 6. Verify isolation

- Candidate files exist only under the chosen workspace.
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

Never use a personal profile export as an upgrade or distribution mechanism.
