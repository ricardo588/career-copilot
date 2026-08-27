#!/usr/bin/env bash
# Career Copilot — simple installer for non-technical users
# Run: bash <(curl -fsSL https://raw.githubusercontent.com/ricardo588/career-copilot/main/install.sh)

set -euo pipefail

# Friendly colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

say()   { echo -e "${BLUE}🔹${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
err()   { echo -e "${RED}❌${NC} $*"; exit 1; }

# ---------- Minimum checks ----------
say "Checking requirements..."

command -v hermes >/dev/null || err "Hermes is not installed. Ask for help installing it first."
command -v python3 >/dev/null || err "Python 3 is not installed."
command -v git >/dev/null || err "Git is not installed."

HERMES_VER=$(hermes --version 2>/dev/null | head -1 || echo "unknown")
say "Hermes detected: $HERMES_VER"
ok "Requirements met"

# ---------- Clone / update repo ----------
REPO_DIR="$HOME/.career-copilot-source"
REPO_URL="https://github.com/ricardo588/career-copilot.git"

say "Downloading Career Copilot..."
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" pull --ff-only --quiet
    ok "Updated"
else
    git clone --quiet "$REPO_URL" "$REPO_DIR"
    ok "Downloaded"
fi

# ---------- Install profile ----------
PROFILE_NAME="career-copilot"

say "Installing profile into Hermes..."
if hermes profile info "$PROFILE_NAME" >/dev/null 2>&1; then
    warn "Profile '$PROFILE_NAME' already exists. Updating it without deleting user data..."
    hermes profile update "$PROFILE_NAME" -y >/dev/null
    ok "Profile '$PROFILE_NAME' updated"
else
    hermes profile install "$REPO_DIR" --name "$PROFILE_NAME" --alias >/dev/null
    ok "Profile '$PROFILE_NAME' installed"
fi

# ---------- Configure Hermes ----------
say "Configuring Hermes..."
hermes -p "$PROFILE_NAME" setup >/dev/null 2>&1
hermes -p "$PROFILE_NAME" config migrate >/dev/null 2>&1
ok "Hermes configured"

# ---------- Create private workspace ----------
WORKSPACE_DIR="$HOME/Documents/CareerCopilot"

say "Creating your private workspace at $WORKSPACE_DIR ..."
SKILL_DIR="$HOME/.hermes/profiles/$PROFILE_NAME/skills/career-copilot"
mkdir -p "$WORKSPACE_DIR"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE_DIR" >/dev/null
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE_DIR" start >/dev/null
ok "Workspace ready (private permissions applied)"

# ---------- Done ----------
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Career Copilot installed and ready!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "To get started, run this command:"
echo -e "${BLUE}    hermes -p $PROFILE_NAME chat -s career-copilot${NC}"
echo
echo "Then type something like:"
echo '    "Hello, help me with my onboarding. One question at a time, please."'
echo
echo "Your private data stays ONLY in: $WORKSPACE_DIR"
echo "Nothing leaves your machine without your explicit confirmation."
echo