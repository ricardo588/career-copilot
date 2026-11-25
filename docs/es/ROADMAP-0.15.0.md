# Career Copilot 0.15.0 — Distribución como skill comunitario

English version: [docs/ROADMAP-0.15.0.md](../ROADMAP-0.15.0.md).

## Objetivo

Hacer explícita, portable y revisable la ruta pública de skill comunitario de Career Copilot junto con su distribución completa de perfil Hermes. Este es un release de distribución y documentación: no cambia el manejo de datos de candidato, la capacidad de ejecución ni la política de acciones externas.

## Alcance entregado

- El frontmatter del skill portable `career-copilot` declara la misma licencia Apache-2.0 que el repositorio y `skills.sh.json`.
- La documentación en inglés y español distingue la instalación de skill comunitario de la ruta completa de perfil Hermes.
- Ambas rutas declaran el límite de workspace privado, el valor inicial `draft_only` y los requisitos de autorización para adaptadores opcionales.
- La documentación proporciona el identificador exacto del skill comunitario y una lista de verificación para indexación futura.

## Límites no negociables

- Ningún workspace, CV, contacto, tracker, credencial, sesión u otro dato privado de candidato se incluye en el repositorio o distribución.
- Este release no agrega plugin, ficha oficial de Marketplace, listado automático de directorio, feature de telemetría, capacidad de red ni acción externa.
- El proveedor del directorio controla el indexado y el tiempo de búsqueda. `skills.sh.json` aporta metadata de categoría sólo cuando el proveedor indexa el repositorio; no es una afirmación de listado o respaldo.
- La distribución de perfil sigue siendo un adaptador Hermes opcional; la ruta de skill comunitario no la instala silenciosamente.

## Gates de release

- `python3 -m json.tool skills.sh.json`
- `python3 scripts/validate_bundle.py`
- `python3 -m unittest discover -s tests -v`
- `python3 skills/career-copilot/scripts/privacy_scan.py .`
- Verificación de instalación de perfil desechable y smoke test sintético.
- Comprobación de resolución de la release pública contra el tag `v0.15.0` con la CLI `skills`, sin tocar un workspace real de candidato.