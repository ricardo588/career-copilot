# Solución de problemas

Versión original en inglés: [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md).

## El skill no aparece

```bash
hermes -p <PROFILE> skills list
hermes profile info <PROFILE>
```

Reinstala desde una fuente validada si `career-copilot` no aparece. No copies un perfil personal como atajo.

## El espacio de trabajo se creó en el lugar incorrecto

Detente antes de agregar datos personales. Crea un nuevo directorio fuera del repositorio y de la raíz del perfil, actualiza `skills.config.career_copilot.workspace` y vuelve a ejecutar bootstrap.

El script de onboarding rechaza intencionalmente un espacio de trabajo dentro del perfil.

## El onboarding no finaliza

```bash
SKILL_DIR="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot"
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace '<WORKSPACE>' status
python3 "$SKILL_DIR/scripts/onboarding.py" --workspace '<WORKSPACE>' questions
```

Como mínimo, proporciona roles objetivo, seniority, fortalezas, evidencia verificada, país/ubicación elegible, política del tracker y política de acciones externas.

## YAML no se puede leer en la pipeline

Los archivos de onboarding finalizados son YAML compatible con JSON y no necesitan dependencia adicional. El YAML tradicional editado a mano requiere PyYAML en el entorno de ejecución.

## `gws` no se encuentra

Los adaptadores de Google son opcionales. Instala y autentica un CLI de Google Workspace compatible usando su documentación oficial y luego verifica `gws --help`. No agregues credenciales a este repositorio.

## La mutación de Google falla en la verificación

Trata la operación como fallida. Lee de nuevo el destino exacto, confirma la cuenta/hoja/rango/ID de mensaje y vuelve a intentar solo después de resolver la discrepancia. Nunca reportes éxito solo por el código de salida de la API.

## Se rechazó la ruta de Obsidian

Usa una ruta relativa `.md` dentro del vault configurado. Las rutas absolutas y la travesía `..` están bloqueadas.

## Falla el escaneo de privacidad en CI

Ejecuta localmente:

```bash
python3 skills/career-copilot/scripts/privacy_scan.py .
```

Si un marcador personalizado provocó la falla, elimina el valor privado y reemplázalo con datos sintéticos. No debilites el escáner solo para que CI pase.

## Necesitas ayuda de Hermes Agent

Usa la documentación oficial actual: https://hermes-agent.nousresearch.com/docs
