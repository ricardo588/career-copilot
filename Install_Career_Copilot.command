#!/usr/bin/env bash
# Career Copilot — instalador de doble-click para macOS
# Guárdalo como "Instalar Career Copilot.command" y dale permisos:
# chmod +x "Instalar Career Copilot.command"
# Luego haz doble-click.

# Mantener la ventana abierta al final
trap 'echo; read -p "Presiona Enter para cerrar..."' EXIT

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

say()   { echo -e "${BLUE}🔹${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
err()   { echo -e "${RED}❌${NC} $*"; exit 1; }

clear
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Career Copilot — Instalador fácil${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# ---------- Verificaciones ----------
say "Verificando que todo esté listo..."

command -v hermes >/dev/null || err "Hermes no está instalado. Abre Terminal y pide ayuda para: brew install hermes-agent"
command -v python3 >/dev/null || err "Python 3 no está instalado (normalmente ya viene en macOS)."
command -v git >/dev/null || err "Git no está instalado (instala Xcode Command Tools: xcode-select --install)."

HERMES_VER=$(hermes --version 2>/dev/null | head -1 || echo "desconocida")
say "Hermes: $HERMES_VER"
ok "Todo listo"

# ---------- Descargar ----------
REPO_DIR="$HOME/.career-copilot-source"
REPO_URL="https://github.com/ricardo588/career-copilot.git"

say "Descargando Career Copilot desde GitHub..."
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" pull --ff-only --quiet
    ok "Ya lo tenías, actualizado"
else
    git clone --quiet "$REPO_URL" "$REPO_DIR"
    ok "Descargado"
fi

# ---------- Instalar profile ----------
PROFILE_NAME="career-copilot"

say "Instalando en Hermes..."
if hermes profile list 2>/dev/null | grep -q "^$PROFILE_NAME\b"; then
    warn "Perfil existente detectado — actualizando..."
    hermes profile delete "$PROFILE_NAME" -y >/dev/null 2>&1
fi

hermes profile install "$REPO_DIR" --name "$PROFILE_NAME" --alias >/dev/null
ok "Perfil '$PROFILE_NAME' instalado"

# ---------- Configurar ----------
say "Configurando Hermes..."
hermes -p "$PROFILE_NAME" setup >/dev/null 2>&1
hermes -p "$PROFILE_NAME" config migrate >/dev/null 2>&1
ok "Configurado"

# ---------- Workspace ----------
WORKSPACE_DIR="$HOME/Documents/CareerCopilot"
say "Creando tu carpeta privada en Documentos/CareerCopilot..."
SKILL_DIR="$HOME/.hermes/profiles/$PROFILE_NAME/skills/career-copilot"
mkdir -p "$WORKSPACE_DIR"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE_DIR" >/dev/null
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE_DIR" start >/dev/null
ok "Carpeta privada creada con permisos de solo-tu-usuario"

# ---------- Final ----------
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ¡Instalación completada! 🎉${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "Ahora abre Terminal (o usa la que ya tienes) y ejecuta:"
echo
echo -e "    ${BLUE}hermes -p career-copilot chat -s career-copilot${NC}"
echo
echo "Y escribe:"
echo '    "Hola, ayúdame con mi onboarding. Una pregunta a la vez, por favor."'
echo
echo -e "${YELLOW}💡 Tip:${NC} Copia el comando de arriba (⌘C), pégalo en Terminal (⌘V), pulsa Enter."
echo
echo "Tus datos (CV, preferencias, contactos) quedan SOLO en:"
echo "    $WORKSPACE_DIR"
echo "Nada se sube a GitHub ni sale de tu Mac sin que lo autorices."
echo