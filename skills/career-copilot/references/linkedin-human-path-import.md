# LinkedIn connections export to Human Path (read-only)

`linkedin_human_path_import.py` consumes an explicitly supplied private connections CSV and vacancy JSON and emits a review artifact to stdout.

```bash
python3 skills/career-copilot/scripts/linkedin_human_path_import.py \
  --workspace /private/workspace \
  --export /private/workspace/connections.csv \
  --vacancy /private/workspace/vacancy.json
```

It never accepts an output path and never writes a filesystem artifact. The caller is responsible for any optional persistence of stdout.

The CSV requires `First Name`, `Last Name`, and `Company`; optional columns are `Position` and `Connected On`. Duplicate or unknown headers fail closed.

Every match is only a historical discovery clue. It reports discovery state `export_match_found`, identity state `needs_identity_review`, current employment `unverified`, and a contact-permission value of `not_granted`. No textual match confirms identity, employment, relationship strength, referral availability or permission to contact.
