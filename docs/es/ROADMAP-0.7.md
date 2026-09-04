# Career Copilot 0.7 — Diseño de Operational Tracker

English version: [docs/ROADMAP-0.7.md](../ROADMAP-0.7.md).

## Estado

**Alcance aprobado:** reconciliación de tracker y política de compensación.

Este documento es un plan de diseño y entrega, no una promesa de implementación automática. La versión 0.7 debe preservar el límite privacy-first de Career Copilot y su política predeterminada `draft_only`.

## Objetivo

Hacer que la integración opcional de Google Sheets sea suficientemente segura para un flujo real de búsqueda de empleo, sin incluir datos del candidato, credenciales, el esquema exacto de un tracker ni políticas personales dentro de la distribución.

La versión agrega reconciliación determinista entre un registro y un backend Google Sheets configurado, además de una política de compensación ejecutable. No automatiza postulaciones, mensajes, outreach, ni trabajo externo recurrente.

## Fuera de alcance

- No enviar aplicaciones, mensajes, contacto con reclutadores, acciones públicas ni login en bolsas de trabajo.
- No instalar cron jobs recurrentes; cualquier agenda futura será explícitamente opt-in.
- No hardcodear salarios, empresas objetivo, estatus, contactos, IDs de Sheet o datos de candidatos.
- No requerir Google Sheets para usuarios que prefieran tracker CSV local.
- No hacer transacciones multi-superficie con Obsidian/Kanban en 0.7.

## Decisiones aprobadas

1. **Backend:** Google Sheets será un backend operacional opcional; el CSV local continúa soportado.
2. **Alcance:** v0.7 cubre reconciliación de tracker y compensación. Inbox, Obsidian/Kanban y schedules quedan después.
3. **Configuración:** estatus, prioridades, IDs de negocio, gates de networking y compensación son datos privados del perfil, nunca defaults personales en el repo.
4. **Seguridad:** `draft_only` sigue siendo el default. Toda escritura en Google requiere `confirm_each_external`, plan revisado y readback exacto.
5. **Release:** publicar como `0.7.0` con guía de upgrade y verificación en perfil desechable.

## Arquitectura propuesta

### 1. Núcleo puro de reconciliación

Crear un módulo determinista sin red, `gws`, credenciales ni mutaciones. Recibe snapshot normalizado de la hoja, mapeo privado de columnas, registro deseado e identidad estable opcional (`external_job_id`, URL canónica, empresa, rol).

Devuelve sólo uno de:

- `create_plan`
- `update_plan`
- `duplicate_match`
- `ambiguous_identity`
- `integrity_failure`
- `no_change`

Resuelve identidad en este orden:

1. ID externo/requisición exacta;
2. URL canónica sin parámetros de tracking;
3. empresa normalizada + rol casi idéntico, siempre requiriendo revisión humana antes de fusionar.

Una fila física nunca será la identidad de negocio.

### 2. Adaptador de esquema de Sheet

Un mapeo privado de ejemplo:

```yaml
tracker:
  backend: google_sheets
  canonical_source: sheet
  sheet:
    spreadsheet_id_env: CAREER_COPILOT_SHEET_ID
    worksheet: Applications
    header_range: Applications!A1:Z1
    data_range: Applications!A2:Z
  fields:
    business_id: No
    company: Company
    role: Role
    status: Status
    priority: Priority
    canonical_url: Canonical URL
    external_job_id: External Job ID
    notes: Notes
  integrity:
    require_contiguous_business_ids: false
    reject_duplicate_business_ids: true
```

El flujo será: lectura → auditoría → plan dry-run con valores anteriores/nuevos → confirmación explícita → escritura mínima de rangos → readback de cada rango → auditoría privada mínima.

### 3. Integridad de IDs de negocio

Con contigüidad activada, el motor debe reportar conteo, máximo, faltantes, duplicados, filas vecinas y si el cambio es seguro/bloqueado/ambiguo.

