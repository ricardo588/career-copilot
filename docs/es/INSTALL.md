# Instalación para terceros

Versión original en inglés: [docs/INSTALL.md](../INSTALL.md).

Career Copilot se instala como un perfil aislado de Hermes. Cada persona obtiene un espacio de trabajo privado separado; el repositorio no contiene datos de candidatos.

## Enlaces rápidos para usuarios finales

| Método | Archivo | Ideal para |
|--------|---------|------------|
| **Línea única (Linux/macOS/WSL)** | [`install.sh`](../../install.sh) | Personas cómodas con Terminal |
| **Doble clic (macOS)** | [`Install_Career_Copilot.command`](../../Install_Career_Copilot.command) | Sin experiencia de terminal |
| **Guía paso a paso** | [`QUICKSTART_NONTECH.es.md`](../../QUICKSTART_NONTECH.es.md) | Quien prefiera leer primero |

## Requisitos previos

- Hermes Agent 0.20.0 o más reciente
- Python 3.11 o más reciente
- Git
- Acceso al repositorio público de distribución
- Un proveedor de modelos configurado en Hermes

Verifica con:

```bash
hermes --version
python3 --version
git --version
```

## 1. Obtén el repositorio

El repositorio es público. Clónalo directamente o instálalo desde GitHub sin credenciales:

```bash
git clone https://github.com/ricardo588/career-copilot.git
```

## 2. Instala un perfil aislado

Desde una copia local:

```bash
hermes profile install /path/to/career-copilot --name my-career-copilot --alias
```

O desde un repositorio de GitHub al que el instalador pueda acceder:

```bash
hermes profile install ricardo588/career-copilot --name my-career-copilot --alias
```

El instalador valida `distribution.yaml` y copia solo los archivos pertenecientes a la distribución.

## 3. Configura Hermes

```bash
hermes -p my-career-copilot setup
hermes -p my-career-copilot config migrate
hermes -p my-career-copilot skills list
```

Confirma que `career-copilot` esté habilitado.

## 4. Crea un espacio de trabajo privado

Elige un directorio fuera del repositorio clonado y fuera del directorio del perfil de Hermes.

```bash
SKILL_DIR="$HOME/.hermes/profiles/my-career-copilot/skills/career-copilot"
WORKSPACE="$HOME/Documents/CareerCopilot"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE" start
```

El bootstrap no sobrescribe archivos existentes. El onboarding guarda puntos de control en un archivo JSON oculto y crea copias de seguridad antes de finalizar `profile.yaml` o `rules.yaml`.

## 5. Inicia el asistente

```bash
hermes -p my-career-copilot chat -s career-copilot
```

Mensaje inicial sugerido:

> Continúa mi onboarding de Career Copilot. Primero pregúntame si ya tengo un CV; si lo tengo, extrae localmente la información admitida y pídeme confirmar o corregirla. Después haz una sola pregunta corta por sección para todo lo que falte, guarda cada respuesta confirmada en puntos de control y mantén el modo draft-only por defecto.

`draft_only` bloquea las acciones externas. Otros usuarios pueden optar explícitamente por `confirm_each_external`; cada acción exacta y su destino siguen necesitando una confirmación fresca. Para un perfil que nunca deba cambiar de modo, inicia el onboarding con `start --lock-draft-only`.

## 6. Verifica el aislamiento

- El estado generado del candidato existe solo dentro del espacio de trabajo elegido. Un CV fuente puede permanecer en la ruta local elegida por el usuario y nunca debe copiarse al clon ni al perfil instalado.
- No aparecen CV, contactos, datos de compensación ni credenciales en el clon.
- `git status --short` sigue limpio después de usar el asistente.
- Las integraciones externas permanecen desactivadas hasta que se configuren localmente.

## Actualización

Actualiza el clon fuente, revisa las notas de la versión y luego reinstala en un perfil desechable antes de reemplazar un perfil en uso.

```bash
git pull --ff-only
hermes profile install . --name career-copilot-upgrade-test
hermes -p career-copilot-upgrade-test skills list
```

Nunca uses la exportación de un perfil personal como mecanismo de actualización o distribución.
