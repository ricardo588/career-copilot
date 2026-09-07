# Career Copilot 0.10.0 — Descubrimiento privado de vacantes

Versión original en inglés: [docs/ROADMAP-0.10.0.md](../ROADMAP-0.10.0.md).

## Alcance

v0.10.0 amplía el onboarding estratégico con dos capacidades privadas y deterministas:

1. Las sugerencias de cobertura de portales usan la familia de puesto, seniority, industria, geografía elegible, modalidad y tipo de empleo declarados por la persona.
2. Una exportación local JSON de vacantes elegida explícitamente puede generar un shortlist privado y de sólo lectura.

## Comportamiento entregado

1. **Recomendaciones bajo control de la persona:** onboarding pregunta opcionalmente industria y tipo de empleo. `status` devuelve `portal_recommendations` editables, cada una con ID, nombre y motivo.
2. **Cobertura, no ranking:** el catálogo incluye cobertura base profesional y de fuentes oficiales, además de sugerencias condicionales para México, tecnología, puestos o industrias creativas, trabajo remoto, trabajo por contrato o freelance y puestos senior en Estados Unidos. Son heurísticas locales, no afirmaciones sobre disponibilidad vigente, calidad del portal ni desempeño de mercado.
3. **Importación privada explícita:** `vacancy_discovery.py` lee únicamente la exportación local JSON indicada. Valida fuente seleccionada, frescura, URL canónica HTTP(S) y URLs canónicas duplicadas.
4. **Contexto trazable:** cada shortlist privado conserva el contexto declarado de puesto, seniority, industria, geografía, modalidad y tipo de empleo sin declarar silenciosamente que una vacante es compatible.
5. **Traspaso seguro:** un shortlist no es una escritura al tracker, vacante verificada, autorización de postulación ni autorización de acción externa. Cada entrada conservada requiere verificación en una fuente canónica antes de evaluarla o rastrearla posteriormente.

## Límites de seguridad

- v0.10.0 no consulta LinkedIn, OCC, ningún otro portal, sitio de carrera de empresa ni ATS.
- No se introducen credenciales, sesiones de navegador, scraping, llamadas API, contactos, postulaciones, ediciones de perfil público ni solicitudes externas.
- Las importaciones requieren un archivo local privado elegido explícitamente; los reportes deben estar fuera de repositorios Git y se escriben con permisos privados.
- Las empresas objetivo, portales seleccionados y reportes de shortlist permanecen en el workspace privado; las pruebas del repositorio usan sólo fixtures sintéticos.
- Se mantienen sin cambio las salvaguardas de `draft_only`, `confirm_each_external`, evidencia, privacidad y tracker.

## Actualización

No se requiere migrar datos privados. Los perfiles existentes ya admiten `target_industries` y `employment_types`; el onboarding reanudado ahora ofrece preguntas opcionales para esos campos. Los portales seleccionados y empresas objetivo existentes no cambian.

## Verificación manual requerida antes de publicar

Antes de publicar, ejecuta la suite completa de pruebas unitarias, validación del bundle, escaneo de privacidad, revisiones de diff Git, la demo sintética con cero acciones externas y una instalación desechable de perfil Hermes. CI ejecuta validación del bundle y pruebas unitarias; las verificaciones restantes son pasos locales deliberados de release.

## Diferido

- Adaptadores de adquisición directa desde portales, ATS o sitios de carrera.
- Soporte de importación CSV y normalizadores por fuente de exportación.
- Evidencia de cobertura de mercado vigente, fechada por fuente, fuera del catálogo local.
- Escrituras automáticas al tracker, postulaciones, mensajes, contactos u otras acciones externas.
