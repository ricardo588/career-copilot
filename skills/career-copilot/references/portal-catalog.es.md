# Catálogo versionado de cobertura de portales

## Propósito y límite

Este catálogo es el registro de evidencia de las sugerencias locales de cobertura de portales de Career Copilot. **No** es un ranking de desempeño de mercado, una afirmación de disponibilidad vigente de vacantes, una garantía de compatibilidad ni una instrucción de consultar o usar un portal.

El producto devuelve sólo las entradas cuyas condiciones de perfil declarado coinciden con su heurística local. La persona puede seleccionar, modificar u omitir cualquier sugerencia. Career Copilot no abre, consulta, extrae, autentica, postula ni realiza ninguna otra acción en estos servicios.

La fuente canónica de una vacante individual sigue siendo el sitio de carrera o ATS de la empresa correspondiente. La recomendación `official_company_sites` es una política de seguridad del producto, documentada en el [roadmap v0.10.0](../../../docs/ROADMAP-0.10.0.md#safety-boundaries), no una afirmación de cobertura de mercado.

## Versión de catálogo `2026-09-07`

`onboarding.py` expone esta versión exacta como `catalog_version` y `evidence_checked_on` para cada portal sugerido. `evidence_url` es la fuente citada abajo. La evidencia sólo respalda la categoría de cobertura indicada.

| ID | Condición de cobertura declarada | Alcance respaldado por evidencia |
| --- | --- | --- |
| `linkedin` | Cobertura base de red profesional | LinkedIn documenta la búsqueda de empleos y la búsqueda por ubicación.[1] |
| `official_company_sites` | Cobertura base de fuentes canónicas | Política de seguridad del producto; ver límite anterior. |
| `occ_mundial` | México declarado | OCC publica una página de listados de empleo en México.[2] |
| `computrabajo` | México declarado | El portal México de Computrabajo expone cobertura de empleo por ubicación.[3] |
| `hireline` | Puesto tecnológico y México declarado | Hireline describe un portal de empleo tecnológico en México.[4] |
| `get_on_board` | Puesto tecnológico y Latinoamérica o remoto declarado | Get on Board presenta cobertura de empleo tecnológico en México y remoto.[5] |
| `behance` | Puesto o industria creativa declarada | Behance documenta filtros de Joblist por campo creativo, ubicación y tipo de empleo.[6] |
| `we_work_remotely` | Modalidad remota declarada | We Work Remotely publica una página de vacantes remotas.[7] |
| `upwork` | Tipo de empleo por contrato o freelance declarado | Upwork publica una página de trabajos freelance.[8] |
| `the_ladders` | Estados Unidos y seniority ejecutivo declarado | Ladders publica listados de búsqueda de puestos senior.[9] |
| `indeed` | Geografía aún no declarada | Indeed expone una búsqueda de empleo con campo de ubicación.[10] |

## Inventario de evidencia

- La ayuda oficial de LinkedIn documenta la búsqueda de empleos y resultados por ubicación.[1]
- La página oficial de OCC es una página de listados de empleo en México.[2]
- El portal México de Computrabajo lista cobertura de empleo por ubicación.[3]
- La página oficial de Hireline México describe cobertura de empleo tecnológico.[4]
- La página oficial de Get on Board México presenta cobertura de empleo tecnológico y remoto.[5]
- La ayuda oficial de Behance describe filtros de Joblist por campo creativo, ubicación y tipo de empleo.[6]
- We Work Remotely publica una página oficial de listados de vacantes remotas.[7]
- Upwork publica una página oficial de trabajos freelance.[8]
- Ladders publica listados de búsqueda de puestos senior.[9]
- Indeed expone una búsqueda de empleo con campo de ubicación.[10]

## Regla de mantenimiento

Antes de cambiar una entrada, vuelve a verificar su fuente oficial, actualiza la versión-fecha en `onboarding.py`, actualiza esta tabla y su contraparte en inglés, y agrega o revisa una prueba focalizada de onboarding. Si una fuente deja de respaldar el alcance documentado, limita o elimina la sugerencia. No infieras rankings, volumen, conversión, compatibilidad, elegibilidad ni disponibilidad en tiempo real a partir de este catálogo.

## Sources

[1] https://linkedin.com/help/linkedin/answer/a511260
[2] https://www.occ.com.mx/empleos/en-ciudad-de-mexico
[3] https://mx.computrabajo.com
[4] https://hireline.io/mx
[5] https://www.getonbrd.com.mx
[6] https://help.behance.net/hc/en-us/articles/360034476413-Guide-Applying-For-Jobs-On-Behance
[7] https://weworkremotely.com/remote-jobs
[8] https://www.upwork.com/freelance-jobs
[9] https://theladders.com/signup/all-jobs
[10] https://www.indeed.com
