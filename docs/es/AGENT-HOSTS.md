# Hosts de agentes y portabilidad

Versión original en inglés: [docs/AGENT-HOSTS.md](../AGENT-HOSTS.md).

Career Copilot es un paquete de flujos de trabajo local-first, no un producto de un solo agente. Su núcleo portable es `skills/career-copilot/`: un `SKILL.md`, scripts Python deterministas, referencias, plantillas y ejemplos sintéticos. No contiene datos de candidatos, credenciales ni estado específico de perfiles de un host.

## Hosts soportados en v0.12.1

| Host | Soporte | Punto de entrada |
| --- | --- | --- |
| Hermes Agent | Adaptador ejecutable | `distribution.yaml`, `install.sh` y `Install_Career_Copilot.command` |
| Claude Code | Adaptador de skill ejecutable | `.claude/skills/career-copilot/SKILL.md` |
| OpenClaw | Adaptador de skill ejecutable | `.openclaw/skills/career-copilot/SKILL.md` |
| ChatGPT | Sólo guía | `agent-adapters/chatgpt/INSTRUCTIONS.md` |

Los adaptadores de Claude Code y OpenClaw apuntan al mismo núcleo portable. No crean perfiles, instalan dependencias, obtienen credenciales ni conceden autorización para acciones externas.

## Uso desde un host local ejecutable

1. Clona el repositorio y usa el mecanismo documentado de ese host para descubrir skills locales.
2. Asegura que el host tenga Python 3.11+ si ejecutará scripts.
3. Crea un workspace privado fuera del clon y de todo repositorio Git.
4. Lee `skills/career-copilot/SKILL.md` antes de operar. Ejecuta sólo el flujo que pidió explícitamente la persona.
5. Pasa rutas explícitas dentro del workspace privado. Usa `draft_only` por defecto; no ejecutes una acción externa sin la autorización vigente requerida.

Los scripts Python son independientes del host, pero un host no queda soportado automáticamente sólo por poder leer Markdown. Debe preservar los límites de workspace privado y acciones explícitas, además de ejecutar Python local de forma segura.

## Límite de ChatGPT

El paquete para ChatGPT explica el flujo y puede preparar instrucciones revisables. No accede por defecto al workspace local ni a la terminal y no debe afirmar que ejecutó un script, revisó una vacante, actualizó un tracker, envió un mensaje o postuló. Usa un host local ejecutable soportado para esos pasos.

## Distribución específica de Hermes

Hermes sigue siendo un adaptador opcional soportado. Su instalador de perfiles, comandos y solución de problemas están en [INSTALL.md](INSTALL.md), [QUICKSTART.md](QUICKSTART.md) y [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Esos comandos no aplican a Claude Code, OpenClaw ni ChatGPT.
