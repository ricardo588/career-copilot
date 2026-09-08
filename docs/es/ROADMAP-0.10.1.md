# Career Copilot 0.10.1 — Evidencia del catálogo de portales

Versión original en inglés: [docs/ROADMAP-0.10.1.md](../ROADMAP-0.10.1.md).

## Estado

**Entregada:** v0.10.1 agrega un contrato de evidencia fechado y con enlace de fuente a cada sugerencia de cobertura de portales del onboarding.

## Comportamiento entregado

1. **Sugerencias versionadas:** cada entrada de `portal_recommendations` incluye `catalog_version` y `evidence_checked_on`, ambos definidos en la versión de catálogo `2026-09-07`.
2. **Evidencia acotada:** cada entrada incluye `evidence_url` HTTPS y `evidence_scope`. El alcance describe únicamente la categoría de cobertura respaldada y rechaza explícitamente un ranking de mercado.
3. **Catálogo local completo:** las 11 entradas sugeridas actualmente se documentan con enlaces de fuentes oficiales en [el catálogo de portales](../../skills/career-copilot/references/portal-catalog.es.md), junto con su contraparte en inglés y una regla de mantenimiento.
4. **Base segura:** los sitios de carrera oficiales y ATS siguen siendo una recomendación de seguridad del producto para verificar fuente canónica, no una afirmación de cobertura de mercado.

## Límites de seguridad

- v0.10.1 no abre, consulta, extrae, autentica, postula ni realiza ninguna otra acción en LinkedIn, OCC, otro portal, sitio de carrera de empresa ni ATS.
- El catálogo no afirma disponibilidad en tiempo real, volumen, conversión, calidad del portal, compatibilidad de la persona, elegibilidad ni ranking.
- Los portales elegidos por la persona siguen siendo preferencias del workspace privado. El catálogo de evidencia contiene URLs de fuentes públicas y ningún dato de candidato.
- Las salvaguardas de `draft_only`, `confirm_each_external`, tracker, privacidad e importación de vacantes de sólo lectura no cambian.

## Actualización

No se requiere migrar datos privados. Los checkpoints de onboarding y perfiles finalizados existentes siguen siendo compatibles porque las sugerencias de portal son salida derivada de `status`. Los clientes que consumen objetos de recomendación deben preservar los nuevos campos de evidencia.

## Verificación manual requerida antes de publicar

Antes de publicar, ejecuta la suite completa de pruebas unitarias, validación del bundle, escaneo de privacidad, revisiones de diff Git, validación de citas de ambos catálogos, la demo sintética con cero acciones externas y una instalación desechable de perfil Hermes. CI ejecuta validación del bundle y pruebas unitarias; las verificaciones restantes son pasos locales deliberados de release.

## Diferido

- Adaptadores de adquisición directa desde portales, ATS o sitios de carrera.
- Normalizadores de exportación específicos por fuente más allá del contrato CSV genérico documentado.
- Evidencia de cobertura de mercado más amplia y renovada, fechada por fuente, más allá de este catálogo inicial.
- Escrituras automáticas al tracker, postulaciones, mensajes, contactos u otras acciones externas.
