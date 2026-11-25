# Career Copilot 0.14.0 — Evidencia privada de conexiones LinkedIn

English version: [docs/ROADMAP-0.14.0.md](../ROADMAP-0.14.0.md).

## Objetivo

Agregar un importador determinista y local de una exportación explícita de **conexiones** de LinkedIn que produzca pistas conservadoras de descubrimiento para Human Path. Nunca debe afirmar empleo actual, identidad exacta, fuerza de relación, capacidad de referido ni autorización de contacto.

## Arquitectura de seguridad

El importador es estrictamente **read-only**:

- Acepta un workspace privado y inputs de export/vacante dentro de ese workspace.
- Abre inputs relativos a descriptor con `O_NOFOLLOW`, rechaza symlinks, workspaces Git y archivos no regulares, y continúa desde los descriptores de directorio abiertos originalmente si luego cambia un ancestro por pathname.
- No realiza red, navegador, API, login, cookies, credenciales, procesos ni acciones externas.
- Emite el artefacto de revisión sólo a stdout. No tiene `--output` ni realiza escritura de filesystem. Un host que decida persistir stdout es dueño de esa frontera separada de escritura.

Esto elimina deliberadamente del modelo de seguridad del importador la carrera previa de publicación de outputs.

## Contrato de evidencia

Cada resultado candidato mantiene estados independientes:

- `discovery_state: export_match_found`
- `identity_state: needs_identity_review`
- `current_employment: unverified`
- el campo de autorización siempre tiene el valor `not_granted`

Un match textual nunca confirma identidad. Los matches sólo por empresa y los duplicados textuales son ambigüedades para revisión manual. No se muta tracker, story bank, Sheets, Obsidian, correo, calendario ni registros de Human Path.

## Gates de aceptación

- Sólo se aceptan headers CSV UTF-8 documentados; headers duplicados o no soportados fallan cerrados.
- Todos los fixtures son sintéticos; ningún export, contacto, identificador o URL de perfil reales entra al repositorio.
- Las pruebas parchean socket y lanzamiento de procesos y comprueban cero intentos.
- Hay regresiones para paths fuera del workspace, workspaces Git, symlinks, CSV malformado, ambigüedad e inmutabilidad de inputs.
- Antes del release pasan bundle validation, suite completa, privacy scan y auditoría independiente de seguridad.
