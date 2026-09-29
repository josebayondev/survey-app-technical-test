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
