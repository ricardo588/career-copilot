# Demo sintética de extremo a extremo

Versión original en inglés: [docs/DEMO.md](../DEMO.md).

El escenario incluido demuestra el flujo local sin usar un candidato, empleador, cuenta o vacante reales.

## Flujo

1. Carga un perfil de candidato sintético y reglas.
2. Carga una vacante abierta sintética desde una URL reservada `.test`.
3. Evalúa título, seniority, elegibilidad, frescura y solapamiento de evidencia.
4. Carga un Human Path sintético con fuente, reclutador y responsable de contratación.
5. Crea una fila canónica de tracker con relojes independientes de verificación de vacante y Human Path.
6. Vuelve a ejecutar de forma segura sin crear un duplicado.
7. Carga hechos del entrevistador con fuente y hipótesis etiquetadas explícitamente.
8. Genera un brief de entrevista usando solo evidencia declarada.
9. Agrega una siguiente acción sintética y deriva una señal `follow_up_overdue` de solo lectura sin cambiar el estado del tracker durante la revisión.
10. Renderiza un brief sintético de negociación de oferta con comparación de paquete fechada en la fuente y lenguaje de solo borrador.
11. Registra que ocurrieron cero acciones externas.

## Ejecutar

Desde un perfil instalado:

```bash
SKILL_DIR="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot"
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 "$SKILL_DIR/scripts/run_synthetic_demo.py" --output-dir "$OUTPUT_DIR"
```

Desde el repositorio fuente:

```bash
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir "$OUTPUT_DIR"
```

Artefactos generados:

- `demo-result.json`
- `tracker.csv`
- `tracker-review.json`
- `interview-brief.md`
- `offer-negotiation.md`

Ejecuta por separado los modos de preparación relacional y de debrief de entrevista, ambos de solo lectura (sus salidas deben quedar fuera del repositorio):

```bash
python3 skills/career-copilot/scripts/pipeline.py \
  --relationship-prep skills/career-copilot/examples/synthetic/relationship-meeting.json \
  --relationship-prep-md "$OUTPUT_DIR/relationship-prep.md"

python3 skills/career-copilot/scripts/pipeline.py \
  --interview-debrief skills/career-copilot/examples/synthetic/interview-debrief.json \
  --interview-debrief-md "$OUTPUT_DIR/interview-debrief.md"
```

## Criterios de aprobación

- `evaluation.recommendation` es `High`.
- Exactamente tres requisitos están respaldados por una superposición de evidencia significativa.
- El requisito comercial de gestión no relacionado no se marca como respaldado.
- `tracker_rows` es `1`.
- `human_path.status` es `confirmed`.
- `vacancy_last_verified` coincide con la fecha fija de evaluación.
- `human_path_last_verified` coincide con `retrieved_at` validado del artefacto de Human Path.
- `external_actions` es `0`.
- `tracker_review.read_only` es `true` y exactamente un elemento es `follow_up_overdue`.
- El estado persistido del tracker permanece en `applied`; la revisión no lo muta.
- Los atributos protegidos y sus proxies de nombre/foto/fecha quedan excluidos del fit scoring.
- El brief de entrevista contiene Human Path, inteligencia sobre entrevistadores y el guardrail de evidencia.

La fecha fija de evaluación por defecto es `2026-08-26`, lo que hace reproducible la prueba.
