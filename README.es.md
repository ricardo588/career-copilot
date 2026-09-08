# Career Copilot para Hermes

<p align="center">
  <img src="assets/career-copilot-wordmark.png" alt="Career Copilot" width="800">
</p>

Versión original en inglés: [README.md](README.md).

Operaciones reutilizables y centradas en la privacidad para la búsqueda de empleo en [Hermes Agent](https://hermes-agent.nousresearch.com/docs).

## Capacidades

- Incorporación conversacional reanudable con puntos de control privados
- Incorporación basada en CV que extrae localmente la información admitida y pide al usuario confirmar o corregirla
- Empresas objetivo opcionales y sugerencias transparentes, editables por el usuario, de cobertura de portales según familia de puesto, seniority, industria, geografía elegible, modalidad y tipo de empleo declarados
- Generación privada y de sólo lectura de shortlists desde exportaciones JSON/CSV de vacantes, con validación de fuente seleccionada, frescura y URL canónica; nunca consulta un portal ni cambia un tracker
- Evaluación de vacantes específica por candidato con evidencia verificada
- Matrices con cita de requisito-a-evidencia por oportunidad, más revisión local opcional del CV
- Empresas objetivo privadas y respaldadas por evidencia con relojes independientes de frescura para empresa y Human Path
- Revisión semanal de campaña, configurable y de solo lectura, con borradores, aprobaciones, intentos, resultados y aprendizaje diferenciados
- Banco privado de historias estructuradas con procedencia, desconocidos explícitos y vistas reutilizables para evaluación, entrevistas y CV
- Criterios de carrera opcionales y narrativa de salida aprobada por el candidato, manteniendo separados hechos, interpretaciones y preferencias
- Investigación Human Path para contactos actuales, reclutador/publicador y responsable de contratación
- Inteligencia relacional estructurada con rol, influencia, fortaleza, frescura de la evidencia y autorización independiente
- Reconexión selectiva con lazos débiles, tope privado por ciclo, contexto relacional y sin pedir empleo/referido en el primer borrador
- Posicionamiento basado en evidencia: alcance, acción de liderazgo y resultado confirmado
- Registros de preparación y resultado de reuniones informativas, y debriefs posteriores a entrevistas con separación de hechos y solo borrador para seguimiento
- Registros privados de ofertas, comparación de paquete total con fecha de origen y borradores de negociación con límites exactos de autorización
- Inteligencia sobre entrevistadores a partir de hechos obtenidos, manteniendo separadas las hipótesis
- Dedupe canónico y seguimiento local en CSV
- Relojes independientes de verificación de vacantes y Human Path, con migración conservadora de legados
- Demo sintética de perfil → vacante → tracker → entrevista
- Adaptadores opcionales con modo dry-run primero para Google Sheets, Gmail y Obsidian
- `draft_only` por defecto, opt-in explícito `confirm_each_external` y perfiles bloqueables
- Guardrails explícitos para mensajes, postulaciones y acciones públicas
- Pruebas automáticas de privacidad, instalación y funcionamiento

## Modelo de privacidad

El repositorio contiene solo metodología, plantillas vacías, scripts deterministas y fixtures sintéticos. Los CV, bancos de historias, preferencias de carrera, contactos, compensación, correos, memorias, sesiones, credenciales, identificadores y trackers reales pertenecen al espacio de trabajo privado de cada instalador y nunca se comprometen al repositorio.

No exportes un perfil personal de Hermes para distribuir este proyecto. Instala la distribución de perfil incluida aquí.

## Documentación

- [Installation](docs/INSTALL.md) — referencia completa de CLI
- [Non-technical quickstart](QUICKSTART_NONTECH.md) — línea única, archivo .command para macOS, guía paso a paso
- [Quickstart](docs/QUICKSTART.md) — quickstart para desarrolladores
- [Synthetic demo](docs/DEMO.md)
- [Optional adapters](docs/ADAPTERS.md)
- [Privacy and threat model](docs/PRIVACY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### En español

- [Instalación](docs/es/INSTALL.md)
- [Guía rápida para no técnicos](QUICKSTART_NONTECH.es.md)
- [Inicio rápido](docs/es/QUICKSTART.md)
- [Demo sintética](docs/es/DEMO.md)
- [Adaptadores opcionales](docs/es/ADAPTERS.md)
- [Privacidad y modelo de amenazas](docs/es/PRIVACY.md)
- [Solución de problemas](docs/es/TROUBLESHOOTING.md)
- [Diseño de Proyección opcional a Kanban de Obsidian 0.9](docs/es/ROADMAP-0.9.md)
- [Diseño de Onboarding estratégico 0.9.1](docs/es/ROADMAP-0.9.1.md)
- [Diseño de Descubrimiento privado de vacantes 0.10.0](docs/es/ROADMAP-0.10.0.md)
- [Diseño de Evidencia del catálogo de portales 0.10.1](docs/es/ROADMAP-0.10.1.md)
- [Roadmap de alcance integrado de adquisición segura 0.11.0](docs/es/ROADMAP-0.11.0.md)
- [Catálogo versionado de cobertura de portales](skills/career-copilot/references/portal-catalog.es.md)
- [Contrato de adquisición explícita y acciones](skills/career-copilot/references/acquisition-and-actions.es.md)
- [Diseño de Triage transaccional Gmail 0.8](docs/es/ROADMAP-0.8.md)
- [Diseño de Operational Tracker 0.7](docs/es/ROADMAP-0.7.md)

## Instaladores (para usuarios finales)

| Método | Archivo | Ideal para |
|--------|---------|------------|
| **Línea única (Linux/macOS/WSL)** | [`install.sh`](install.sh) | Personas cómodas con Terminal |
| **Doble clic (macOS)** | [`Install_Career_Copilot.command`](Install_Career_Copilot.command) | Sin experiencia de terminal |
| **Guía paso a paso** | [`QUICKSTART_NONTECH.md`](QUICKSTART_NONTECH.md) | Quien prefiera leer primero |

Todos los instaladores crean un perfil aislado de Hermes, un espacio de trabajo privado (`~/Documents/CareerCopilot/` con permisos `0700/0600`) y arrancan la incorporación guiada. Las acciones externas están bloqueadas por defecto en `draft_only`; otros usuarios pueden optar explícitamente por `confirm_each_external`.

## Desarrollo local

Requisitos: Hermes Agent 0.20.0 o superior, Git y Python 3.11 o superior.

```bash
python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
hermes profile install . --name career-copilot-test
```

Ejecuta la demo de extremo a extremo sin cuentas reales:

```bash
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir "$OUTPUT_DIR"
```

## Estado actual

La versión 0.11.0 agrega adquisición pública explícita y de sólo lectura para feeds Greenhouse y Lever confirmados por la persona candidata, frescura normalizada por proveedor, auditoría local de frescura del catálogo y planes de acciones externas sólo como borrador. Valida rutas privadas de salida antes de cualquier GET, rechaza redirecciones y acepta únicamente URLs de páginas de vacante alojadas por proveedores documentados; nunca busca, autentica, sigue URLs de postulación, postula, escribe el tracker ni contacta personas. Conserva la evidencia fechada del catálogo de portales v0.10.1. Conserva el triage transaccional Gmail y la proyección opcional y local a Kanban de Obsidian de v0.9.0. Amplía el onboarding estratégico de v0.9.1 con sugerencias transparentes y editables por la persona de cobertura de portales, derivadas de familia de puesto, seniority, industria, geografía elegible, modalidad y tipo de empleo declarados. El catálogo local es una heurística de cobertura, no un ranking vigente de desempeño de mercado; su evidencia fechada y límite de mantenimiento se publican en el [catálogo versionado de cobertura de portales](skills/career-copilot/references/portal-catalog.es.md). También introduce shortlists privados y de sólo lectura desde exportaciones JSON/CSV de vacantes: acepta sólo un archivo local proporcionado explícitamente, normaliza localmente encabezados CSV y etiquetas de fuente documentados, valida fuentes seleccionadas por la persona, frescura de publicación y URLs canónicas, elimina duplicados canónicos y conserva el contexto del candidato para evaluación posterior sin declarar un encaje. No consulta portales, obtiene vacantes vigentes, escribe el tracker, postula, contacta personas ni ejecuta acciones externas. Las elecciones de empresa/portal y los reportes shortlist permanecen privados. Cualquier mutación de Obsidian sigue requiriendo `confirm_each_external`, hash vigente de un plan revisado, auditoría en workspace privado, prelectura vigente, escritura atómica y readback verificado. Los adaptadores Google requieren un CLI `gws` compatible, instalado y autenticado por separado.

Con licencia Apache-2.0; consulta [LICENSE](LICENSE).
