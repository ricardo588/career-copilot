# Hermes Marketplace plugin package

Versión en español: [docs/es/PLUGIN_MARKETPLACE.md](es/PLUGIN_MARKETPLACE.md).

## Package layout

The repository root is a portable Agent Plugins v1 package:

- `plugin.json` is the root manifest.
- `skills/career-copilot/` is the single runtime skill tree; it is not copied or vendored elsewhere.
- The skill's deterministic scripts, empty templates and synthetic fixtures remain under that tree.

The package has no `mcp.json`, `plugin.yaml`, Python entrypoint, tools, hooks, middleware, lifecycle service, cron, install/network hook, telemetry, configuration schema, environment-variable requirement, secret requirement, or dependency manifest. Installing it neither configures a model provider nor needs credentials.

## Install, enable, disable, and remove

After Marketplace catalog admission, the reviewed install route will be:

```bash
hermes plugins install career-copilot
hermes plugins enable career-copilot
hermes plugins disable career-copilot
hermes plugins remove career-copilot
```

Portable packages install disabled by default. `enable` exposes the package's namespaced skill in a new Hermes session; it does not start a service or grant capabilities. `disable` hides the package without deleting it. `remove` removes only the installed package. It does not delete a candidate workspace, other skills, or a complete Hermes profile.

Before catalog admission, `career-copilot` is not a Marketplace name and must not be presented as discoverable or approved. A trusted user may use Hermes's documented custom Git-source installation path, preferably pinned to a full published commit SHA; that path is not catalog review.

## Coexistence and namespaces

This package reuses `skills/career-copilot/` directly. Hermes exposes plugin skills under a plugin-derived namespace (for example, `agent-plugin-career-copilot-<hash>:career-copilot`), so it does not silently overwrite the separately installed skills.sh skill named `career-copilot`.

Career Copilot has three distinct distribution routes:

| Route | Scope | State behavior |
|---|---|---|
| skills.sh community skill | Lightweight direct skill install | Separate installed skill; no automatic state sharing. |
| Marketplace plugin package | Reviewed plugin distribution when admitted | Namespaced skill; no extra privileges or duplicated runtime tree. |
| Complete Hermes profile | Isolated profile distribution | Separate profile configuration and skill copy. |

Choose one route for the intended host setup. Installing more than one route does not synchronize configuration or candidate state. In every route, select a private workspace outside the repository, plugin installation, and host profile.

## Privacy, actions, and optional integrations

The package contains methodology, empty templates, deterministic scripts and synthetic fixtures only. It does not contain candidate CVs, contacts, compensation, trackers, email, credentials, provider settings, session state, or profile exports.

`draft_only` remains the default external-action policy. The package does not automatically apply, send messages, contact people, publish, alter a real pipeline, open a login, or make network calls as an effect of installation or enablement. Google Sheets, Gmail, and Obsidian are optional integrations governed by the existing skill instructions; each needs user-owned configuration and explicit authorization. A model-provider configuration belongs to the user's Hermes host, never to this package.

## Rollback and uninstall protection

Disable the plugin to roll back availability while preserving its installed files, or remove it to delete only the installed package. Neither operation removes a user-selected candidate workspace. Back up or manage that private workspace separately; it is deliberately outside the package lifecycle.

## Validation is not catalog admission

`hermes plugins doctor . --ci` validates the local portable package against Hermes runtime contracts. Repository tests and privacy scans validate this source tree. These checks do not create a catalog entry, publish a release, reserve the `career-copilot` name, make the package searchable, or represent human review.

Catalog admission happens later and separately: an authorized published release supplies a full immutable 40-character commit SHA; an authorized contributor then submits one catalog-entry PR to the Hermes repository; catalog CI validates that pinned tree; and a maintainer reviews and merges or declines it. Until that merge, there is no official Marketplace listing or discoverability claim.

See [the local catalog-submission process](../catalog-submission/README.md) for the intentionally non-submittable preparation record.
