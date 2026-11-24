# Agent hosts and portability

Versión en español: [docs/es/AGENT-HOSTS.md](es/AGENT-HOSTS.md).

Career Copilot is a local-first workflow package, not a single-agent product. Its portable core is `skills/career-copilot/`: a `SKILL.md`, deterministic Python scripts, references, templates and synthetic examples. It contains no candidate data, credentials or host-specific profile state.

## Supported hosts in v0.12.1

| Host | Support | Entry point |
| --- | --- | --- |
| Hermes Agent | Executable adapter | `distribution.yaml`, `install.sh` and `Install_Career_Copilot.command` |
| Claude Code | Executable skill adapter | `.claude/skills/career-copilot/SKILL.md` |
| OpenClaw | Executable skill adapter | `.openclaw/skills/career-copilot/SKILL.md` |
| ChatGPT | Guidance only | `agent-adapters/chatgpt/INSTRUCTIONS.md` |

The Claude Code and OpenClaw adapters point to the same portable core. They do not create a profile, install dependencies, obtain credentials or grant external-action permission.

## Use with an executable local host

1. Clone the repository and use the host's documented local-skill discovery method.
2. Ensure Python 3.11+ is available to the host if it will execute the scripts.
3. Create a private workspace outside the clone and every Git repository.
4. Read `skills/career-copilot/SKILL.md` before operating. Run only the workflow that the user explicitly requested.
5. Pass explicit paths below the private workspace. Default to `draft_only`; do not perform an external action without the required current authorization.

The Python scripts are host-neutral, but a host is not automatically supported merely because it can read Markdown. It must preserve the private-workspace and explicit-action boundaries and must be able to execute local Python safely.

## ChatGPT boundary

The ChatGPT package explains the workflow and can prepare reviewable instructions. It does not have access to a local workspace or terminal by default and must not claim that it ran a script, checked a vacancy, updated a tracker, sent a message or submitted an application. Use a supported executable local host for those steps.

## Hermes-specific distribution

Hermes remains a supported optional adapter. Its profile installer, commands and troubleshooting guidance are documented in [INSTALL.md](INSTALL.md), [QUICKSTART.md](QUICKSTART.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Those commands do not apply to Claude Code, OpenClaw or ChatGPT.
