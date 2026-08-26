# Synthetic end-to-end verification

Run:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/run_synthetic_demo.py --output-dir <TEMPORARY_DIRECTORY>
```

The scenario uses only bundled synthetic JSON and a reserved `.test` URL. It must generate:

- `demo-result.json`;
- one-row `tracker.csv`;
- `interview-brief.md`;
- recommendation `High`;
- exactly three meaningfully supported requirements;
- zero external actions.

Re-evaluating/tracking the same vacancy must update the existing row rather than add a duplicate.

Do not replace the synthetic fixtures with real candidate, employer, vacancy or account data.
