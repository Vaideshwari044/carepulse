# CarePulse — README

AI-assisted remote patient monitoring and early-warning **decision-support prototype**.

**Not a diagnostic device. Not clinically validated. Not for patient care. Uses synthetic and replayed data only.**

## Quick start

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Demo credentials

Configured via environment variables (`ADMIN_DEMO_PASSWORD`, `CLINICIAN_DEMO_PASSWORD`). Seeded users (Phase 1+):

- `admin@carepulse.demo`
- `clinician@carepulse.demo`

## Current phase

Phase 0 scaffold: Docker Compose, PostgreSQL, FastAPI `/health`, React hello page, safety footer.

## Limitations

Prototype engineering only. Thresholds are not clinically derived. No diagnosis. No treatment guidance.
