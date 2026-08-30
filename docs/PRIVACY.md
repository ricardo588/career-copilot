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
- Story-bank evidence, metrics, provenance and career-direction preferences
- Relationship evidence/authorization, meeting outcomes and interview debrief reflections
- Emails and message IDs
- Live vacancy/application tracker
- Account identifiers, tokens and credential files
- Hermes sessions, memories and profile exports

## Storage boundary

Generated private state belongs in `career_copilot.workspace`, outside both the source repository and installed Hermes profile. A CV may remain at its candidate-chosen local path outside Git repositories; onboarding stores the path and confirmed proposal state without copying the CV. The onboarding script rejects workspaces inside the distribution/profile root or a Git tree.

Hermes extracts CV text from the local file. The extracted content is then processed by the model provider configured for that Hermes profile unless the user selected a local model. Onboarding must disclose that boundary before asking for the file. The checkpoint stores only proposed values, direct/inferred labels and source-section names required for confirmation—not the full extracted CV text. No additional document parser or OCR service is used by default.

Every bootstrap run normalizes the private workspace and nested directories to `0700`, and regular files to `0600`; symlinks are rejected. CV proposals are bound to the staged file contents with SHA-256 and cannot be confirmed if the source changes at the same path.

The repository `.gitignore` blocks common private artifacts, but ignore rules are defense-in-depth—not permission to store private files in the clone.

## External-action boundary

In the default `draft_only` mode, Career Copilot may:

- analyze supplied information;
- search/read when authorized;
- update private local state according to local policy;
- prepare drafts and previews.

It may not, even if draft text was approved or `--apply` was supplied:

- apply for a role;
- send or reply to a message;
- publish or modify a public profile;
- contact a person;
- change an external spreadsheet or message state.

Other users may explicitly opt in to `confirm_each_external`. That mode still requires fresh confirmation for the exact destination, content and action. A profile with `external_action_mode_locked: true` remains `draft_only`; onboarding and reset cannot change it.

Human Path, relationship intelligence, meeting prep and interviewer research are always read-only. Discovering a contact, recruiter, hiring manager or interviewer does not authorize contact, reference use, referral language, introduction or follow-up. Interview debrief mode does not update the tracker; any follow-up remains a draft.

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
