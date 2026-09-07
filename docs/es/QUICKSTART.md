# Inicio rápido

Versión original en inglés: [docs/QUICKSTART.md](../QUICKSTART.md).

## Instala

```bash
hermes profile install ricardo588/career-copilot --name my-career-copilot --alias
hermes -p my-career-copilot setup
```

## Inicializa el estado privado

```bash
SKILL_DIR="$HOME/.hermes/profiles/my-career-copilot/skills/career-copilot"
WORKSPACE="$HOME/Documents/CareerCopilot"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" start
```

La finalización también crea o conserva el banco privado `stories.jsonl`. Para inspeccionar evidencia reutilizable y confirmada sin escribir:

```bash
python3 "$SKILL_DIR/scripts/story_bank.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --stories "$WORKSPACE/stories.jsonl" \
  --mode interview
```

## Ejecuta el onboarding conversacional

```bash
hermes -p my-career-copilot chat -s career-copilot
```

Pídele a Career Copilot que continúe el onboarding. Debe:

1. Leer el estado del onboarding.
2. Preguntar si el usuario ya tiene un CV.
3. Si lo tiene, leerlo localmente y pedir al usuario que confirme o corrija la propuesta extraída.
4. Hacer una fase a la vez solo para la información y permisos faltantes.
5. Preguntar por empresas objetivo opcionales y, cuando ya se conozcan la familia de puesto, seniority, industria, geografía elegible, modalidad y tipo de empleo, mostrar sugerencias transparentes de cobertura de portales para que la persona elija, ajuste u omita.
6. Cuando la persona proporcione explícitamente una exportación privada de vacantes, crear un shortlist de sólo lectura; no consultar un portal, escribir el tracker, postular ni contactar a nadie.
7. Guardar cada respuesta confirmada en el punto de control privado.
8. Reportar los campos obligatorios faltantes sin repetir valores sensibles.
9. Finalizar solo cuando los campos obligatorios estén completos.

## Importa una exportación privada de vacantes (sólo lectura)

Si la persona proporciona explícitamente una exportación JSON privada desde un portal seleccionado, crea un shortlist sin contactar al portal ni cambiar el tracker:

```bash
python3 "$SKILL_DIR/scripts/vacancy_discovery.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --rules "$WORKSPACE/rules.yaml" \
  --import-file "$WORKSPACE/exportacion-privada.json" \
  --output "$WORKSPACE/shortlist-privado.json" \
  --as-of 2026-09-07
```

El reporte conserva el contexto declarado de puesto, seniority, industria, geografía, modalidad y tipo de empleo para la evaluación posterior. No infiere un veredicto de encaje y debe mantenerse dentro del workspace privado.

## Ejecuta la demo sintética segura

```bash
DEMO_DIR="$(mktemp -d)/career-copilot-demo"
python3 "$SKILL_DIR/scripts/run_synthetic_demo.py" --output-dir "$DEMO_DIR"
```

Resultado esperado:

- recomendación `High`;
- una fila de tracker deduplicada;
- un brief de entrevista;
- cero acciones externas.

## Primer flujo real

Cuando el onboarding esté completo, pregunta:

> Evalúa esta vacante contra mi perfil privado. Separa hechos confirmados, interpretación de encaje, brechas y siguiente acción. No postules ni contactes a nadie.

Consulta [PRIVACY.md](PRIVACY.md) antes de habilitar integraciones.
