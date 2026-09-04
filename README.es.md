# Career Copilot para Hermes

<div align="center">
<pre>
 ██████╗ █████╗ ██████╗ ███████╗███████╗██████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
██║     ███████║██████╔╝█████╗  █████╗  ██████╔╝
██║     ██╔══██║██╔══██╗██╔══╝  ██╔══╝  ██╔══██╗
╚██████╗██║  ██║██║  ██║███████╗███████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚══════╝╚══════╝╚═╝  ╚═╝

 ██████╗ ██████╗ ██████╗ ██╗██╗      ██████╗ ████████╗
██╔════╝██╔═══██╗██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
██║     ██║   ██║██████╔╝██║██║     ██║   ██║   ██║
██║     ██║   ██║██╔═══╝ ██║██║     ██║   ██║   ██║
╚██████╗╚██████╔╝██║     ██║███████╗╚██████╔╝   ██║
 ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝


                         N
                         ▲
                         │
                    ╲    │    ╱
                      ╲  │  ╱
               W ◀───────◆───────▶ E
                      ╱  │  ╲
                    ╱    │    ╲
                         ▼
                         S
                         │
                         │
                      ·  │  ·
                         │
                    ─────✈─────
                       ╱ │ ╲
                     ╱   │   ╲
                  ·      │      ·
                         │
                         ▼
                    ╭─────────╮
                    │  ▣   ▣  │
                    │         │
                    ╰────┬────╯
                         ┴

              PRIVATE • EVIDENCE-DRIVEN
                   CAREER NAVIGATION
</pre>

<strong>Your career. Your data. Your path.</strong>
</div>

Versión original en inglés: [README.md](README.md).

Operaciones reutilizables y centradas en la privacidad para la búsqueda de empleo en [Hermes Agent](https://hermes-agent.nousresearch.com/docs).

## Capacidades

- Incorporación conversacional reanudable con puntos de control privados
- Incorporación basada en CV que extrae localmente la información admitida y pide al usuario confirmar o corregirla
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

La versión 0.6.0 es una versión piloto. Agrega reconexión selectiva con lazos débiles y posicionamiento basado en evidencia a la inteligencia relacional privada, manteniendo las guardrails de acciones externas en modo draft-only. Los adaptadores de Google requieren un CLI `gws` compatible, instalado y autenticado por separado. El adaptador de Gmail no envía mensajes de forma intencional. Las mutaciones de Google requieren un perfil privado en modo `confirm_each_external`.

Con licencia Apache-2.0; consulta [LICENSE](LICENSE).
