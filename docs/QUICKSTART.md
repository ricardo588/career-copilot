# Quickstart

## Install

```bash
hermes profile install <OWNER>/career-copilot --name my-career-copilot --alias
hermes -p my-career-copilot setup
```

## Initialize private state

```bash
SKILL_DIR="$HOME/.hermes/profiles/my-career-copilot/skills/career-copilot"
WORKSPACE="$HOME/Documents/CareerCopilot"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" start
```

## Run conversational onboarding

```bash
hermes -p my-career-copilot chat -s career-copilot
```

Ask Career Copilot to continue onboarding. It should:

1. Read onboarding status.
2. Ask whether the user already has a CV.
3. If so, read it locally and ask the user to confirm or correct the extracted proposal.
4. Ask one phase at a time only for missing information and permissions.
5. Store each confirmed answer in the private checkpoint.
6. Report missing required fields without repeating sensitive values.
7. Finalize only when required fields are complete.

## Run the safe synthetic demo

```bash
DEMO_DIR="$(mktemp -d)/career-copilot-demo"
python3 "$SKILL_DIR/scripts/run_synthetic_demo.py" --output-dir "$DEMO_DIR"
```

Expected result:

- recommendation `High`;
- one deduplicated tracker row;
- one interview brief;
- zero external actions.

## First real workflow

After onboarding is complete, ask:

> Evaluate this vacancy against my private profile. Separate confirmed facts, fit interpretation, gaps, and next action. Do not apply or contact anyone.

See [PRIVACY.md](PRIVACY.md) before enabling integrations.
