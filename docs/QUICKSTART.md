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
2. Ask one phase at a time.
3. Store each answer in the private checkpoint.
4. Report missing required fields without repeating sensitive values.
5. Finalize only when required fields are complete.

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
