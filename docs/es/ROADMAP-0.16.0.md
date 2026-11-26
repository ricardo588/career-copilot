# Career Copilot 0.16.0 — Candidato de release de plugin portable para Marketplace

English version: [docs/ROADMAP-0.16.0.md](../ROADMAP-0.16.0.md).

## Objetivo

Preparar el repositorio público como paquete portable Agent Plugins v1 para una revisión posterior de Hermes Marketplace, sin cambiar el contrato de privacidad ni de acciones de Career Copilot.

## Alcance local entregado

- El `plugin.json` raíz declara el esquema Agent Plugins v1, identidad `career-copilot`, licencia Apache-2.0 y versión `0.16.0`.
- El paquete reutiliza directamente `skills/career-copilot/`; no se agregó un árbol de skill duplicado.
- El paquete es solo de skill: no contiene código de plugin, herramientas, hooks, middleware, servidor MCP, servicio, cron, hook de instalación/red, telemetría, requisito de secreto/configuración ni manifiesto de dependencias.
- La documentación de Marketplace en inglés y español describe comandos de ciclo de vida, namespaces, convivencia de rutas, privacidad, integraciones opcionales, eliminación segura para workspaces y la diferencia entre validación local y admisión al catálogo.
- Un proceso local de preparación de catálogo omite intencionalmente el SHA hasta que exista una release publicada y autorizada.
- La validación de bundle y las pruebas unitarias verifican la identidad del manifiesto portable y la ausencia de capacidades declaradas/entrypoints de runtime.

## Límites no negociables

- Los workspaces de candidato siguen siendo privados, elegidos por el usuario y externos al repositorio, instalación del plugin y distribución de perfil.
- `draft_only` sigue siendo el valor predeterminado. Instalar o habilitar no postula, envía mensajes, contacta, publica, muta un pipeline real, autentica ni hace llamadas de red.
- Google Sheets, Gmail y Obsidian siguen siendo integraciones opcionales configuradas por el usuario con límites de autorización explícitos.
- Este candidato de release no es entrada de catálogo, ficha aprobada, paquete buscable de Marketplace, release publicada ni tag.

## Gates locales de release

```bash
hermes plugins doctor . --ci
python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
python3 skills/career-copilot/scripts/privacy_scan.py .
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir <temporary-directory>
git diff --check
```

## Siguiente autorización

Publicar una release/tag, abrir un PR de catálogo o realizar cualquier escritura externa requiere autorización explícita de Ricardo. Una entrada de catálogo posterior debe usar el SHA inmutable completo de 40 caracteres de esa release autorizada y pasar validación de catálogo en ese pin.
