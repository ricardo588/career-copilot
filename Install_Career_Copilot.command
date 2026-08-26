#!/usr/bin/env bash
# Career Copilot — macOS double-click installer
# Save as "Install Career Copilot.command" and make executable:
# chmod +x "Install Career Copilot.command"
# Then double-click.

# Keep window open at the end
trap 'echo; read -p "Press Enter to close..."' EXIT

# Colors
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
echo -e "${BLUE}  Career Copilot — Easy Installer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# ---------- Checks ----------
say "Checking requirements..."

command -v hermes >/dev/null || err "Hermes is not installed. Open Terminal and ask for help: brew install hermes-agent"
command -v python3 >/dev/null || err "Python 3 is not installed (usually comes with macOS)."
command -v git >/dev/null || err "Git is not installed (install Xcode Command Tools: xcode-select --install)."

HERMES_VER=$(hermes --version 2>/dev/null | head -1 || echo "unknown")
say "Hermes: $HERMES_VER"
ok "All set"

# ---------- Download ----------
REPO_DIR="$HOME/.career-copilot-source"
REPO_URL="https://github.com/ricardo588/career-copilot.git"

say "Downloading Career Copilot from GitHub..."
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" pull --ff-only --quiet
    ok "Already present, updated"
else
    git clone --quiet "$REPO_URL" "$REPO_DIR"
    ok "Downloaded"
fi

# ---------- Install profile ----------
PROFILE_NAME="career-copilot"

say "Installing into Hermes..."
if hermes profile list 2>/dev/null | grep -q "^$PROFILE_NAME\b"; then
    warn "Existing profile detected — updating..."
    hermes profile delete "$PROFILE_NAME" -y >/dev/null 2>&1
fi

hermes profile install "$REPO_DIR" --name "$PROFILE_NAME" --alias >/dev/null
ok "Profile '$PROFILE_NAME' installed"

# ---------- Configure ----------
say "Configuring Hermes..."
hermes -p "$PROFILE_NAME" setup >/dev/null 2>&1
hermes -p "$PROFILE_NAME" config migrate >/dev/null 2>&1
ok "Configured"

# ---------- Workspace ----------
WORKSPACE_DIR="$HOME/Documents/CareerCopilot"
say "Creating your private folder at Documents/CareerCopilot..."
SKILL_DIR="$HOME/.hermes/profiles/$PROFILE_NAME/skills/career-copilot"
mkdir -p "$WORKSPACE_DIR"
python3 "$SKILL_DIR/scripts/bootstrap_workspace.py" --workspace "$WORKSPACE_DIR" >/dev/null
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace "$WORKSPACE_DIR" start >/dev/null
ok "Private folder created with your-user-only permissions"

# ---------- Done ----------
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Installation complete! 🎉${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "Now open Terminal (or use the one you have) and run:"
echo
echo -e "    ${BLUE}hermes -p career-copilot chat -s career-copilot${NC}"
echo
echo "Then type:"
echo '    "Hello, help me with my onboarding. One question at a time, please."'
echo
echo -e "${YELLOW}💡 Tip:${NC} Copy the command above (⌘C), paste into Terminal (⌘V), press Enter."
echo
echo "Your data (CV, preferences, contacts) stays ONLY in:"
echo "    $WORKSPACE_DIR"
echo "Nothing gets uploaded to GitHub or leaves your Mac without your authorization."
echo