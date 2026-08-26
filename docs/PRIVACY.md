# Privacy and threat model

## Public/distributable

- Skill instructions and methodology
- Empty templates
- Deterministic scripts
- Synthetic fixtures
- Tests and CI

## Private/user-owned

- Candidate identity and contact information
- CVs and supporting documents
- Compensation preferences
- Contacts and networking history
- Emails and message IDs
- Live vacancy/application tracker
- Account identifiers, tokens and credential files
- Hermes sessions, memories and profile exports

## Storage boundary

Private files belong in `career_copilot.workspace`, outside both the source repository and installed Hermes profile. The onboarding script rejects workspaces inside the distribution/profile root.

The repository `.gitignore` blocks common private artifacts, but ignore rules are defense-in-depth—not permission to store private files in the clone.

## External-action boundary

Without explicit action-specific confirmation, Career Copilot may:

- analyze supplied information;
- search/read when authorized;
- update private local state according to local policy;
- prepare drafts and previews.

It may not:

- apply for a role;
- send or reply to a message;
- publish or modify a public profile;
- contact a person;
- change an external spreadsheet or message state.

Adapter mutations additionally require `--apply` and readback verification.

## Validation

Before every release:

```bash
PRIVATE_MARKERS='<comma-separated local identifiers>' python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
```

Use identifiers only through the environment; never commit the marker list.

## Incident response

If private data is accidentally committed:

1. Stop sharing the repository.
2. Rotate any exposed secret immediately.
3. Remove the data from Git history, not only the latest file.
4. Re-run the privacy scanner with relevant private markers.
5. Review remote caches, forks, Actions artifacts and logs.
6. Document the cause and add a regression test without embedding the leaked value.
