# Planeación semanal de campaña privada

Genera una vista **read-only** para una semana. No aplica, envía, contacta ni cambia el tracker. Separa trabajo planeado, borradores, acciones autorizadas, intentos y resultados verificados.

## Entradas privadas

- `tracker.csv`: la revisión de vencidos usa la semántica neutral de `pipeline.py --review-tracker`.
- `targets.json`: el registro creado con `scripts/target_companies.py`.
- `weekly-context.json`: foco y registros explícitos de actividad.

Ejemplo de contexto:

```json
{
  "focus": ["Priorizar oportunidades Director con evidencia vigente"],
  "drafts": [{"id": "draft-1", "kind": "follow_up", "opportunity_id": "job-1", "status": "draft"}],
  "authorized_actions": [{"id": "auth-1", "kind": "research", "scope": "market signals", "authorized_at": "2026-09-07"}],
  "attempts": [{"id": "attempt-1", "action_id": "auth-1", "attempted_at": "2026-09-08", "result": "blocked"}],
  "outcomes": [{"id": "outcome-1", "subject": "job-1", "state": "verified", "evidence_ref": "evidence/gmail-evidence.jsonl#opaque-id"}],
  "learning": [{"observation": "Interviews clustered in cloud delivery", "interpretation": "candidate reflection", "next_experiment": "review case preparation"}]
}
```

Un `outcome` con estado `verified` requiere `evidence_ref`. `authorized_actions` no puede ser enviar, aplicar, contactar, publicar ni mutar un status.

## Ejecución

```bash
python3 scripts/weekly_campaign.py \
  --tracker "$WORKSPACE/tracker.csv" \
  --targets "$WORKSPACE/targets.json" \
  --context "$WORKSPACE/weekly-context.json" \
  --week-start 2026-09-07 \
  --output "$WORKSPACE/reviews/week-2026-09-07.json"
```

El reporte separa:

- `activity`: acciones autorizadas e intentos; no impone cuota universal.
- `outputs`: borradores, no acciones enviadas.
- `outcomes`: únicamente lo que fue verificado y referenciado.
- `learning`: observación, interpretación y siguiente experimento del candidato.
- `actionable_items`: follow-ups vencidos derivados y próximos pasos de investigación explícitos.
- `passive_waiting`: procesos en espera sin crear trabajo artificial.
- `research_gaps`: frescura de evidencia de empresa y Human Path en relojes separados.

Los escenarios sintéticos de bajo y mayor volumen tienen la misma semántica; el volumen no crea metas ni fuerza cada oportunidad a recorrer todas las etapas.
