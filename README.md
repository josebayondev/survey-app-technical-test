# Survey app: prueba técnica

Aplicación pequeña de encuestas multiempresa: backend en Django + Django REST Framework, frontend en Vue 3 y SQLite. El enunciado está en [`CANDIDATE_INSTRUCTIONS.md`](CANDIDATE_INSTRUCTIONS.md).

## Qué se ha hecho

| Tarea | PR |
|---|---|
| 1. Aislamiento entre organizaciones | [#1](https://github.com/josebayondev/survey-app-technical-test/pull/1) |
| 2. Webhook idempotente | [#2](https://github.com/josebayondev/survey-app-technical-test/pull/2) |
| 3. Filtro de fechas | [#3](https://github.com/josebayondev/survey-app-technical-test/pull/3) |

- Decisiones, riesgos conocidos y mejoras: [`SOLUTION.md`](SOLUTION.md).
- Uso de IA: [`AI_NOTES.md`](AI_NOTES.md).

## Cómo arrancarlo

Backend (requiere **Python ≥ 3.10**):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Frontend, en otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. El frontend entra siempre como `ana` / `ana123` (organización Northwind). Para probar el aislamiento contra la API está también `bob` / `bob123` (organización Contoso):

```bash
curl -u bob:bob123 http://127.0.0.1:8000/api/surveys/1/results/   # 404: la encuesta es de Northwind
```

## Tests

```bash
cd backend
python manage.py test        # 14 tests
python manage.py test -v 2   # muestra qué comprueba cada test ("Tarea N: ...")
```

## Cómo leer el historial

- Cada tarea tiene su rama y su PR. Dentro de cada PR, el primer commit (`test:`) reproduce el fallo con tests que fallan, y los siguientes lo arreglan. Así se puede ver el rojo y el verde por separado.
- Los PR se han integrado con merge commit, no con squash, para conservar esos pasos en `main`.
- **Las ramas no se han borrado tras el merge, a propósito**, para que el trabajo de cada tarea se pueda revisar por separado. En un proyecto real las borraría al mergear (por ejemplo, activando *Automatically delete head branches* en GitHub).
