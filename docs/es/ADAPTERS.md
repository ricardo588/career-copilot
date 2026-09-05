# Adaptadores opcionales

Versión original en inglés: [docs/ADAPTERS.md](../ADAPTERS.md).

Todos los adaptadores son opcionales, están deshabilitados en la plantilla y siguen la regla dry-run primero. Las credenciales, IDs y rutas del vault permanecen locales.

Define una vez la ruta del adaptador instalado:

```bash
ADAPTER="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot/scripts/adapters.py"
```

## Contrato de seguridad

- Las lecturas pueden ejecutarse cuando el usuario las solicite.
- Las mutaciones muestran un plan salvo que se proporcione explícitamente `--apply`.
- Las mutaciones de Google requieren `--profile <private-profile.yaml>` y se bloquean cuando ese perfil está en `draft_only`.
- Cada mutación hace verificación de lectura posterior.
- El adaptador de Gmail no puede enviar mensajes.
- El adaptador de Sheets solo actualiza un rango explícito.
- El adaptador de Obsidian rechaza rutas fuera del vault configurado.

## Prerrequisito de Google Workspace

Instala y autentica un CLI `gws` compatible siguiendo sus instrucciones oficiales. Mantén su archivo de credenciales fuera del repositorio. Verifica que esté listo con:

```bash
gws --help
```

El adaptador hereda el entorno actual, incluida cualquier variable de entorno del archivo de credenciales que requiera la instalación local de `gws`.

## Google Sheets

Leer:

```bash
python3 "$ADAPTER" sheets-read \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:P10'
```

Reconciliar un registro del tracker (sólo lectura; **no existe la opción
`--apply`**):

```bash
python3 "$ADAPTER" sheets-reconcile \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json '{"business_id":"No","company":"Company","role":"Role","location":"Location","canonical_url":"Canonical URL","external_job_id":"External Job ID","status":"Status","priority":"Priority","notes":"Notes"}' \
  --record-json '{"business_id":"1","company":"Example Company","role":"Program Director","location":"Mexico City","canonical_url":"https://jobs.example.test/1","external_job_id":"SYN-1","status":"identified","priority":"medium","notes":""}'
```

El rango debe iniciar exactamente en la fila del encabezado. El comando lee una
vez, deriva las filas físicas desde ese rango explícito y devuelve un
`create_plan`, `update_plan`, `no_change` o una decisión de bloqueo. Nunca llama
a un endpoint de escritura de Sheets. Consulta la referencia del skill para el
mapeo privado y el contrato de integridad.

### Reconciliar, revisar y aplicar un plan aprobado

`sheets-reconcile-apply` primero funciona como dry run. Devuelve los rangos de
celdas exactos, valores anteriores/nuevos de la reconciliación, auditoría de
integridad y un `approval_sha256`. Revisa esos valores antes de cualquier acción.

```bash
python3 "$ADAPTER" sheets-reconcile-apply \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json "$FIELDS_JSON" \
  --record-json "$RECORD_JSON"
```

Para escribir, repite exactamente los argumentos revisados y agrega `--apply`,
el hash devuelto, un workspace privado y un perfil con modo
`confirm_each_external`:

```bash
python3 "$ADAPTER" sheets-reconcile-apply \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json "$FIELDS_JSON" \
  --record-json "$RECORD_JSON" \
  --approved-plan-sha256 '<HASH_DEL_DRY_RUN_REVISADO>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml" \
  --workspace "$HOME/Documents/CareerCopilot" \
  --apply
```

La llamada con apply vuelve a leer el rango vivo y recalcula el plan. Se bloquea
antes de escribir si el hash del plan actual difiere del hash revisado. Sólo
acepta un rectángulo A1 cerrado con nombre de pestaña, escribe únicamente las
celdas modificadas, vuelve a leer cada celda modificada y agrega eventos mínimos
de auditoría privada. Nunca envía una aplicación ni contacto externo.

El hash de aprobación queda ligado al ID exacto del spreadsheet sin revelar ese
ID en la salida. Un plan coincidente sin cambios devuelve `no_change` y no hace
ninguna mutación externa ni escribe auditoría.

Vista previa de una actualización:

```bash
python3 "$ADAPTER" sheets-update \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A2:B2' \
  --values-json '[["Example Company","Program Director"]]' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml"
```

Aplica solo después de confirmar la hoja, el rango y los valores:

```bash
# Solo `confirm_each_external`: agrega --apply después de la confirmación exacta.
```

El adaptador lee de vuelta el mismo rango y falla si los valores difieren.

## Gmail

Buscar y leer:

```bash
python3 "$ADAPTER" gmail-search --query 'newer_than:7d (recruiter OR application)'
python3 "$ADAPTER" gmail-get --message-id '<MESSAGE_ID>'
```

Vista previa de marcar un mensaje ya atendido como leído:

```bash
python3 "$ADAPTER" gmail-mark-read \
  --message-id '<MESSAGE_ID>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml"
```

En `confirm_each_external`, aplica agregando `--apply` después de la confirmación exacta. En `draft_only`, el adaptador bloquea la mutación. Cuando se aplica, confirma que la etiqueta `UNREAD` no está presente.

Enviar, responder, reenviar y crear borradores están intencionalmente no soportados en esta versión del adaptador. Career Copilot puede preparar texto local de borrador, pero un flujo de trabajo aprobado separado debe encargarse de la transmisión.

## Obsidian

Vista previa de escritura de una nota:

```bash
python3 "$ADAPTER" obsidian-write \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --relative-path 'CareerCopilot/Interview Brief.md' \
  --content-file '/path/to/local/interview-brief.md'
```

Aplica agregando `--apply`. El adaptador escribe de forma atómica y lee de vuelta la nota exacta.

## Pruebas sin cuentas

`tests/test_adapters.py` usa runners de comando falsos para Google y un vault local temporal para Obsidian. CI nunca necesita credenciales de cuenta.
