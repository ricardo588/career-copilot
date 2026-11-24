# Career Copilot 0.12.0 — Skills portables y selección de proveedores

Versión original: [docs/ROADMAP-0.12.0.md](../ROADMAP-0.12.0.md).

## Objetivo

Hacer que Career Copilot pueda usarse desde Hermes, Claude Code y OpenClaw mediante un contrato de skill portable y local-first. Ofrecer un paquete de guía para ChatGPT con el mismo proceso y límites de privacidad, sin afirmar ejecución local.

Agregar recomendaciones deterministas de proveedores a partir únicamente de puesto/familia declarados, seniority, geografía elegible, modalidad y tipo de empleo.

## Decisiones confirmadas

- Hosts ejecutables soportados en v0.12.0: Hermes, Claude Code y OpenClaw.
- ChatGPT recibe instrucciones y referencias solamente; no tiene acceso a workspace, scripts, credenciales, archivos locales ni acciones.
- Cobertura inicial: México, Latinoamérica, Estados Unidos y trabajo remoto.
- Greenhouse y Lever continúan como los únicos adaptadores públicos de lectura integrados. La persona candidata u operadora debe invocar explícitamente una lectura con un identificador confirmado.
- Las recomendaciones de proveedores son guía local de cobertura, nunca ranking de mercado, afirmación de vacante vigente ni autorización para consultar un proveedor.

## Arquitectura

### Núcleo portable

El núcleo portable contiene sólo `SKILL.md`, referencias, plantillas, scripts Python deterministas y ejemplos sintéticos. No contiene configuración de perfiles Hermes, credenciales de agentes ni datos de candidatos.

El skill portable requiere una ruta explícita de workspace privado, Python 3.11+ y un host capaz de ejecutar scripts locales. Toda ejecución permanece local salvo que se invoque explícitamente un adaptador de adquisición documentado.

### Adaptadores de host

- **Hermes:** `distribution.yaml`, configuración de profile e instalador existentes permanecen como adaptador opcional de Hermes.
- **Claude Code:** la instalación de skill de proyecto/usuario coloca el directorio portable en la ubicación documentada por Claude. No requiere integración con la API de Claude.
- **OpenClaw:** instala el mismo directorio portable bajo la raíz de skills documentada por OpenClaw. No añade herramientas externas específicas.
- **ChatGPT:** usa un documento de instrucciones separado. Puede guiar decisiones y generar comandos revisables, pero debe indicar que una persona u otro agente local debe ejecutarlos. Nunca solicita datos de candidatos para almacenarlos en el repositorio.

### Registro de proveedores

Un registro público y versionado guarda ID de proveedor, criterios de cobertura declarada, URL/fecha de evidencia, estado de adquisición y contrato seguro de invocación.

`provider_selection.py` consume sólo profile/rules privados y metadatos del registro. Devuelve proveedores seleccionados/no seleccionados con razones, desconocidos y requisito de acción explícita. No usa red, descubre identificadores, ni muta el tracker.

Un proveedor puede ser:

- `integrated_read_only`: existe un adaptador GET público probado por separado.
- `coverage_only`: puede sugerirse para revisión manual pero no tiene ruta de adquisición ejecutable.
- `not_supported`: no se devuelve como accionable.

## Límites de seguridad

- No hay credenciales, datos de candidato, identificadores board ni outputs privados en el repositorio.
- No hay descubrimiento, consulta, scraping, navegador, postulación, contacto ni escritura de tracker automática.
- Un proveedor ejecutable nuevo requiere contrato público verificado por separado, fixture sintético, validación de URL/identificador, política sin redirects, pruebas y documentación pareada.
- La documentación de cada host no debe describir herramientas no disponibles como si fueran ejecutables.

## Criterios de aceptación

- Un comando sintético de selección produce el mismo resultado con los mismos profile/rules/registro, sin red.
- México, Latinoamérica, Estados Unidos y remoto están representados por registros de evidencia versionados.
- Greenhouse y Lever siguen siendo lecturas públicas explícitas.
- Las instrucciones Hermes, Claude Code y OpenClaw identifican el mismo núcleo portable y no requieren credenciales.
- Las instrucciones ChatGPT declaran claramente que son sólo guía.
- Cada artefacto distribuible es sintético y pasa los validadores de privacidad y bundle.
