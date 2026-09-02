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
