# Adquisición pública explícita y borradores de acciones

## Límite

`vacancy_acquisition.py` admite únicamente dos feeds ATS públicos, explícitos y sólo-GET:

- `greenhouse_public_board` — `https://boards-api.greenhouse.io/v1/boards/<board-token>/jobs`
- `lever_public_postings` — `https://api.lever.co/v0/postings/<site>?mode=json`

La persona candidata u operadora proporciona el identificador board/site y la etiqueta de empresa para una petición. Los identificadores sólo aceptan letras, dígitos, `_` y `-`; Career Copilot nunca descubre identificadores, busca entre empresas, autentica, usa automatización de navegador, extrae páginas renderizadas, sigue URLs de postulación ni envía una postulación.

Ambos normalizadores producen la forma documentada de importación privada (`source`, `company`, `role`, `location`, `canonical_url`, `work_mode`, `employment_type`, `external_job_id`) más una base de frescura fechada. Antes de escribir un reporte, Greenhouse acepta únicamente páginas hosted HTTPS con la forma `boards.greenhouse.io/<board>/jobs/<id>`; Lever acepta únicamente páginas hosted HTTPS con la forma `jobs.lever.co/<site>/<posting-id>` o `jobs.eu.lever.co/<site>/<posting-id>`. Rechaza otros esquemas, hosts, rutas malformadas y URLs de postulación. El normalizador Greenhouse conserva `updated_at` del proveedor como `source_updated_on`, nunca como fecha de publicación; el de Lever mapea `createdAt` a `date_posted` y nunca conserva `applyUrl`. La salida es un reporte privado de adquisición, no un encaje verificado, fila de tracker ni autorización de postulación. Impórtalo sólo después de seleccionar la fuente en las reglas privadas y aplicar la validación normal de frescura/URL canónica.

## Ejecuta una lectura explícita

```bash
python3 ${HERMES_SKILL_DIR}/scripts/vacancy_acquisition.py \
  --adapter greenhouse_public_board \
  --source-identifier <board-token-confirmado-por-la-persona> \
  --company '<etiqueta-de-empresa-confirmada-por-la-persona>' \
  --as-of <YYYY-MM-DD> \
  --output <adquisicion-privada.json>
```

El comando realiza un solo `GET` saliente únicamente cuando se invoca. No recibe credenciales, no tiene endpoint de escritura ni ruta de postulación. Mantén identificadores y salida en el workspace privado, fuera de Git.

## Auditoría de frescura del catálogo

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <workspace-privado> catalog-audit \
  --as-of <YYYY-MM-DD> --max-age-days 90
```

La auditoría valida cada URL/fecha/scope de evidencia local y devuelve las entradas que requieren revisión humana. No abre URLs ni refresca afirmaciones. Una persona debe volver a revisar una fuente oficial antes de cambiar fecha o alcance.

## Acciones externas

`propose_external_action()` crea un plan determinista para `tracker_write`, `application`, `message` o `contact`. Un plan siempre es `draft_only` y tiene `external_actions: 0`; su hash vincula acción, destino y payload. No tiene ejecutor.

Los ejecutores opcionales existentes para Google Sheets y Obsidian local siguen separados. Requieren workspace privado, `confirm_each_external`, hash exacto revisado, lectura vigente del destino y readback verificado. Gmail se limita a triage de un mensaje explícito y marcar como leído; Career Copilot no tiene ejecutor para enviar mensajes, postular ni contactar. Un registro de investigación de empresa target o Human Path nunca concede autorización de contacto.

## Fuentes

- Greenhouse Job Board API: https://docs.greenhouse.io/job-board.html
- Lever Postings API: https://github.com/lever/postings-api
