# Uso de IA

## Herramientas

- **Claude Code** (CLI) durante toda la prueba.
- Dos subagentes revisores de solo lectura (`.claude/agents/`), uno de backend y otro de frontend. Solo pueden leer archivos; revisan cada cambio contra el enunciado y las convenciones de `CLAUDE.md` antes de commitear.
- Los comandos de git (ramas, commits, push, PR) los ejecuté yo; la IA solo los proponía.

## Preparación

**Para qué la usé**
- Leer el enunciado y el código y localizar la causa de cada problema antes de tocar nada.
- Hacer un inventario de otros problemas que el enunciado no pide. No los toco; van a `SOLUTION.md`.
- Diagnosticar un error de entorno: mi Python por defecto era 3.8 y Django 5.1 necesita ≥ 3.10.
- Generar `CLAUDE.md` con `/init`.

**Qué revisé, modifiqué o descarté**
- CI con GitHub Actions: descartado, no lo pide el enunciado.
- `CLAUDE.md`: lo recorté para dejar solo información técnica.

**Cómo lo comprobé**
- Arranqué backend y frontend y vi las 3 respuestas de la demo.
- Reproduje el fallo de la tarea 1: `curl -u bob:bob123 .../api/surveys/1/results/` devolvía 200 con datos de otra organización.
- Ejecuté los tests existentes antes de cambiar nada: 2 en verde.

## Tarea 1: aislamiento entre organizaciones

**Para qué la usé**
- Escribir primero los tests que reproducen el fallo:
  - Un usuario pide una encuesta de otra organización → debe recibir 404.
  - Un usuario miembro de dos organizaciones → debe ver las encuestas de ambas (que el arreglo no bloquee a usuarios legítimos).
- El 200 del usuario autorizado ya lo cubría un test existente; lo reutilicé en vez de duplicarlo.
- Aplicar el arreglo: la encuesta se busca por `pk` y por pertenencia del usuario (`organization__memberships__user=request.user`). Si no es miembro, 404 en lugar de 403, para no revelar que la encuesta existe.

**Qué revisé, modifiqué o descarté**
- La IA escribió un test con un bucle y `subTest`, un patrón que no existe en el resto de tests. Lo reescribí con el mismo estilo que los existentes.
- Documenté las convenciones del código en `CLAUDE.md` para que las propuestas siguientes las respeten.
- El revisor de backend detectó una línea de 89 caracteres en los tests, fuera del estilo Black; la corregí.
- El revisor señaló que el test de varias organizaciones pasaría también sin el arreglo. Lo mantengo a propósito: protege frente a un arreglo que bloquee a usuarios legítimos.

**Cómo lo comprobé**
- Antes del arreglo, el test de otra organización falla (`200 != 404`): confirma el fallo.
- Después del arreglo, los 4 tests pasan.
- El revisor de backend confirmó que el filtro no puede devolver duplicados (`unique_membership`).
- Lo probé a mano con `curl` contra el servidor:
  - `bob` → encuesta de Northwind: 404. `bob` → la suya: 200.
  - `ana` → encuesta de Contoso: 404. `ana` → la suya: 200.
  - Sin credenciales: 401.

## Tarea 2: webhook idempotente

**Para qué la usé**
- Escribir primero los tests que reproducen el fallo:
  - El mismo evento enviado dos veces → debe haber 1 fila; la primera respuesta es 201 y la segunda 200 con la misma respuesta.
  - Un `create` duplicado directo → la base de datos debe lanzar `IntegrityError`.
  - Dos peticiones casi simultáneas → simulación determinista: la primera lectura no encuentra el evento (como si otra petición lo insertara justo después) y aun así el resultado es 200 y 1 fila.
  - El mismo `event_id` en otra encuesta → se crea (la clave es por encuesta).
- Aplicar el arreglo en dos capas:
  - Base de datos: `UniqueConstraint(survey, external_id)` con migración `0002`. Es lo que garantiza que no haya duplicados aunque lleguen dos peticiones a la vez.
  - Vista: `get_or_create` → 201 si se crea, 200 si ya existía.

**Qué revisé, modifiqué o descarté**
- Test de concurrencia con hilos reales: descartado. Con SQLite en tests es inestable ("database is locked"); la simulación prueba el mismo camino sin depender del tiempo.
- Capturar `IntegrityError` a mano en la vista: descartado. Comprobé en el código de Django 5.1 (`QuerySet.get_or_create`) que ya lo captura dentro de un `atomic` y vuelve a leer la fila.
- Migración para limpiar duplicados existentes antes de la restricción: descartada; no lo pide el enunciado y los datos de la demo no tienen duplicados. La menciono en `SOLUTION.md`.
- El revisor de backend confirmó que la simulación pasa por la rama `IntegrityError` → relectura de Django. Propuso comprobar que el parche llega a actuar (si no, el test pasaría por el camino normal); lo añadí como última comprobación, para que antes del arreglo el fallo siga siendo `201 != 200`.
- La migración generada usaba comillas simples y una cabecera con fecha; la dejé con el mismo formato que `0001`.

