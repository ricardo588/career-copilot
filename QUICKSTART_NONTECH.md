# Quickstart — for non-technical users

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
bash <(curl -fsSL https://raw.githubusercontent.com/<OWNER>/career-copilot/main/install.sh)
```

It clones, installs the profile, configures everything, and creates your private workspace.

---

## ✅ What happens next

- The Career Copilot chat opens.
- It asks **one short question at a time** (target roles, seniority, strengths, etc.).
- Your answers are saved **only on your machine** (`~/Documents/CareerCopilot/`).
- **Nothing is sent to GitHub** or shared without your explicit "yes, send it."
- You can close and come back later: it resumes where you left off.

---

## 🆘 If something goes wrong

1. Make sure **Hermes is installed** and working (`hermes --version`).
2. If double-click doesn't open Terminal: right-click → "Open With" → Terminal.
3. If it says "permission denied": run `chmod +x` again.
4. Contact the maintainer and we'll fix it.

---

**Your data, your control. Always.**