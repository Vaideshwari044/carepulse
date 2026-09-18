# Decisions

## D001 — Refresh token storage and transport

**Status:** Confirmed for Phase 0 planning; table lands in Phase 1.

Access and refresh tokens are returned in the JSON body (not cookies). Refresh tokens are stored hashed in a `refresh_tokens` table with expiry and revoked fields. The frontend keeps tokens in memory and `localStorage` for session recovery.

## D002 — Patient identifier in routes

`/patients/{id}` uses the patient UUID. Vital ingestion continues to use `patient_code`.

## D003 — Health endpoint prefix

`GET /health` is served at the application root (`http://localhost:8000/health`). Remaining HTTP APIs use `/api/v1`.

## D004 — Frontend Docker server

Nginx is excluded by the specification. The frontend container runs the Vite development server on port 5173.

## D005 — Docker Compose environment defaults

`docker compose up` works without a committed `.env` file. Defaults live in `docker-compose.yml`. `.env.example` documents overrides. `.env` is gitignored.