**Cómo lo comprobé**
- Antes del arreglo fallan 3 tests (`201 != 200` e `IntegrityError not raised`); el de otra encuesta pasa también sin el arreglo, a propósito.
- Con la restricción pero sin cambiar la vista, el duplicado da error 500 (`IntegrityError`): la base de datos protege, pero hace falta la vista para responder bien.
- Después del arreglo, los 8 tests pasan, también en orden aleatorio (`--shuffle`) y con otra zona horaria en la máquina.
- `sqlmigrate surveys 0002` muestra `UNIQUE ("survey_id", "external_id")` y `makemigrations --check` no detecta cambios pendientes.
- En una base de datos nueva: `migrate`, `seed_demo` y revertir a `0001` y volver a aplicar funcionan.
- Una fecha con zona horaria (`+02:00`) se guarda y se devuelve en UTC. Un reintento con datos distintos devuelve la respuesta original sin modificarla.
- Lo probé a mano con `curl`: el mismo evento dos veces → 201 y 200; la encuesta pasa de 3 a 4 respuestas, no a 5. Token incorrecto → 401.

## Tarea 3: filtro de fechas

**Para qué la usé**
- Definir primero el comportamiento y escribir los tests que lo fijan:
  - Solo `from`, solo `to` y los dos juntos. Los extremos se incluyen y `to` abarca el día entero: una respuesta a las 23:30 del día `to` entra.
  - Fecha inválida (`2025-02-30`) → 400 con el mensaje de DRF, que ya sale en español.
  - `from` posterior a `to` → 400 con un mensaje propio.
  - Encuesta de otra organización con una fecha inválida → 404. Primero se comprueba la organización y después las fechas, para que un 400 no revele que la encuesta existe.
- Backend:
  - `ResultsFilterSerializer` con dos `DateField` opcionales.
  - La vista filtra con `submitted_at__date__gte/lte`. Las fechas son días en UTC, la zona horaria del proyecto.
- Frontend:
  - Dos `<input type="date">` y un botón `Filter`.
  - `api.js` solo envía los parámetros que tienen valor. Si el backend responde 400, muestra sus mensajes.

**Qué revisé, modifiqué o descarté**
- `from` es palabra reservada en Python y no puede ser un atributo de clase. Descarté declarar el campo con otro nombre y `source="from"`, porque DRF lee la entrada por el nombre del campo. Lo resolví definiendo los campos en `get_fields()`.
- Validar las fechas en el cliente: descartado. El backend es la fuente de verdad y el 400 ya da un mensaje claro.
- Botón "Limpiar": descartado. Para quitar un filtro basta con vaciar el campo y volver a pulsar `Filter`.
- Los datos de prueba van en una encuesta nueva con fechas fijas. Así no toco el `setUp` ni el test existente que espera 1 respuesta, y los tests no dependen del día en que se ejecutan.
- Parámetro vacío (`?from=`): DRF lo trata como ausente y no filtra. Lo mantengo porque coincide con lo que hace el frontend.
- El revisor de backend detectó una línea de 91 caracteres en el serializer; la partí al estilo Black.
- El revisor de frontend no encontró nada que cambiar. Señaló dos cosas que documento en `SOLUTION.md`:
  - Si el usuario deja una fecha a medio escribir, el navegador envía el campo vacío y ese filtro se ignora.
  - El filtro usa días en UTC y la tabla muestra la hora local.
- Añadí a cada test nuevo un docstring de una línea (`"""Tarea N: ..."""`) para que se vea qué comprueba al ejecutar `test -v 2`. La IA propuso ponerlos en inglés; los dejé en español. Los tests originales no los toqué.

**Cómo lo comprobé**
- Antes del arreglo fallan 5 tests (devuelven todas las respuestas y `200 != 400`). El del 404 pasa también sin el arreglo, a propósito.
- Después del arreglo pasan los 14 tests, también en orden aleatorio (`--shuffle`). `makemigrations --check` no detecta cambios.
- Con la API: `2025-02-30`, `abc` y `2025-01-20T10:00` → 400 en `from`; `from` posterior a `to` → 400 en `to`.
- `npm run build` compila.
- En el navegador, con los datos de la demo:
  - Solo `from`, solo `to` y el rango devuelven las respuestas esperadas.
  - `from` posterior a `to` muestra "to: Debe ser igual o posterior a from.".
  - Vaciar los campos vuelve a mostrar todas las respuestas.
  - En la pestaña de red, cada petición lleva solo los parámetros con valor.

## Documentación final

**Para qué la usé**
- Redactar `README.md` y `SOLUTION.md` a partir de las decisiones y los riesgos que fui anotando en cada tarea.

**Qué revisé, modifiqué o descarté**
- Revisé que `SOLUTION.md` solo contara lo que está hecho y probado. Lo que no se implementó aparece como riesgo o mejora, no como hecho.
- Añadí al README que las ramas no se han borrado a propósito, para poder revisar cada tarea por separado.

**Cómo lo comprobé**
- Seguí el README desde cero en una copia limpia del repositorio: instalación, `migrate`, `seed_demo`, tests y `npm run build`.
- Revisé el enunciado punto por punto: código, migraciones, tests, `SOLUTION.md` y `AI_NOTES.md`.
