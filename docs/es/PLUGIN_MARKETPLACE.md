# Paquete de plugin para Hermes Marketplace

Versión original en inglés: [docs/PLUGIN_MARKETPLACE.md](../PLUGIN_MARKETPLACE.md).

## Estructura del paquete

La raíz del repositorio es un paquete portable Agent Plugins v1:

- `plugin.json` es el manifiesto raíz.
- `skills/career-copilot/` es el único árbol de runtime del skill; no se copia ni se vende por separado.
- Los scripts deterministas, plantillas vacías y fixtures sintéticos del skill siguen dentro de ese árbol.

El paquete no tiene `mcp.json`, `plugin.yaml`, entrypoint de Python, herramientas, hooks, middleware, servicio de ciclo de vida, cron, hook de instalación/red, telemetría, esquema de configuración, requisito de variable de entorno, requisito de secreto ni manifiesto de dependencias. Instalarlo no configura un proveedor de modelo ni requiere credenciales.

## Instalar, habilitar, deshabilitar y eliminar

Después de una admisión al catálogo de Marketplace, la ruta de instalación revisada será:

```bash
hermes plugins install career-copilot
hermes plugins enable career-copilot
hermes plugins disable career-copilot
hermes plugins remove career-copilot
```

Los paquetes portables se instalan deshabilitados por defecto. `enable` expone el skill con namespace en una nueva sesión de Hermes; no inicia un servicio ni concede capacidades. `disable` oculta el paquete sin eliminarlo. `remove` elimina solo el paquete instalado. No elimina un workspace de candidato, otros skills ni un perfil Hermes completo.

Antes de la admisión al catálogo, `career-copilot` no es un nombre de Marketplace y no debe presentarse como descubrible ni aprobado. Una persona que confíe en el repositorio puede usar la ruta documentada de Hermes para instalar desde Git, de preferencia fijada a un SHA completo publicado; esa ruta no equivale a revisión de catálogo.

## Convivencia y namespaces

Este paquete reutiliza directamente `skills/career-copilot/`. Hermes expone los skills de plugin bajo un namespace derivado del plugin (por ejemplo, `agent-plugin-career-copilot-<hash>:career-copilot`), por lo que no sobrescribe silenciosamente el skill `career-copilot` instalado por separado desde skills.sh.

Career Copilot tiene tres rutas de distribución distintas:

| Ruta | Alcance | Comportamiento de estado |
|---|---|---|
| Skill comunitario skills.sh | Instalación ligera y directa del skill | Skill instalado por separado; no comparte estado automáticamente. |
| Paquete de plugin Marketplace | Distribución revisada del plugin cuando sea admitida | Skill con namespace; sin privilegios extra ni árbol de runtime duplicado. |
| Perfil Hermes completo | Distribución de perfil aislado | Configuración y copia del skill en un perfil separado. |

Elige una ruta para el host previsto. Instalar más de una no sincroniza configuración ni estado de candidato. En todas las rutas, elige un workspace privado fuera del repositorio, de la instalación del plugin y del perfil del host.

## Privacidad, acciones e integraciones opcionales

El paquete contiene solo metodología, plantillas vacías, scripts deterministas y fixtures sintéticos. No contiene CVs de candidato, contactos, compensación, trackers, correo, credenciales, configuración de proveedores, estado de sesión ni exportaciones de perfiles.

`draft_only` sigue siendo la política predeterminada para acciones externas. El paquete no postula, envía mensajes, contacta personas, publica, altera un pipeline real, abre un login ni hace llamadas de red como efecto de instalarse o habilitarse. Google Sheets, Gmail y Obsidian son integraciones opcionales gobernadas por las instrucciones existentes del skill; cada una requiere configuración de la persona usuaria y autorización explícita. La configuración de un proveedor de modelo pertenece al host Hermes del usuario, nunca a este paquete.

## Protección para rollback y desinstalación

Deshabilita el plugin para revertir su disponibilidad preservando los archivos instalados, o elimínalo para borrar solo el paquete instalado. Ninguna operación elimina un workspace de candidato elegido por el usuario. Respalda o administra ese workspace privado por separado; de forma deliberada queda fuera del ciclo de vida del paquete.

## La validación no es admisión al catálogo

`hermes plugins doctor . --ci` valida localmente el paquete portable contra los contratos de runtime de Hermes. Las pruebas y escaneos de privacidad del repositorio validan este árbol fuente. Estas verificaciones no crean una entrada de catálogo, no publican una release, no reservan el nombre `career-copilot`, no vuelven el paquete buscable ni equivalen a revisión humana.

La admisión al catálogo ocurre después y por separado: una release publicada y autorizada aporta un SHA inmutable completo de 40 caracteres; una persona contribuidora autorizada envía entonces un PR de una sola entrada al repositorio de Hermes; la CI del catálogo valida ese árbol fijado; y un mantenedor lo revisa, acepta o rechaza. Hasta que ese PR se fusione, no existe una ficha oficial de Marketplace ni se puede afirmar descubribilidad.

Consulta [el proceso local de envío a catálogo](../../catalog-submission/README.md) para el registro de preparación que intencionalmente no se puede enviar.
