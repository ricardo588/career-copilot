# Troubleshooting

Versión en español: [docs/es/TROUBLESHOOTING.md](es/TROUBLESHOOTING.md).

## Skill does not appear

```bash
hermes -p <PROFILE> skills list
hermes profile info <PROFILE>
```

Reinstall from a validated source if `career-copilot` is absent. Do not copy a personal profile as a shortcut.

## Workspace was created in the wrong place

Stop before adding personal data. Create a new directory outside the repository and profile root, update `skills.config.career_copilot.workspace`, and bootstrap again.

The onboarding script intentionally rejects an in-profile workspace.

## Onboarding will not finalize

```bash
SKILL_DIR="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace '<WORKSPACE>' status
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace '<WORKSPACE>' questions
```

At minimum, provide target roles, seniority, strengths, verified evidence, eligible country/location, tracker policy and external-action policy.

## YAML cannot be read by the pipeline

Finalized onboarding files are JSON-compatible YAML and need no dependency. Hand-edited traditional YAML requires PyYAML in the executing environment.

## `gws` is not found

The Google adapters are optional. Install/authenticate a compatible Google Workspace CLI using its official documentation, then verify `gws --help`. Do not add credentials to this repository.

## Google mutation fails verification

Treat the operation as failed. Read the exact target again, confirm account/sheet/range/message ID, and retry only after resolving the mismatch. Never report success from an API exit code alone.

## Obsidian path rejected

Use a relative `.md` path beneath the configured vault. Absolute paths and `..` traversal are blocked.

## CI privacy scan fails

Run locally:

```bash
python3 skills/career-copilot/scripts/privacy_scan.py .
```

If a custom marker triggered the failure, remove the private value and replace it with synthetic data. Do not weaken the scanner merely to make CI pass.

## Need Hermes Agent help

Use the current official documentation: https://hermes-agent.nousresearch.com/docs