Un faltante o duplicado no autoriza renumerar. v0.7 puede detectar y bloquear anomalías; la reconstrucción automatizada de registros desplazados queda diferida hasta contar con contrato y fixtures suficientes.

### 4. Política de compensación

Extender el perfil privado con políticas estructuradas por tipo de empleo, moneda y periodicidad. El evaluador debe retornar: `not_configured`, `unknown`, `compatible`, `below_floor` o `exception_required`.

Reglas clave:

- sueldo base y paquete total son campos diferentes;
- monto no publicado es `unknown`;
- bajo piso puede proponer retiro/descartar, nunca escribirlo sin permiso y verificación;
- rechazo de empleador y retiro por presupuesto son causas terminales distintas;
- conversión de moneda queda fuera de alcance sin una fuente fechada explícita.

### 5. Estatus y prioridades configurables

No se hardcodeará un pipeline personal. El perfil puede definir estatus válidos, terminales, transiciones, requisito de contacto confiable para prioridad alta y fase a partir de la cual se recomienda networking.

## Plan de entrega por milestones

### A — Contrato y núcleo puro

- `scripts/tracker_reconciliation.py`
- `references/google-sheets-tracker-backend.md`
- `templates/tracker-backend.template.yaml`
- `tests/test_tracker_reconciliation.py`

**Salida:** sin dependencia de `gws`; decisiones reproducibles; ambigüedad bloquea el cambio.

### B — Integración Sheets con gate

- Extender `adapters.py` o crear `tracker_backend.py` enfocado.
- Reutilizar `confirm_each_external`, bitácora privada, escrituras acotadas y readback.
- Comando `reconcile` dry-run y ruta `apply` separada.

**Salida:** `draft_only` no puede escribir; toda escritura devuelve readback exacto; no hay reescritura de hoja completa.

### C — Compensación

- Extender template/onboarding y `pipeline.py`.
- Diseñar migración versionada de schema si se agregan campos al tracker.
- Probar nómina, contractor, monto desconocido, bajo piso y excepción.

**Salida:** compensación desconocida nunca cuenta como match; retiro por presupuesto no se confunde con rechazo.

### D — Documentación y release

- Actualizar docs EN/ES, quickstarts, privacidad, adapters y schema de tracker.
- Guía de migración para CSV y Sheets existentes.
- Demo sintética de reconciliación sin credenciales.
- Validación de bundle, tests, demo y perfil Hermes aislado.

## Fixtures obligatorios

1. ID externo duplicado.
2. URL duplicada con tracking removido.
3. Empresa/rol similares que requieren revisión humana.
4. ID de negocio faltante o duplicado.
5. Fila física desplazada sin perder identidad.
6. Columnas vacías o no soportadas.
7. Readback distinto tras escritura.
8. Mutación intentada en `draft_only`.
9. Nómina y contractor bajo piso.
10. Compensación no publicada.
11. Excepción aprobada por candidato.

Todos deben ser sintéticos.

## Seguridad y privacidad

- Credenciales, IDs de Sheet, rutas, mensajes y datos de candidatos permanecen fuera del repo.
- Toda mutación requiere perfil/workspace privados, apply explícito y readback.
- `draft_only` bloquea escrituras aunque exista flag apply.
- La bitácora conserva sólo referencias mínimas y hashes de plan.
- Los artefactos privados mantienen permisos adecuados y se rechazan dentro de Git/distribución.

## Diferido

### v0.8

- Triage Gmail transaccional: evidencia → identidad → reconciliación → marcar leído verificado.
- Proyección opt-in hacia Obsidian/Kanban.
- Ledger idempotente de mensajes procesados.

### v0.9

- Blueprints opt-in de schedules.
- Política de plan de fuentes y reglas de validación.
- Dossiers de entrevista y PDF móvil opcional.

## Gobierno de entrega

Implementar en rama dedicada, commits pequeños, tests con fake runners antes de cualquier smoke test y pruebas reales sólo contra una Sheet de prueba privada. Publicar únicamente después de privacy scan limpio, bundle validation, suite completa, demo sintética e instalación aislada verificada.
