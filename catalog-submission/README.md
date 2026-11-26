# Local catalog-submission preparation

This directory is intentionally outside `plugin-catalog/` and contains no catalog entry. It is a local checklist, not an external write payload.

Do not create, copy, or submit a catalog YAML from this repository state. The Phase 2 package is a release candidate and is neither admitted, listed, searchable, nor approved.

## Generate a future entry only after explicit authorization

1. Publish an authorized public release first. This task does not publish one.
2. Resolve the release commit and verify it is a full immutable 40-character Git SHA:

   ```bash
   git rev-parse <authorized-release-tag>^{commit}
   ```

3. Re-run package validation against that exact checkout, including `hermes plugins validate <path> --install-deps` when catalog submission is authorized.
4. Prepare one `plugin-catalog/career-copilot.yaml` file in the authorized Hermes catalog checkout. Its `sha` must be the exact value from step 2 and its quoted `version` must match the published release.
5. Disclose that this is a skill-only portable Agent Plugins v1 package, with no tools, hooks, middleware, MCP server, environment variables, secrets, telemetry, services, or package-side installation/network activity; describe the private workspace and `draft_only` boundary.
6. Show Ricardo the exact external diff and disclosure before any PR or publication action.

No SHA is included here: a branch, tag, short SHA, placeholder, or invented value is not acceptable for catalog submission.
