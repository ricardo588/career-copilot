# Quickstart — para tu hermana (y cualquiera no técnico)

## 🖱️ Opción A: Doble-click (macOS, más fácil)

1. Descarga este archivo: **[Install_Career_Copilot.command](Install_Career_Copilot.command)** (botón derecho → "Guardar enlace como…")
2. Abre **Terminal** y dale permisos (solo la primera vez):
   ```bash
   chmod +x ~/Downloads/Install_Career_Copilot.command
   ```
3. **Haz doble-click** en el archivo descargado.
4. Verás una ventana con pasos automáticos. Al final te dirá el comando para empezar.
5. Copia ese comando, pégalo en Terminal, pulsa Enter.
6. Escribe: `"Hola, ayúdame con mi onboarding. Una pregunta a la vez, por favor."`

---

## 🌐 Opción B: Una línea en Terminal (Linux/macOS/WSL)

Copia y pega esto **entero** en Terminal y pulsa Enter:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ricardo588/career-copilot/main/install.sh)
```

Hace todo solo: clona, instala profile, configura, crea tu carpeta privada.

---

## ✅ Qué pasa después

- Se abre el chat de Career Copilot.
- Te hace **una pregunta corta a la vez** (roles, senioridad, fortalezas, etc.).
- Tus respuestas se guardan **solo en tu Mac** (`~/Documents/CareerCopilot/`).
- **Nada se envía a GitHub** ni a nadie sin tu "sí, envíalo" explícito.
- Puedes cerrar y volver otro día: retoma donde lo dejaste.

---

## 🆘 Si algo falla

1. Asegúrate de tener **Hermes instalado** y funcionando (`hermes --version`).
2. Si el doble-click no abre Terminal: clic derecho → "Abrir con" → Terminal.
3. Si dice "permission denied": ejecuta `chmod +x` otra vez.
4. Escríbeme (Ricardo) y lo arreglo yo.

---

**Tus datos, tu control. Siempre.**