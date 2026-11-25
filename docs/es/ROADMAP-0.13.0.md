# Career Copilot 0.13.0 — Evidencia relacional privada y preparación de entrevistas

English version: [docs/ROADMAP-0.13.0.md](../ROADMAP-0.13.0.md).

## Objetivo

Extender las capacidades existentes de banco privado de historias, brief de entrevista y debrief con captura/confirmación STAR e intake de entrevista. El importador de export de LinkedIn se difirió explícitamente de este release porque su frontera de concurrencia de filesystem privado requiere un diseño separado.

## Alcance confirmado

1. **Export de conexiones de LinkedIn a Human Path:** diferido; `v0.13.0` no incluye input de export de conexiones ni artefacto de Human Path. El importador existente de export de vacantes es una capacidad separada de descubrimiento local de vacantes y no pertenece a esta iniciativa.
2. **Experiencia guiada STAR:** guiar captura y confirmación explícita sobre el story bank existente; no reemplazar su esquema, persistir datos de candidato ni inventar evidencia.
3. **Intake de entrevista:** capturar logística confirmada y gaps de evidencia antes de reutilizar la matriz de requisitos, investigación de entrevistadores y generador de brief existentes.
4. **Debrief:** tratar el debrief read-only existente como entregado; sólo agregar una sugerencia opcional y confirmable de mejorar una historia cuando los hechos del debrief la soporten.

## Límites no negociables

- Sin integración de export de conexiones de LinkedIn, API, scraping, navegador, cookies, login, red ni lanzamiento de procesos.
- Sin mutación de tracker, Sheets, Obsidian, calendario, correo o mensajes.
- Ningún fixture o documento puede contener export de conexiones, contacto, identificador o URL de perfil reales.

## Gates iniciales de aceptación

- Los flujos STAR y de entrevista conservan la separación entre hechos, inferencia, desconocidos y borradores.
- Antes del release pasan la suite sintética completa, validación del bundle, escaneo de privacidad, regresiones de seguridad de rutas y auditoría independiente.
