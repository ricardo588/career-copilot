# Career Copilot 0.12.0 — Portable Agent Skills and Provider Selection

Spanish version: [docs/es/ROADMAP-0.12.0.md](es/ROADMAP-0.12.0.md).

## Goal

Make Career Copilot usable from Hermes, Claude Code and OpenClaw through one portable, local-first skill contract. Provide a ChatGPT guidance package that explains the same process and privacy boundaries without claiming local script execution.

Add deterministic provider recommendations based only on a candidate's declared role family, seniority, eligible geography, work mode and employment type.

## Confirmed decisions

- Supported executable skill hosts in v0.12.0: Hermes, Claude Code and OpenClaw.
- ChatGPT receives instructions and reference material only; it has no workspace, script, credential, local-file or action capability.
- Initial provider-coverage scope: Mexico, Latin America, United States and remote work.
- Greenhouse and Lever remain the only integrated public read adapters. A candidate/operator must still explicitly invoke one read with a confirmed identifier.
- Provider recommendations are local coverage guidance, never a market ranking, live-vacancy assertion or authorization to query a provider.

## Architecture

### Portable core

The portable core contains only `SKILL.md`, references, templates, deterministic Python scripts and synthetic examples. It has no Hermes profile settings, agent credentials or candidate data.

The portable skill requires an explicit private workspace path, Python 3.11+ and an agent host that can invoke local scripts. Every script invocation remains local unless a documented acquisition adapter is explicitly invoked.

### Host adapters

- **Hermes:** existing `distribution.yaml`, profile config and installer remain an optional Hermes adapter.
- **Claude Code:** project/user skill installation copies or links the portable skill directory into the host's documented skill location. No Claude API integration is required.
- **OpenClaw:** install the same portable skill directory under OpenClaw's documented skill root. No OpenClaw-specific external tool is introduced.
- **ChatGPT:** use a separately packaged instruction document. It can guide a user through decisions and generate reviewable commands, but must state that the user or another local agent must run commands. It must never request candidate data for repository storage.

### Provider registry

A public, versioned registry records provider ID, declared coverage criteria, evidence URL/date, acquisition state and safe invocation contract.

`provider_selection.py` consumes only private profile/rules inputs and registry metadata. It returns selected and non-selected providers with reasons, unknowns and the explicit-action requirement. It does not perform network requests, discover board/site identifiers or mutate the tracker.

A provider can be marked:

- `integrated_read_only`: a separately tested public GET adapter exists.
- `coverage_only`: it may be suggested for manual review but has no executable acquisition path.
- `not_supported`: it is not returned as actionable.

## Safety gates

- No credentials, candidate data, board identifiers or private outputs in the repository.
- No automatic discovery, query, scraping, browser use, application, contact or tracker write.
- A new executable provider requires a separately verified public contract, synthetic fixture, URL/identifier validation, no-redirect policy, tests and paired documentation.
- Portable-host documents must not describe unavailable tools as if they were executable.

## Acceptance criteria

- One synthetic provider-selection command produces the same result from the same profile/rules/registry input without network access.
- Mexico, Latin America, United States and remote criteria are represented by versioned evidence records.
- Greenhouse and Lever remain explicit-only public reads.
- Hermes, Claude Code and OpenClaw instructions identify the same portable core and do not require credentials.
- ChatGPT instructions clearly declare guidance-only limitations.
- Every distribution artifact is synthetic and passes the privacy/bundle validators.
