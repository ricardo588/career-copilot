# Career Copilot 0.9 — Proyección opcional a Kanban de Obsidian

Versión original en inglés: [docs/ROADMAP-0.9.md](../ROADMAP-0.9.md).

## Estado

**Entregada en v0.9.0.** v0.9 extiende la frontera de proyección privada, atómica y Markdown de Obsidian entregada en v0.8 con una proyección opcional y local de tarjetas a Kanban de Obsidian. No crea proveedores remotos, escaneos de vaults, sincronización ni acciones automáticas. El contrato detallado de seguridad siguiente se conserva como frontera de la versión; el endurecimiento posterior al comando implementado para un tablero queda diferido y no se infiere.

## Objetivo

Permitir que una persona renderice opcionalmente un artefacto de Career Copilot seleccionado de forma explícita y ya revisado en un único **tablero Kanban privado de Obsidian**, dentro de su flujo existente de Obsidian.

El tablero es una vista local y revisable; no es autoridad del tracker, sistema de sincronización ni fuente de decisiones automáticas. El formato exacto debe configurarse de forma privada y ser compatible con el proceso Kanban de Obsidian que la persona ya utiliza. La distribución pública no contiene un tablero, ruta de vault, nombre de tablero ni contenido de candidato.

## Decisiones de producto

