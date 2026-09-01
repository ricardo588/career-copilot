# Empresas objetivo privadas y respaldadas por evidencia

Usa este flujo para sostener una lista de organizaciones a investigar. El registro vive **solamente** en el workspace privado; nunca copies CVs, contactos, señales ni el JSON resultante al repositorio.

## Principios

- El interés por una empresa es una **preferencia declarada por la persona candidata**, no una afirmación de que la empresa sea buena, esté contratando o sea adecuada.
- Toda señal actual requiere `summary`, URL de fuente y `checked_at` explícito.
- La frescura de señales de la empresa y la de Human Paths se revisa con relojes independientes.
- Investigación, relaciones o señales no autorizan contacto, referidos ni aplicaciones. El registro siempre persiste `contact_authorization: not_granted_by_research`.
- Un cliente no identificado debe registrarse como `unknown` o `confidential`; no se adivina el nombre.
- Las actualizaciones agregan fuentes y conservan las señales históricas. Archivar no borra evidencia.

## Ejemplo de entrada privada

Guarda, fuera de Git, por ejemplo como `~/Documents/CareerCopilot/targets/acme-input.json`:

```json
{
  "company": "Acme Holdings",
  "role_families": ["Program Delivery", "PMO"],
  "candidate_preference": {
    "statement": "Quiero explorar roles de transformación empresarial aquí.",
    "declared_at": "2026-09-01"
  },
  "current_signals": [{
    "summary": "La página oficial de carreras lista roles de liderazgo de transformación.",
    "source_url": "https://careers.example.com/",
    "checked_at": "2026-09-01"
  }],
  "human_paths": [{
    "summary": "No se encontró un contacto confiable en la red propiedad de la persona candidata.",
    "source_url": "https://network.example.com/search",
    "checked_at": "2026-09-01",
    "status": "none_found"
  }],
  "relevant_units": ["Enterprise Technology"],
  "risks": ["La necesidad de contratación actual no está confirmada."],
  "questions": ["¿Qué unidad es responsable del portafolio de transformación?"],
  "next_research_action": "Verificar familias de puestos vigentes en el sitio oficial."
}
```

Para un cliente anónimo, no uses un nombre inventado:

```json
{
  "company": "",
  "client_identity": {"status": "confidential", "reason": "La reclutadora no reveló al cliente."}
}
```

Completa los demás campos requeridos como en el ejemplo anterior.

## Comandos

Crear o refrescar el registro privado:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/target_companies.py \
  --registry ~/Documents/CareerCopilot/targets/companies.json \
  --upsert ~/Documents/CareerCopilot/targets/acme-input.json \
  --as-of 2026-09-01
```

Revisar frescura sin modificar el registro. Los umbrales son independientes y explícitos:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/target_companies.py \
  --registry ~/Documents/CareerCopilot/targets/companies.json \
  --review --as-of 2026-09-15 \
  --company-stale-after-days 14 \
  --human-path-stale-after-days 7
```

Archivar una empresa conservando toda la evidencia previa:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/target_companies.py \
  --registry ~/Documents/CareerCopilot/targets/companies.json \
  --archive company-<stable-id> \
  --reason "Cambio de foco declarado por la persona candidata." \
  --as-of 2026-09-15
```

Las escrituras verifican que el destino esté fuera de Git, no use symlinks y aplique permisos `0700` al directorio y `0600` al archivo.
