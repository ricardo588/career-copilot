# Quickstart — for non-technical users

Spanish version: [QUICKSTART_NONTECH.es.md](QUICKSTART_NONTECH.es.md).

## 🖱️ Option A: Double-click (macOS, easiest)

1. Download this file: **[Install_Career_Copilot.command](Install_Career_Copilot.command)** (right-click → "Save link as…")
2. Open **Terminal** and grant execute permission (first time only):
   ```bash
   chmod +x ~/Downloads/Install_Career_Copilot.command
   ```
3. **Double-click** the downloaded file.
4. A window runs the installer automatically. At the end it shows the command to start.
5. Copy that command, paste into Terminal, press Enter.
6. Type: `"Hello, help me with my onboarding. One question at a time, please."`

---

## 🌐 Option B: One line in Terminal (Linux/macOS/WSL)

Copy and paste this **entire line** into Terminal and press Enter:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ricardo588/career-copilot/main/install.sh)
```

It clones, installs the profile, configures everything, and creates your private workspace.

---

## ✅ What happens next

- The Career Copilot chat opens.
- It first asks whether you already have a CV. If so, it reads the local file, proposes the information it can extract, and asks you to confirm or correct it instead of repeating those questions.
- It then asks **one short question at a time** only for missing preferences, constraints and permissions.
- Your answers are saved **only on your machine** (`~/Documents/CareerCopilot/`).
- **External actions are blocked by default** (`draft_only`): it can research and prepare drafts, but it cannot apply, send, publish or contact people.
- Advanced users may explicitly opt in to `confirm_each_external`; every exact action still needs a fresh confirmation.
- You can close and come back later: it resumes where you left off.

---

## 🆘 If something goes wrong

1. Make sure **Hermes is installed** and working (`hermes --version`).
2. If double-click doesn't open Terminal: right-click → "Open With" → Terminal.
3. If it says "permission denied": run `chmod +x` again.
4. Contact the maintainer and we'll fix it.

---

**Your data, your control. Always.**