1. **Sólo Obsidian.** v0.9 no agrega proveedor Kanban remoto, credenciales, integración API ni actividad de red. Opera únicamente a través de la frontera actual de vault local de Obsidian.
2. **Opcional, un tablero a la vez.** La persona selecciona explícitamente un vault privado configurado y una ruta Markdown relativa del tablero. La instalación no crea, escanea, migra ni actualiza tableros.
3. **Render unidireccional.** Career Copilot renderiza un artefacto local revisado como tarjeta o sección Kanban. Nunca importa, analiza, reconcilia ni toma contenido Kanban como datos canónicos del tracker.
4. **Gramática del plugin fijada.** El renderer apunta a la gramática Markdown pública de [Obsidian Kanban](https://github.com/community-archive/obsidian-kanban), verificada contra la revisión `main` `5134c05`. Una configuración privada selecciona sólo ruta relativa permitida, claves de lane y marcadores de tarjeta controlados; no puede redefinir ni adivinar la gramática. Si falta, es inválida, ambigua o incompatible, bloquea en lugar de sobrescribir un tablero.
5. **Dry-run primero.** La salida por defecto contiene cambio Markdown determinista, ruta relativa de destino, fingerprint del contenido vigente y `approval_sha256`; no escribe. `--apply` exige perfil privado `confirm_each_external`, workspace privado, hash revisado exacto, prelectura vigente, escritura atómica y readback exacto.
6. **Reusar el guard de vault de v0.8.** Se siguen rechazando vaults que sean symlinks o residan en la distribución o un repositorio Git. La escritura sigue siendo local, pero requiere la misma frontera de ruta privada, auditoría y readback de v0.8.
7. **Contenido mínimo necesario.** Una tarjeta renderizada contiene sólo resumen revisado seleccionado por la persona, campos explícitamente permitidos y referencias locales opacas de procedencia. Cuerpos Gmail, credenciales, datos de candidato fuera del payload revisado, rutas absolutas y artefactos crudos nunca entran a archivos del repositorio, logs públicos ni fixtures sintéticos.

## No objetivos

- No servicio Kanban remoto, selección de proveedor, OAuth/API key, webhooks, polling ni sincronización.
- No creación automática de tareas, workers en segundo plano, trabajos recurrentes, schedules, triage de inbox completo, generación masiva ni descubrimiento de tableros.
- No importación, reconciliación inversa, resolución automática de identidad ni update del tracker a partir del contenido del tablero.
- No transacción multisuperficie con Gmail, Sheets, CSV u otra nota Obsidian.
- No envío de solicitudes, outreach, enviar/responder/reenviar/crear borrador/archivar/etiquetar/borrar correo ni acción pública.
- Política de plan de fuentes, schedules/blueprints opt-in, dossier de entrevistas ampliado y PDF móvil siguen diferidos; no se incorporan a v0.9.

## Arquitectura y contrato de seguridad

### 1. Renderer puro de tablero

Agregar un renderer sin dependencias que acepte sólo entradas normalizadas:

- artefacto local revisado y referencias opacas de procedencia;
- descriptor o versión de plantilla privada del formato de tablero;
- ruta Markdown relativa explícita del tablero;
- clave explícita de columna o lane; y
- contenido vigente del tablero cuando un update aprobado apunte a un tablero existente.

Devuelve exactamente un resultado determinista:

- `create_board_plan`;
- `append_card_plan`;
- `update_card_plan`;
- `no_change`;
- `duplicate_projection`;
- `ambiguous_target`;
- `integrity_failure`; o
- `policy_blocked`.

El renderer no depende de mutaciones de filesystem ni red. Procedencia faltante, formato de tablero malformado/no admitido, identidad ambigua de lane/tarjeta, ruta relativa insegura, ledger corrupto o contenido vigente incompatible bloquean; no existe fallback de mejor esfuerzo.

### 2. Gramática fijada del tablero y región controlada

El renderer admite sólo la gramática de tablero respaldada por Markdown del plugin. Su fixture sintético y salida deben usar:

```markdown
---
kanban-plugin: board
---

## <configured lane heading>

- [ ] <reviewed card text> ^<opaque-card-marker>

%% kanban:settings
```

El código fuente del plugin define el frontmatter `kanban-plugin`, renderiza cada encabezado `##` como lane y representa tarjetas como elementos de lista Markdown; su escritor canónico también emite un bloque final `%% kanban:settings`. Un archivo es un corte temático `***` seguido por un encabezado `## Archive`. v0.9 no crea, mueve, completa, archiva ni analiza esa región de archivo.

La configuración privada puede definir sólo claves/encabezados de lane permitidos, marcador opaco estable de tarjeta, campos/orden permitidos y límite de render exacto. La implementación modifica únicamente ese límite. Si frontmatter/settings del plugin faltan o son inconsistentes, un encabezado de lane falta o se repite, el marcador controlado falta/se repite/se altera manualmente, o cambiaría contenido fuera del límite configurado, la operación bloquea. Nunca reescribe un vault entero, infiere lane desde texto, convierte silenciosamente otra gramática ni trata una nota que no sea tablero como tablero.

### 3. Aprobación y ciclo de vida de escritura

El dry-run `approval_sha256` liga un plan canónico versionado con:

- hash de identidad canónica del vault y ruta relativa del tablero;
- formato/versión de tablero, clave de lane, límite de render y fingerprint del tablero actual;
- operación, identidad opaca de tarjeta, referencias de artefacto/procedencia revisados y payload Markdown exacto; y
- estado de prelectura esperado.

Para `--apply`, el adaptador debe:

1. rechazar `draft_only` antes de mutar filesystem;
2. requerir hash revisado exacto, perfil privado, workspace privado y `confirm_each_external`;
3. revalidar vault, ruta relativa, configuración de formato y fingerprint actual del tablero;
4. recalcular el plan y bloquear ante hash obsoleto o diferente;
5. escribir atómicamente sólo el cambio Markdown revisado; y
6. leer de vuelta el archivo exacto del tablero y agregar un evento de auditoría mínimo privado sólo tras verificar el contenido esperado.

Un retorno de escritura atómica no es éxito por sí solo. Readback fallido o distinto es falla de integridad, nunca no-op.

### 4. Idempotencia y recuperación

Mantener un ledger privado append-only de proyección, indexado por fingerprint versionado del artefacto revisado, identidad canónica de vault, ruta relativa, formato de tablero, lane y payload exacto de tarjeta. Sólo conserva referencias opacas, hashes y resultados.

- Una proyección previa verificada coincidente produce `duplicate_projection` o `no_change` sin escribir.
- Un fingerprint igual ligado a otra identidad de tablero/tarjeta es colisión y bloquea.
- Ledger corrupto, permisos inseguros, traversal de symlink, escape de ruta, contenido obsoleto de tablero o readback fallido bloquean.
- Un fallo local parcial se audita como falla; la recuperación requiere un nuevo plan revisado desde el contenido vigente.

### 5. Contrato CLI (propuesto)

El nombre puede cambiar durante implementación, pero no el límite:

```text
obsidian-kanban-project \
  --vault <private-vault> \
  --relative-path <board-relative-markdown-path> \
  --board-format-config <private-format-config> \
  --lane <configured-lane-key> \
  --artifact-json <reviewed-local-artifact>
```

Sin `--apply`, emite plan determinista redactado y `approval_sha256`. Para aplicar se repiten exactamente las entradas revisadas y se agrega:

```text
--profile <private-profile.yaml> \
--workspace <private-workspace> \
--approved-plan-sha256 <reviewed-hash> \
--apply
```

No debe ofrecer flags para escanear vault, consultas amplias de tableros, proyección masiva, conversión de formato, sincronización, ejecución automática ni selección de lane basada en contenido.

## Plan de entrega

### Hito A — contrato de formato y renderer puro

- Definir esquema genérico privado de configuración de formato y marcador estricto de límite de render.
- Agregar renderer canónico, hash de plan, contrato de ledger y plantillas genéricas sólo con placeholders.
- Agregar pruebas unitarias de cada decisión, compatibilidad de formato, seguridad de ruta, duplicado/colisión, preservación de límite de render y enlace de hash.

**Criterio de salida:** todas las pruebas del renderer corren sin contenido de candidato, vault real, mutación de filesystem ni red; formato/contenido ambiguo siempre falla cerrado.

### Hito B — adaptador Kanban de Obsidian con gating

- Agregar el comando estrecho `obsidian-kanban-project` junto a la frontera existente de adaptador Obsidian.
- Reusar validación de vault privado, escritura atómica, readback exacto, eventos mínimos de auditoría y protección `draft_only` de v0.8.
- Agregar pruebas con fake/temp vault para dry-run, aprobación obsoleta, vault equivocado, rutas inseguras, marcador de render incorrecto y readback fallido.

**Criterio de salida:** ninguna escritura es alcanzable sin el contrato completo de aprobación revisada, y el adaptador cambia sólo su límite de render configurado.

### Hito C — flujo sintético y hardening de release

- Agregar fixture sintético de formato privado y tablero sintético con referencias opacas únicamente.
- Demostrar resultados create/append/update/no-change locales; conservar `external_actions == 0` en la demo sintética ordinaria porque no hay acción a proveedor externo.
- Actualizar documentación EN/ES de adaptadores; ejecutar gate completo de release, privacy scan, bundle validation, instalación aislada y revisión independiente.

**Criterio de salida:** repositorio y salida de demo no contienen tablero, vault, candidato, Gmail, tracker, credencial ni workspace reales.

## Matriz de pruebas

Debe cubrir:

- resultados create, append, update, no-change, duplicate, destino ambiguo, bloqueo de política y falla de integridad;
- cambios de enlace de aprobación para vault, ruta relativa, formato, límite de render, lane, artefacto, procedencia, payload y fingerprint actual;
- perfil/workspace/hash ausente o inválido, `draft_only`, plan obsoleto, rutas inseguras, symlinks, vaults Git/distribución, ledger corrupto y colisiones;
- marcadores faltantes/repetidos/modificados, formato no admitido, lane diferente, contenido manual inesperado en región controlada, fallo de escritura atómica y readback distinto;
- preservación de todo contenido fuera del límite configurado; y
- documentación bilingüe, ayuda CLI, demo sintética, privacy scan, bundle validation, instalación aislada y suite unitaria completa.

## Impacto de actualización y release

v0.9 no realiza migración en instalación, escaneo de vault, descubrimiento de tableros ni escritura. CSV, Sheets, triage Gmail y proyección Markdown libre de Obsidian de v0.8 continúan compatibles e independientes. Kanban queda deshabilitado hasta que se entregue configuración privada de vault/formato y se invoque el comando explícito.

Este documento no autoriza acceso, copia ni cambio de otro flujo Job Hunter o workspace de candidato. Si después se autoriza smoke test local, debe usar vault de prueba privado y desechable y contenido de tablero sintético.

## Diferido más allá de v0.9

- Proveedores Kanban remotos, sincronización, importaciones, polling, webhooks, schedules recurrentes y proyección masiva.
- Cambios automáticos al tracker, atomicidad entre sistemas e inferencia de hechos desde Kanban.
- Conversión de formato o migración automática de tableros existentes.
- Política de plan de fuentes, schedules/blueprints opt-in, dossier de entrevistas ampliado y PDF móvil.
