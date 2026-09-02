# Inicio rápido — para personas no técnicas

Versión original en inglés: [QUICKSTART_NONTECH.md](QUICKSTART_NONTECH.md).

## 🖱️ Opción A: Doble clic (macOS, la más fácil)

1. Descarga este archivo: **[Install_Career_Copilot.command](Install_Career_Copilot.command)** (clic derecho → "Save link as…")
2. Abre **Terminal** y concede permiso de ejecución (solo la primera vez):
   ```bash
   chmod +x ~/Downloads/Install_Career_Copilot.command
   ```
3. **Haz doble clic** en el archivo descargado.
4. Se abrirá una ventana que ejecuta el instalador automáticamente. Al final muestra el comando para iniciar.
5. Copia ese comando, pégalo en Terminal y presiona Enter.
6. Escribe: `"Hello, help me with my onboarding. One question at a time, please."`

---

## 🌐 Opción B: Una línea en Terminal (Linux/macOS/WSL)

Copia y pega esta **línea completa** en Terminal y presiona Enter:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ricardo588/career-copilot/main/install.sh)
```

Clona, instala el perfil, configura todo y crea tu espacio de trabajo privado.

---

## ✅ Qué pasa después

- Se abre el chat de Career Copilot.
- Primero pregunta si ya tienes un CV. Si lo tienes, lee el archivo local, propone la información que puede extraer y te pide confirmar o corregirla en lugar de repetir esas preguntas.
- Después hace **una pregunta corta a la vez** solo sobre preferencias, restricciones y permisos faltantes.
- Tus respuestas se guardan **solo en tu máquina** (`~/Documents/CareerCopilot/`).
- Las **acciones externas están bloqueadas por defecto** (`draft_only`): puede investigar y preparar borradores, pero no puede postular, enviar, publicar ni contactar personas.
- Los usuarios avanzados pueden optar explícitamente por `confirm_each_external`; cada acción exacta sigue necesitando una confirmación fresca.
- Puedes cerrar y regresar después: retoma donde lo dejaste.

---

## 🆘 Si algo sale mal

1. Asegúrate de que **Hermes esté instalado** y funcione (`hermes --version`).
2. Si el doble clic no abre Terminal: clic derecho → "Open With" → Terminal.
3. Si dice "permission denied": vuelve a ejecutar `chmod +x`.
4. Contacta al mantenedor y lo corregimos.

---

**Tus datos, tu control. Siempre.**
