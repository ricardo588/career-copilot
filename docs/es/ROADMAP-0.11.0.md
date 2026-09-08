# Career Copilot 0.11.0 — Alcance integrado de adquisición segura

Versión original en inglés: [docs/ROADMAP-0.11.0.md](../ROADMAP-0.11.0.md).

## Estado

**Objetivo de release:** v0.11.0 integra el alcance diferido de discovery, formatos de fuente, refresco de evidencia y planeación de acciones, preservando propiedad privada y autorización explícita. Se vuelve una versión publicada sólo al crear su tag de release.

## Comportamiento entregado

1. **Adquisición directa de sólo lectura:** una persona operadora puede invocar exactamente un `GET` público de Greenhouse Job Board o Lever Postings usando un identificador board/site confirmado por la persona candidata. Esta ruta no tiene credenciales, búsqueda, automatización de navegador, scraping, endpoint de postulación ni mutación.
2. **Normalizadores específicos por fuente:** los campos JSON documentados de Greenhouse y Lever se normalizan al contrato existente de vacante privada. `updated_at` de Greenhouse se conserva como `source_updated_on`, no se afirma como fecha de publicación; el shortlist etiqueta esa base de frescura explícitamente. El reporte sigue sujeto a las validaciones de fuente seleccionada, frescura e identidad canónica antes del shortlist.
3. **Gobernanza de evidencia refrescable:** `onboarding.py catalog-audit` revisa los metadatos URL/fecha/scope del catálogo local contra una fecha de revisión explícita y reporta entradas que requieren comprobación humana. No hace una petición de red.
4. **Alcance de acciones externas:** los planes deterministas para postulación, mensaje, contacto y escritura de tracker siempre son borradores. El hash de aprobación vincula destino y payload, pero no pueden ejecutar. Los ejecutores existentes de Sheets/Obsidian preservan contratos separados de `confirm_each_external`, lectura vigente y readback.
5. **Investigación de empresas target:** el registro privado existente sigue siendo la ruta de empresa target respaldada con evidencia; la preferencia de la persona, señales vigentes, frescura de Human Path y autorización de contacto permanecen separadas.

## Límites de seguridad

- La adquisición directa es sólo una lectura pública explícita iniciada mediante CLI. No se ejecuta durante onboarding, status, auditoría de catálogo, importación, evaluación ni demo.
- Ningún código de este alcance postula, envía mensajes, contacta personas, modifica perfiles públicos ni escribe un tracker.
- El producto nunca coloca credenciales, identificadores board/site, URLs elegidas por una persona, reportes de adquisición ni planes privados de acciones en el repositorio distribuible.
- Una auditoría de catálogo identifica evidencia desactualizada; nunca trata una fuente antigua como afirmación de disponibilidad actual.

## Actualización

No se requiere migración de datos privados. Las importaciones CSV/JSON, checkpoints de onboarding y consumidores de salida existentes siguen siendo compatibles. El nuevo campo de catálogo `evidence_checked_on` es aditivo. El reporte de adquisición directa usa la misma forma de payload `vacancies` que la ruta de importación existente.

## Verificación

Ejecuta pruebas focalizadas de adquisición/onboarding, la suite completa, validación de bundle y privacidad, revisiones de diff y la demo sintética. La demo inyecta una respuesta Greenhouse en memoria y reporta `network_executed: false`; no contacta a un proveedor.

## Regla para extensiones restantes

Agregar otro proveedor requiere contrato público verificado por separado, normalizador con fixtures, allowlist de URL de fuente, documentación EN/ES pareada y el mismo límite de lectura explícita/sin mutación. Agregar un ejecutor para cualquier acción requiere autorización específica del proveedor, lectura vigente del destino, hash exacto de aprobación, auditoría privada y readback verificado; no puede inferirse desde un plan.
