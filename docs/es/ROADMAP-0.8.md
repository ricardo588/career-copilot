# Career Copilot 0.8 — Triage transaccional de Gmail

Versión original en inglés: [docs/ROADMAP-0.8.md](../ROADMAP-0.8.md).

## Estado

**Entregada:** v0.8.0 agrega un flujo deliberadamente acotado de triage de evidencia Gmail y una frontera de proyección privada hacia Obsidian. Es una versión de seguridad: no introduce envío de solicitudes, envío/respuesta/reenvío/creación de borradores de correo, archivar, etiquetar, borrar, reconciliación automática ni trabajos recurrentes.

## Objetivo

Permitir que un solo mensaje de Gmail seleccionado explícitamente se use como **evidencia privada revisable**, sin convertir su texto en una decisión automática del tracker. La persona conserva la responsabilidad de revisar evidencia, resolver identidad, escoger un registro del tracker y aprobar cualquier mutación.

## Decisiones de producto aceptadas

1. **Evidencia primero:** el triage Gmail lee un mensaje exacto y crea una propuesta local para revisión. Nunca infiere un hecho del tracker desde el texto del correo.
2. **Retención privada:** un hecho revisado requiere un `supported_fact` proporcionado por quien revisa y exactamente un extracto mínimo o un hash de contenido. La referencia resultante es opaca y permanece en el workspace privado.
3. **Reconciliación de solo lectura:** `gmail-reconcile` entrega una referencia opaca revisada al planificador determinista de reconciliación y devuelve únicamente una propuesta dry-run. No puede escribir Gmail, CSV, Sheets ni un tracker remoto.
4. **Marcar leído de alcance estrecho:** Gmail sólo puede retirar `UNREAD`, después de un hash exacto del plan revisado, `confirm_each_external`, una prelectura actual que confirme el estado sin leer y una lectura posterior que confirme que `UNREAD` ya no existe.
5. **Ledger cerrado ante fallas:** el ledger local append-only es idempotente para el mismo mensaje, bloquea una colisión de fingerprint y bloquea un ledger corrupto para revisión humana.
6. **Sólo Obsidian:** V0.8 permite una proyección opcional a Markdown local con dry-run, hash exacto de plan, auditoría privada, escritura atómica y readback. Se rechazan vaults que sean symlinks o estén dentro de la distribución o de un repositorio Git. Kanban remoto se difiere a V0.9.

## Flujo

```text
mensaje Gmail explícito
  → propuesta privada para revisión
  → evento de evidencia revisada opcional
  → propuesta pura de reconciliación del tracker (sólo dry-run)
  → marcado individual como leído opcional, aprobado y verificado por separado
```

Las rutas de evidencia y auditoría son artefactos del workspace privado:

- `evidence/gmail-evidence.jsonl#<uuid>`
- `triage/gmail-triage.jsonl#<uuid>`
- `audit/external-actions.jsonl#<uuid>`

Nunca deben copiarse a un tracker, repositorio, distribución de perfil o ticket público.

## Criterios de seguridad y privacidad

- Un evento del ledger almacena referencias y hashes mínimos, no cuerpos de Gmail.
- El almacenamiento de evidencia rechaza soporte ambiguo o contradictorio y acepta un extracto (máximo 500 caracteres) **o** un hash de contenido SHA-256 de 64 caracteres en minúsculas, nunca ambos.
- Una lectura inválida, estado `UNREAD` obsoleto, hash incorrecto, readback diferente, escape de ruta, corrupción del ledger o identidad ambigua detiene el flujo.
- `draft_only` bloquea cualquier mutación antes de actividad de mutación Gmail u Obsidian.
- Una mutación exitosa reporta readback verificado; la respuesta exitosa del proveedor por sí sola no basta.
- Las pruebas y demos no usan datos de Gmail, Obsidian, Sheets, tracker, perfil, credencial, contacto, compensación o candidato en producción.

## Actualización

No se requiere migrar datos privados para 0.8. Los workspaces existentes y trackers CSV locales siguen siendo compatibles. Los directorios nuevos de evidencia Gmail, ledger y auditoría del adaptador se crean solamente bajo un workspace privado elegido por el usuario cuando se ejecuta el comando opcional correspondiente.

Antes de reemplazar un perfil instalado, instala esta versión en un perfil desechable, ejecuta la demo sintética y confirma que el workspace se mantenga fuera de la distribución y de cualquier repositorio Git.

## Verificación de release

El gate de release ejecuta:

1. suite completa de pruebas unitarias;
2. validación del bundle;
3. demo sintética de extremo a extremo con cero acciones externas;
4. instalación desechable de perfil Hermes;
5. escaneo de privacidad y revisiones de diff Git.

## Diferido a V0.9 o posterior

- Proyección o reconciliación con Kanban remoto.
- Resolución automática de identidad desde evidencia Gmail.
- Triage de inbox completo/en segundo plano, schedules y trabajos recurrentes.
- Enviar, responder, reenviar, crear borradores, archivar, etiquetar o borrar correo.
- Transacciones multi-sistema y cambios automáticos al tracker.
