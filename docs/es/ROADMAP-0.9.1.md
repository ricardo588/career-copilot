# Career Copilot 0.9.1 — Onboarding estratégico

Versión original en inglés: [docs/ROADMAP-0.9.1.md](../ROADMAP-0.9.1.md).

## Estado

**Entregada:** v0.9.1 agrega una fase privada y reanudable de estrategia de búsqueda al onboarding. Captura empresas objetivo opcionales y presenta sugerencias transparentes de cobertura de portales después de contar con puestos y geografía elegible declarados.

## Comportamiento entregado

1. **Empresas bajo control de la persona:** `search.target_companies` guarda una lista proporcionada por la persona en el checkpoint privado de onboarding y en las reglas privadas finalizadas.
2. **Portales bajo control de la persona:** `search.selected_job_portals` guarda los identificadores de portales elegidos. La persona puede ajustarlos, agregar alternativas o dejar la lista vacía.
3. **Sugerencias transparentes:** `status` devuelve `portal_recommendations` con ID, nombre y motivo. El catálogo inicial incluye LinkedIn y sitios oficiales de carrera, cobertura enfocada en México y adiciones para puestos tecnológicos cuando corresponde.
4. **Actualización conservadora:** los checkpoints existentes obtienen listas vacías de empresas objetivo y portales al reanudarse. No ocurre migración de datos de candidato, mutación del tracker ni solicitud externa.

## Límites de seguridad

- Las sugerencias son heurísticas locales de cobertura derivadas únicamente de puestos y geografía elegible declarados. No son un ranking vigente de desempeño de mercado.
- El nombre de una empresa objetivo expresa intención de la persona; no es evidencia de que contrata, un hecho verificado de la empresa ni autorización para investigar o contactar a alguien.
- Un portal seleccionado es una preferencia privada. v0.9.1 no consulta portales, obtiene vacantes, postula, edita perfiles públicos, contacta personas ni ejecuta acciones externas.
- Las salvaguardas existentes de `draft_only`, `confirm_each_external`, evidencia, privacidad y readback no cambian.

## Actualización

No se requiere migrar datos privados. Reanuda el onboarding normalmente; los checkpoints heredados reciben listas vacías `search.target_companies` y `search.selected_job_portals`. Los perfiles, reglas y trackers existentes siguen siendo compatibles hasta que se vuelva a finalizar el onboarding.

## Verificación manual requerida antes de publicar

Antes de publicar, ejecuta la suite completa de pruebas unitarias, validación del bundle, escaneo de privacidad, revisiones de diff Git, la demo sintética con cero acciones externas y una instalación desechable de perfil Hermes. CI actualmente ejecuta validación del bundle y pruebas unitarias; las verificaciones restantes son pasos locales deliberados de release.

## Diferido

- Descubrimiento de vacantes de sólo lectura desde portales seleccionados por la persona.
- Evidencia de cobertura de mercado con fecha y refrescable para regiones fuera del catálogo inicial.
- Conversión de una preferencia de empresa objetivo en un registro de investigación respaldado por evidencia.
- Cualquier postulación, comunicación, edición de perfil público u otra acción externa.
