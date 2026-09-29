# Solución

## Decisiones

### 1. Aislamiento entre organizaciones
- La encuesta se busca por `pk` **y** por pertenencia del usuario (`organization__memberships__user=request.user`). El filtro se aplica en la consulta: no se carga la encuesta para comprobar el permiso después.
- Si el usuario no es miembro, la respuesta es **404 y no 403**, para no revelar que la encuesta existe.
- Un usuario de varias organizaciones ve las encuestas de todas; hay un test que lo protege.

### 2. Webhook idempotente
- La garantía está en la base de datos: `UniqueConstraint(survey, external_id)` (migración `0002`). Es lo que resuelve dos peticiones casi simultáneas; una comprobación previa en Python no basta porque ambas pueden leer "no existe" a la vez.
- La vista usa `get_or_create`: **201** si crea la respuesta y **200** con la existente si el evento ya había llegado. No capturo `IntegrityError` a mano porque Django ya lo hace dentro de `get_or_create`: si el `create` choca con la restricción, vuelve a leer la fila.
- La clave incluye la encuesta porque el `event_id` lo genera el proveedor y no tiene por qué ser único entre encuestas.
- Un reintento con datos distintos devuelve la respuesta original sin modificarla. Para un reintento, el primer evento recibido es el válido.

### 3. Filtro de fechas
- `from` y `to` son opcionales (`YYYY-MM-DD`) y se pueden usar juntos o por separado. Los extremos se incluyen y `to` abarca el día entero. Las fechas son días en UTC, la zona horaria del proyecto.
- Fechas inválidas: **400** con el mensaje de validación de DRF en el campo que falla (`from` o `to`). `from` posterior a `to` → 400. Un parámetro vacío se ignora.
- Primero se comprueba la organización (404) y después las fechas, para que un 400 no revele que existe una encuesta ajena.
- La validación está en un serializer, como el webhook. `from` es palabra reservada en Python, así que los campos se declaran en `get_fields()`.
- En el frontend, el backend es la fuente de verdad: no hay validación en el cliente y se muestra el mensaje del 400.

## Riesgos conocidos
- **Duplicados existentes:** como el fallo existía, una base de datos real probablemente ya tenga respuestas duplicadas, y la migración `0002` fallaría al crear la restricción. Antes de desplegarla haría una migración de datos que los elimine. No la he automatizado porque implica borrar datos y primero hay que acordar qué fila se conserva (la primera recibida, la más reciente o la `complete` si hay una `partial`).
- **Concurrencia real:** la carrera está probada con una simulación determinista, no con peticiones en paralelo. Con SQLite los hilos en tests son inestables. La protección real es la restricción de la base de datos.
- **Zona horaria:** el filtro trabaja con días en UTC y la tabla muestra la hora local del navegador. Cerca de medianoche, una respuesta puede aparecer en un día distinto al filtrado.

## Detectado fuera de alcance
No lo he tocado porque el enunciado no lo pide, pero lo corregiría:
- Credenciales `ana:ana123` fijas en `frontend/src/api.js`: no hay login real.
- `surveyId = 1` fijo en `App.vue`.
- `SECRET_KEY`, `DEBUG = True` y `WEBHOOK_TOKEN` fijos en `settings.py`. Irían en variables de entorno.
- El token del webhook se compara con `!=`, que no es una comparación en tiempo constante. Usaría `hmac.compare_digest` o, mejor, una firma HMAC del cuerpo de la petición.
- Los resultados no tienen paginación.
- El frontend solo muestra "Request failed with status X" para los errores que no son 400. Tampoco pluraliza ("1 responses").

## Mejoras con más tiempo
- Un manager o queryset `for_user(user)` para no repetir el filtro por organización en futuras vistas.
- Índice en `(survey, submitted_at)` para el filtro de fechas con muchos datos.
- Enviar la zona horaria del usuario para filtrar por su día local.
- Test de concurrencia real con peticiones en paralelo contra PostgreSQL.
- Tests de frontend (por ejemplo, Vitest) y CI que ejecute tests y build en cada PR.
