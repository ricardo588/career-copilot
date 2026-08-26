#!/usr/bin/env bash
# Career Copilot — instalador simple para usuarios no técnicos
# Ejecuta: bash <(curl -fsSL https://raw.githubusercontent.com/ricardo588/career-copilot/main/install.sh)

set -euo pipefail

# Colores para output amigable
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sin color

say()   { echo -e "${BLUE}🔹${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
err()   { echo -e "${RED}❌${NC} $*"; exit 1; }

# ---------- Verificaciones mínimas ----------
say "Verificando lo necesario..."

command -v hermes >/dev/null || err "Hermes no está instalado. Pide ayuda para instalarlo primero."
command -v python3 >/dev/null || err "Python 3 no está instalado."
command -v git >/dev/null || err "Git no está instalado."

HERMES_VER=$(hermes --version 2>/dev/null | head -1 || echo "unknown")
say "Hermes detectado: $HERMES_VER"
ok "Requisitos cumplidos"

# ---------- Clonar / actualizar repo ----------
REPO_DIR="$HOME/.career-copilot-source"
REPO_URL="https://github.com/ricardo588/career-copilot.git"

say "Descargando Career Copilot..."
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" pull --ff-only --quiet
    ok "Actualizado"
else
    git clone --quiet "$REPO_URL" "$REPO_DIR"
    ok "Descargado"
fi

# ---------- Instalar profile ----------
PROFILE_NAME="career-copilot"

say "Instalando perfil en Hermes..."
if hermes profile list 2>/dev/null | grep -q "^$PROFILE_NAME\b"; then
    warn "El perfil '$PROFILE_NAME' ya existe. Lo actualizamos..."
    hermes profile delete "$PROFILE_NAME" -y >/dev/null 2>&1
fi

hermes profile install "$REPO_DIR" --name "$PROFILE_NAME" --alias >/dev/null
ok "Perfil '$PROFILE_NAME' instalado"

# ---------- Configurar Hermes ----------
say "Configurando Hermes..."
hermes -p "$PROFILE_NAME" setup >/dev/null 2>&1
hermes -p "$PROFILE_NAME" config migrate >/dev/null 2>&1
ok "Hermes configurado"

# ---------- Crear workspace privado ----------
WORKSPACE_DIR="$HOME/Documents/CareerCopilot"

say "Creando tu espacio de trabajo privado en $WORKSPACE_DIR ..."
SKILL_DIR="$HOME/.hermes/profiles/$PROFILE_NAME/skills/career-copilot"
mkdir -p "$WORKSPACE_DIR"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE_DIR" >/dev/null
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE_DIR" start >/dev/null
ok "Workspace listo (permisos privados aplicados)"

# ---------- Listo ----------
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 ¡Career Copilot instalado y listo!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "Para empezar, ejecuta este comando:"
echo -e "${BLUE}    hermes -p $PROFILE_NAME chat -s career-copilot${NC}"
echo
echo "Y escribe algo como:"
echo '    "Hola, ayúdame con mi onboarding. Una pregunta a la vez, por favor."'
echo
echo "Tus datos privados quedan SOLO en: $WORKSPACE_DIR"
echo "Nada sale de tu Mac sin tu confirmación explícita."
echo