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

Si la persona proporciona explícitamente una exportación JSON o CSV privada desde un portal seleccionado, crea un shortlist sin contactar al portal ni cambiar el tracker. El soporte CSV es un contrato local completo y versionado de mapeo, no una afirmación de que sea compatible con el formato de exportación de algún proveedor.

### Contrato CSV compatible

Los siguientes encabezados sin distinción entre mayúsculas/minúsculas se normalizan reemplazando `_` y `-` por espacios y colapsando espacios repetidos. Los campos internos obligatorios son `source`, `company`, `role`, `location`, `canonical_url` y `date_posted`; los demás son opcionales y quedan como cadenas vacías si no existen.

| Campo interno | Encabezados CSV aceptados |
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

La normalización de etiquetas de fuente compatible es: `LinkedIn`/`LinkedIn Jobs` → `linkedin`; `OCC Mundial`/`OCC.com.mx` → `occ_mundial`; `Computrabajo` → `computrabajo`; `Hireline` → `hireline`; `Get on Board` → `get_on_board`; `We Work Remotely` → `we_work_remotely`; `Upwork` → `upwork`; `Behance` → `behance`; `The Ladders` → `the_ladders`; `Official Company Sites` → `official_company_sites`; y `Official ATS` → `official_ats`. Cualquier otra etiqueta de fuente se convierte a snake case en minúsculas (los espacios se vuelven `_`) y debe coincidir exactamente con un portal seleccionado en las reglas privadas; de otro modo, la validación normal de fuente seleccionada la descarta. Ninguna etiqueta de fuente autoriza una consulta ni afirma compatibilidad con formatos de proveedores.

```bash
python3 "$SKILL_DIR/scripts/vacancy_discovery.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --rules "$WORKSPACE/rules.yaml" \
  --import-file "$WORKSPACE/exportacion-privada.json" \
  --output "$WORKSPACE/shortlist-privado.json" \
  --as-of 2026-09-07
```

El reporte conserva el contexto declarado de puesto, seniority, industria, geografía, modalidad y tipo de empleo para la evaluación posterior. No infiere un veredicto de encaje y debe mantenerse dentro del workspace privado.

## Adquiere un feed ATS público explícito (sólo lectura)

Greenhouse Job Board y Lever Postings son los dos adaptadores públicos JSON específicos compatibles. Se ejecutan únicamente cuando invocas explícitamente el comando con un identificador board/site y etiqueta de empresa confirmados por la persona candidata; no buscan en proveedores, aceptan credenciales, postulan, contactan personas ni cambian un tracker.

```bash
python3 "$SKILL_DIR/scripts/vacancy_acquisition.py" \
  --adapter greenhouse_public_board \
  --source-identifier '<BOARD_TOKEN_CONFIRMADO>' \
  --company '<ETIQUETA_EMPRESA_CONFIRMADA>' \
  --as-of <YYYY-MM-DD> \
  --output "$WORKSPACE/adquisicion-privada.json"
```

El reporte usa la misma forma `vacancies` de la ruta de importación privada. Greenhouse entrega `source_updated_on` (momento de actualización del proveedor), que el shortlist etiqueta como base de frescura; no es una afirmación de fecha de publicación. Selecciona `greenhouse_public_board` o `lever_public_postings` en las reglas privadas antes de importarlo a un shortlist. Lee [el contrato de adquisición y acciones](../../skills/career-copilot/references/acquisition-and-actions.es.md) antes de usarlo.

Audita la frescura del catálogo localmente sin abrir URLs de fuente:

```bash
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" \
  catalog-audit --as-of <YYYY-MM-DD> --max-age-days 90
```

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
