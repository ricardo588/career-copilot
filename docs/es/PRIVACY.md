# Privacidad y modelo de amenazas

Versión original en inglés: [docs/PRIVACY.md](../PRIVACY.md).

## Público / distribuible

- Instrucciones y metodología del skill
- Plantillas vacías
- Scripts deterministas
- Fixtures sintéticos
- Pruebas y CI

## Privado / propiedad del usuario

- Identidad del candidato e información de contacto
- CV y documentos de respaldo
- Preferencias de compensación y registros privados de ofertas
- Contactos e historial de networking
- Evidencia del banco de historias, métricas, procedencia y preferencias de dirección de carrera
- Evidencia y autorización relacional, resultados de reuniones, reflexiones de debrief de entrevistas y borradores de negociación
- Notas de investigación de mercado, fechas de origen y IDs de mensajes
- Tracker vivo de vacantes/postulaciones
- Identificadores de cuentas, tokens y archivos de credenciales
- Sesiones de Hermes, memorias y exportaciones de perfil

## Límite de almacenamiento

El estado privado generado debe vivir en `career_copilot.workspace`, fuera tanto del repositorio fuente como del perfil instalado de Hermes. Un CV puede permanecer en la ruta local elegida por el candidato fuera de repositorios Git; el onboarding guarda la ruta y el estado de la propuesta confirmada sin copiar el CV. El script de onboarding rechaza espacios de trabajo dentro de la raíz de distribución/perfil o dentro de un árbol Git.

Hermes extrae el texto del CV desde el archivo local. Después, el contenido extraído es procesado por el proveedor de modelos configurado para ese perfil de Hermes, salvo que el usuario haya seleccionado un modelo local. El onboarding debe revelar ese límite antes de pedir el archivo. El punto de control almacena solo valores propuestos, etiquetas directas/inferidas y nombres de secciones de origen necesarias para la confirmación, no el texto completo del CV extraído. Por defecto no se usa ningún parser de documentos ni servicio OCR adicional.

Cada ejecución de bootstrap normaliza el espacio de trabajo privado y los directorios anidados a `0700`, y los archivos regulares a `0600`; se rechazan symlinks. Las propuestas del CV quedan vinculadas al contenido del archivo en staging con SHA-256 y no pueden confirmarse si el origen cambia en la misma ruta.

El `.gitignore` del repositorio bloquea artefactos privados comunes, pero las reglas de ignore son defensa en profundidad, no permiso para guardar archivos privados en el clon.

## Límite de acciones externas

En el modo `draft_only` por defecto, Career Copilot puede:

- analizar la información proporcionada;
- buscar/leer cuando esté autorizado;
- actualizar el estado privado local conforme a la política local;
- preparar borradores y vistas previas.

No puede, incluso si se aprobó el texto del borrador o se proporcionó `--apply`:

- postularse a un puesto;
- enviar o responder mensajes;
- publicar o modificar un perfil público;
- contactar a una persona;
- cambiar el estado de una hoja de cálculo o mensaje externo.

Otros usuarios pueden optar explícitamente por `confirm_each_external`. Ese modo sigue requiriendo confirmación fresca para el destino, el contenido y la acción exactos. Un perfil con `external_action_mode_locked: true` permanece en `draft_only`; el onboarding y el reset no pueden cambiarlo.

Human Path, la inteligencia relacional, la preparación de reuniones y la investigación de entrevistadores son siempre de solo lectura. Descubrir un contacto, reclutador, hiring manager o entrevistador no autoriza contacto, uso como referencia, lenguaje de recomendación, introducción ni seguimiento. El modo de debrief de entrevista no actualiza el tracker; cualquier seguimiento permanece como borrador.

Las mutaciones de adaptadores además requieren `--apply` y verificación de lectura posterior.

## Validación

Antes de cada lanzamiento:

```bash
PRIVATE_MARKERS='<comma-separated local identifiers>' python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
```

Usa identificadores solo mediante el entorno; nunca cometas la lista de marcadores.

## Respuesta a incidentes

Si datos privados se comprometen por accidente:

1. Detén el uso compartido del repositorio.
2. Rota de inmediato cualquier secreto expuesto.
3. Elimina los datos del historial de Git, no solo del archivo más reciente.
4. Vuelve a ejecutar el escáner de privacidad con los marcadores privados relevantes.
5. Revisa cachés remotos, forks, artefactos de Actions y logs.
6. Documenta la causa y agrega una prueba de regresión sin incrustar el valor filtrado.
