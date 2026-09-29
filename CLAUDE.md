# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Small multi-tenant survey app (part of a simulated SaaS): Django 5.1 + Django REST Framework backend, Vue 3 + Vite frontend, SQLite. The task statement lives in `CANDIDATE_INSTRUCTIONS.md`.

## Commands

Backend (from `backend/`, requires **Python ≥ 3.10** — Django 5.1 will not install on older versions):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # demo orgs, users, surveys and responses
python manage.py runserver      # http://127.0.0.1:8000
python manage.py test           # all tests
python manage.py test surveys.tests.SurveyApiTests.test_authorized_user_can_list_results  # single test
python manage.py makemigrations --check --dry-run   # detect missing migrations
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev     # http://localhost:5173, proxies /api to 127.0.0.1:8000
npm run build
```

There is no linter or formatter configured.

## Architecture

- Single Django app `surveys`; all API routes are mounted under `/api/` (`config/urls.py` → `surveys/urls.py`):
  - `GET /api/surveys/<id>/results/` — `SurveyResultsView`, authenticated users.
  - `POST /api/webhooks/responses/` — `ResponseWebhookView`, called by an external survey provider; no user auth, validated via the `X-Webhook-Token` header against `settings.WEBHOOK_TOKEN`.
- Tenancy model (`surveys/models.py`): `Organization` is the tenant. Users belong to organizations through `Membership` (unique per user+organization; a user can belong to several). `Survey` belongs to one `Organization`. `Response` belongs to a `Survey`; `external_id` holds the provider's event id, and the webhook finds the survey by `Survey.external_key`.
- DRF defaults (`config/settings.py`): Basic + Session authentication, `IsAuthenticated` by default. `TIME_ZONE = "UTC"`, `USE_TZ = True`, `LANGUAGE_CODE = "es-es"` (DRF validation messages come back in Spanish).
- Frontend is a single component (`src/App.vue`) that loads results for a fixed survey id through `src/api.js`, which sends Basic Auth credentials for the demo user.
- Tests are in `surveys/tests.py` and use DRF's `APIClient` with `force_authenticate`.

## Code conventions

Follow the existing style; do not introduce new patterns or libraries.

Backend:
- Double quotes, 4-space indentation, Black-style formatting (88-character lines; one argument per line with a trailing comma when a call does not fit).
- Imports: standard library, then Django, then DRF, then relative local imports (`from .models import ...`).
- Views are `APIView` subclasses (no viewsets/routers). DRF's `Response` is imported as `ApiResponse` because the model is also called `Response`.
- Input validation uses plain `serializers.Serializer` classes in `serializers.py` (like `WebhookSerializer`); output uses `ModelSerializer`.
- Model constraints are declared in `Meta.constraints` with an explicit `name` (e.g. `unique_membership`).
- Tests live in `surveys/tests.py`, inside `SurveyApiTests` (`TestCase`), using `APIClient`, hard-coded URL strings (`f"/api/surveys/{id}/results/"`), one behaviour per test named `test_<behaviour>` with a one-line docstring (`"""Tarea N: ..."""`, in Spanish), and arrange / act / assert blocks separated by blank lines.

Frontend:
- Vue 3 `<script setup>` with the Composition API (`ref`, `onMounted`), no extra libraries.
- HTTP calls live in `src/api.js` as exported `async` functions using `fetch`; errors are thrown as `Error`.
- Components handle `loading` / `error` refs with `try` / `catch` / `finally`.
- Plain CSS in the component's `<style>` block; double quotes and semicolons in JS.

## Demo data (`seed_demo`)

- `ana` / `ana123` → organization Northwind, survey id 1 "Customer satisfaction" (3 responses)
- `bob` / `bob123` → organization Contoso, survey id 2 "Employee NPS"
