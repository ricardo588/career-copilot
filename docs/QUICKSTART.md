# Quickstart

Versión en español: [docs/es/QUICKSTART.md](es/QUICKSTART.md).

## Install

```bash
hermes profile install ricardo588/career-copilot --name my-career-copilot --alias
hermes -p my-career-copilot setup
```

## Initialize private state

```bash
SKILL_DIR="$HOME/.hermes/profiles/my-career-copilot/skills/career-copilot"
WORKSPACE="$HOME/Documents/CareerCopilot"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" start
```

Finalization also creates or preserves the private `stories.jsonl` bank. To inspect reusable, confirmed evidence without writing:

```bash
python3 "$SKILL_DIR/scripts/story_bank.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --stories "$WORKSPACE/stories.jsonl" \
  --mode interview
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
5. Ask for optional target companies and, after role family, seniority, industry, eligible geography, work mode and employment type are known, show transparent job-portal coverage suggestions for the user to select, amend or skip.
6. When a person explicitly supplies a private vacancy export, create a read-only shortlist; do not query a portal, write the tracker, apply or contact anyone.
7. Store each confirmed answer in the private checkpoint.
8. Report missing required fields without repeating sensitive values.
9. Finalize only when required fields are complete.

## Import a private vacancy export (read only)

If the person explicitly provides a private JSON or CSV export from a selected portal, shortlist it without contacting the portal or changing the tracker. CSV support is a complete, versioned local mapping contract, not a claim that any vendor's export format is supported.

### Supported CSV contract

The following case-insensitive headers are normalized by replacing `_` and `-` with spaces and collapsing whitespace. Required internal fields are `source`, `company`, `role`, `location`, `canonical_url` and `date_posted`; the other fields are optional and become empty strings when absent.

| Internal field | Accepted CSV headers |
| --- | --- |
| `source` | `Source`, `Portal`, `Job Portal` |
| `company` | `Company`, `Company Name`, `Employer`, `Employer Name` |
| `role` | `Role`, `Title`, `Job Title`, `Position`, `Position Title` |
| `location` | `Location`, `Job Location`, `City` |
| `canonical_url` | `Canonical URL`, `URL`, `Job URL`, `Job Link`, `Posting URL` |
| `date_posted` | `Date Posted`, `Posted Date`, `Posting Date`, `Date` |
| `work_mode` | `Work Mode`, `Workplace Type` |
| `employment_type` | `Employment Type`, `Job Type` |
| `external_job_id` | `External Job ID`, `Job ID`, `Requisition ID` |

Supported source-label normalization is: `LinkedIn`/`LinkedIn Jobs` → `linkedin`; `OCC Mundial`/`OCC.com.mx` → `occ_mundial`; `Computrabajo` → `computrabajo`; `Hireline` → `hireline`; `Get on Board` → `get_on_board`; `We Work Remotely` → `we_work_remotely`; `Upwork` → `upwork`; `Behance` → `behance`; `The Ladders` → `the_ladders`; `Official Company Sites` → `official_company_sites`; and `Official ATS` → `official_ats`. Any other source label becomes lowercase snake case (spaces become `_`) and must exactly match a portal selected in the private rules; otherwise the normal source-selection validation discards it. No source label authorizes a query or claims vendor-format support.

```bash
python3 "$SKILL_DIR/scripts/vacancy_discovery.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --rules "$WORKSPACE/rules.yaml" \
  --import-file "$WORKSPACE/private-export.json" \
  --output "$WORKSPACE/private-shortlist.json" \
  --as-of 2026-09-07
```

The report preserves the declared role, seniority, industry, geography, work-mode and employment-type context for later evaluation. It does not infer a fit verdict and must remain in the private workspace.

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
