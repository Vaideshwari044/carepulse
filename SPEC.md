# CarePulse — Build Specification v2.1

## AI-Assisted Remote Patient Monitoring & Early-Warning Decision Support

**Tagline:** From isolated vital signs to intelligent deterioration patterns.

This file is the complete engineering specification. Follow it exactly. Execute one phase at a time. Never skip an exit gate. Never claim a gate passed without running it.

---

# PART 0 — HOW TO USE THIS SPECIFICATION

Maintain `PROGRESS.md` at the repository root. Read `SPEC.md` completely before writing code. A phase is complete only when code is written, executed, tests/verification run, real output observed, `PROGRESS.md` updated, changes committed, and the phase gate passes.

---

# PART 1 — ROLE AND MISSION

Build CarePulse, an AI-assisted remote patient monitoring and early-warning decision-support platform.

Priority: Functionality → Reliability → Explainability → Real-time experience → Honest framing → Visual polish.

The most important requirement is the genuine pipeline:

Synthetic Data → Simulator → POST /vitals → Validation → Data Quality → PostgreSQL → Sliding Window → Baseline → Feature Engineering → Trend → Rate of Change → Persistence → Multi-Parameter Analysis → Rule Risk Engine → ML Model → Risk Fusion → Risk State Machine → Explanation Engine → Alert Engine → WebSocket → React Dashboard → Human Action → Audit Log

---

# PART 2 — CLINICAL SAFETY LANGUAGE

CarePulse is an AI-assisted early-warning decision-support prototype. It is not a diagnostic device, not clinically validated, not a replacement for healthcare professionals, not intended for actual patient care, and not a treatment recommendation system.

Use: Possible physiological deterioration pattern detected. Clinical review recommended. AI-assisted early warning. Model classification confidence. Data confidence. Prototype engineering labels. Synthetic data.

Do not name diseases in demo output or alert messages.

Persistent safety footer on every page:

`Prototype — synthetic and replayed data — not clinically validated — not for patient care.`

---

# PART 3 — NO FAKE FUNCTIONALITY

No TODOs, NotImplementedError, buttons without handlers, frontend-generated risk/explanations/alerts, fake ML, fake WebSocket events, or static fixture endpoints pretending to be live.

---

# PART 4 — DEMO MODE

Synthetic data must travel through the complete real pipeline via HTTP POST /vitals. Do not inject demo readings directly into internal services.

---

# PART 5 — DEVELOPMENT RULES

1. Vertical slice first.
2. No silent substitutions. Use BLOCKER protocol.
3. Document decisions in `docs/decisions.md`.
4. Small conventional commits.
5. Update `PROGRESS.md` after every phase.

---

# PART 6 — P0 MANDATORY

Infrastructure, database, auth, patients, ingestion, analytics, risk, alerts, explainability, WebSocket, simulator (six scenarios, real HTTP), frontend core (login, dashboard, cards, charts, alerts, connection), human-in-loop, `docker compose up`.

ML training is P1. Model fallback is P0-critical.

---

# PART 7–9 — P1 / P2 / P3

P1: Random Forest, model persistence/version/fallback, hybrid fusion, data quality engine, patient detail, Alert Center, audit logs, AI Insights, feature importance, why-no-alert, reconnect, backend tests, landing page.

P2: Analytics, History, Settings, notifications, profile, Framer Motion polish.

P3: Three.js, SHAP, VitalDB/PhysioNet replay, frontend E2E. Public datasets must never block the project.

---

# PART 10 — TECHNOLOGY STACK

Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, asyncpg, python-jose, passlib[bcrypt], structlog.

ML: pandas, numpy, scikit-learn, joblib. SHAP is P3 only.

Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query v5, Zustand, Recharts, Lucide React, Framer Motion. Three.js is P3 only.

Infrastructure: Docker, Docker Compose, PostgreSQL 16.

---

# PART 11 — EXPLICITLY EXCLUDED

Do not add Redis, Kafka, Celery, Kubernetes, Nginx, RabbitMQ, MongoDB, a second database, another ORM, or another CSS framework. Background processing uses asyncio.

---

# PART 12 — PORTS

Frontend 5173, Backend 8000, PostgreSQL 5432.

WebSocket: `ws://localhost:8000/ws/monitoring?token=<jwt>`

---

# PART 13 — CONFIGURATION

All constants in `backend/app/core/config.py` via Pydantic Settings with env overrides.

```
WINDOW_SIZE_READINGS = 10
WINDOW_DURATION_SECONDS = 300
INGEST_INTERVAL_SECONDS = 5
BASELINE_MIN_SAMPLES = 20
BASELINE_MIN_DURATION_SEC = 600
BASELINE_ROLLING_WINDOW = 200
BASELINE_FREEZE_ABOVE_RISK = 40
RISK_STABLE_MAX = 24
RISK_EARLY_CHANGE_MAX = 49
RISK_WARNING_MAX = 74
ESCALATE_CONSECUTIVE = 2
DEESCALATE_CONSECUTIVE = 3
DEESCALATE_MARGIN = 8
MIN_STATE_DWELL_SECONDS = 60
PERSISTENCE_LOOKBACK = 6
PERSISTENCE_ALERT_MIN = 3
ALERT_COOLDOWN_SECONDS = 300
ALERT_DEDUP_WINDOW_SECONDS = 900
ALERT_AUTO_RESOLVE_STABLE_SECONDS = 600
STALE_AFTER_SECONDS = 30
MISSING_AFTER_SECONDS = 90
QUALITY_DEGRADED_BELOW = 0.80
INSUFFICIENT_DATA_BELOW = 0.50
W_ML = 0.45
W_RULE = 0.55
W_DEVIATION = 0.30
W_TREND = 0.20
W_RATE = 0.15
W_PERSISTENCE = 0.20
W_MULTIPARAM = 0.15
```

Startup asserts (with float tolerance): W_ML + W_RULE == 1 and rule component weights == 1.

---

# PART 14 — TIME

All backend/database timestamps UTC. PostgreSQL TIMESTAMPTZ. Simulator UTC. Frontend converts UTC → local only for display. Never mix naive and timezone-aware datetimes.

---

# PART 15 — DATABASE TABLES

users, patients, vital_readings, patient_baselines, feature_snapshots, risk_predictions, alerts, alert_actions, data_quality_events, audit_logs, model_versions, system_settings.

UUID PKs except patients.patient_code (P101, P102, …).

Vital readings: id, patient_id, recorded_at, ingested_at, heart_rate, spo2, respiratory_rate, systolic_bp, diastolic_bp, temperature, source, created_at. NUMERIC nullable; null means not measured.

Unique: (patient_id, recorded_at, source).

Indexes:

- vital_readings(patient_id, recorded_at DESC)
- risk_predictions(patient_id, computed_at DESC)
- alerts(status, priority DESC, created_at DESC)
- alerts(patient_id, signature, status)
- audit_logs(user_id, created_at DESC)
- data_quality_events(patient_id, created_at DESC)

Also: refresh_tokens table (hashed token, expiry, revoked) — confirmed decision D001.

---

# PART 16–17 — TRANSACTIONS AND CONCURRENCY

Ingestion transaction: validate → store vital → features → risk → store prediction → create/update alert → commit → then broadcast WebSocket. Per-patient asyncio.Lock is acceptable.

---

# PART 18–20 — PATIENTS, VITALS, VALIDATION

Patient fields: patient_code, display_name, monitoring_status, baseline_status, current_risk_score, current_risk_state, current_confidence, last_update. No real names.

Primary: HR, SpO2, RR. Secondary: SBP, DBP, temperature (half weight).

Hard-invalid ranges reject + INVALID quality event, never stored as valid vitals:

| Parameter | Concerning | Hard-invalid |
| HR | <50 or >100 | 20–250 |
| SpO2 | <94 | 50–100 |
| RR | <10 or >22 | 4–60 |
| SBP | <100 or >160 | 50–260 |
| DBP | <60 or >100 | 30–160 |
| Temp °C | <36.0 or >38.0 | 30–43 |

---

# PART 21–28 — ANALYTICS ENGINES

Baseline READY after 20 valid readings AND 600 seconds. Until then COLLECTING / INSUFFICIENT_DATA.

sd_floor: hr 3.0, spo2 1.0, rr 1.5, sbp 5.0, dbp 4.0, temp 0.2.

Do not update baseline when current risk score >= BASELINE_FREEZE_ABOVE_RISK.

Sliding window: max 10 readings, drop older than 300s, recoverable from PostgreSQL.

Trend: OLS, X = minutes, >= 4 non-null else UNKNOWN. S: hr 2.0, spo2 0.4, rr 0.8, sbp 3.0, dbp 2.0, temp 0.08. trend_strength = clamp(slope/S, -3, 3). Direction INCREASING/DECREASING/STABLE. Only concerning direction contributes to risk.

Rate: (current-previous)/max(minutes, 0.1); median of latest three pairwise rates; rate_severity = clamp(abs(rate)/(2S), 0, 1); concerning direction only.

Persistence: concerning if in band OR abs(z)>=2 in concerning direction. persistence_score = clamp(100 * consecutive_concerning / 3, 0, 100).

Multi-parameter concordance and multiparam_score per spec. Output: "Possible physiological deterioration pattern detected." Never diagnose disease.

Rule score: weighted deviation, trend, rate, persistence, multiparam with W_* weights, clamped 0–100.

---

# PART 29–32 — QUALITY, MISSING DATA, FUSION, CONFIDENCE

Quality statuses: GOOD, DEGRADED, STALE, MISSING, INVALID. Penalties as specified. Poor quality must never reduce physiological risk; it lowers confidence. quality_score < 0.50 or baseline not READY → display_state INSUFFICIENT_DATA while still storing risk_score.

If model READY: risk_score = 0.45 * ml_score + 0.55 * rule_score. Else risk_score = rule_score, model_status FALLBACK, model_confidence 0.50.

ml_score = 100*P(HIGH)+50*P(MODERATE)+0*P(LOW).

overall_confidence = 0.4 * model_confidence + 0.6 * data_confidence.

UI labels: Model classification confidence, Data confidence. Never "probability of illness".

---

# PART 33–34 — RISK STATE MACHINE

STABLE 0–24, EARLY_CHANGE 25–49, DETERIORATION_WARNING 50–74, HIGH_PRIORITY 75–100, plus RECOVERY and INSUFFICIENT_DATA.

Escalate: 2 consecutive above boundary. De-escalate: 3 consecutive below boundary-8. Min dwell 60s. Recovery when descending from WARNING or HIGH_PRIORITY with at least two primary parameters toward baseline. Every transition stores risk prediction and emits WebSocket. Flicker is a P0 bug.

---

# PART 35–37 — EXPLANATIONS

Server-generated, deterministic, template-based. No LLM. Fields: headline, what_happened, why_detected, contributors, baseline_delta, persistence, trend, data_quality, ml_contribution, recommendation.

Contributions from actual weighted score terms must sum to 100%.

GET /patients/{id}/risk/why-not returns negative evidence from the same feature snapshot.

---

# PART 38–42 — ALERTS AND HUMAN LOOP

Signature sha256(patient_id | alert_type | sorted(contributing_parameters) | risk_level). Dedup, cooldown, escalate, auto-resolve after 600s STABLE with AUTO_RECOVERY.

States: OPEN, ACKNOWLEDGED, REVIEWED, SNOOZED, ESCALATED, RESOLVED.

Actions: acknowledge, review, snooze, escalate, note, not-concerning, resolve. Persist user, timestamp, action, alert, note, response time.

Priority formula per spec. Age factor for unacknowledged alerts.

---

# PART 43–51 — ML (P1) AND FALLBACK (P0)

System must work without a model. Missing/failed model → FALLBACK, rule_score, no HTTP 500. Display: "AI model unavailable. Rule-based monitoring fallback is active."

Training: >=60 synthetic patients, >=500 readings, six scenarios, parquet under data/training/, reproducible seed. Labels from future 15-minute simulator state, not rule_score. Split by patient 60/20/20, chronological within patient. RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=20, class_weight="balanced", random_state=42). Persist models/rf_v1.joblib and models/rf_v1.json. feature_version = fv1.

---

# PART 52–59 — API, AUTH, CORS

Prefix /api/v1. Docs /docs. Error envelope `{ "error": { "code", "message", "details": {} } }`. No stack traces.

Auth: POST /auth/register, login, refresh, logout; GET /users/me.

Patients CRUD; DELETE ADMIN only, soft delete. Query: search, risk_level, status, page, size.

Vitals: GET patient vitals/baseline/risk/why-not/history/quality; POST /vitals and /vitals/batch.

Alerts action routes as specified. Analytics, model, monitoring demo controls, admin, GET /health at root.

Ingestion JSON contract and sources: simulator, dataset_replay, manual, device. At least one vital present. Idempotent on patient+recorded_at+source.

Authorization on backend. Password hashing, expiring tokens, refresh revocation, generic invalid-login, rate limiting. No frontend secrets. CORS from env; development http://localhost:5173; no allow_origins=["*"] in production-shaped config.

Route IDs: `/patients/{id}` is UUID (D002).

---

# PART 60–64 — WEBSOCKET

Unauthenticated close 4401. Events: VITAL_UPDATE, RISK_UPDATE, ALERT_CREATED, ALERT_UPDATED, ALERT_RESOLVED, PATIENT_STATUS_UPDATED, DATA_QUALITY_UPDATE, RECOVERY_UPDATE, SYSTEM_STATUS, DEMO_STATUS, PING.

Envelope: event, event_id, emitted_at, patient_code, payload.

Client: dedupe last 500 event_ids, reconnect with backoff 1,2,4,8,16,30s + jitter, refetch REST after reconnect.

Connection display: LIVE, RECONNECTING, OFFLINE. LIVE only if socket open AND heartbeat within 45s.

In-process connection manager, async fan-out, drop client if send queue > 100.

---

# PART 65–80 — FRONTEND

Routes: /, /login, /register, /dashboard, /patients, /patients/:id, /monitoring, /alerts, /analytics, /history, /ai-insights, /profile, /settings, /admin.

Design tokens, Inter, tabular numerals, accessibility (icon+text+color), prefers-reduced-motion, calm monitoring UI.

Reusable components listed in original spec. Patient cards, TanStack Query for server state, Zustand for UI only, centralized apiClient, loading/empty/error/success, error boundary, responsive including 390px.

Dashboard, patient detail, Alert Center, AI Insights, analytics pages as specified by priority.

---

# PART 81–86 — SIMULATOR AND DEMO

Six scenarios: Stable, Temporary variation, Gradual deterioration, Multi-parameter, Missing data, Recovery. Demo patients have READY baselines without bypassing the engine. Demo control panel on dashboard. POST /monitoring/demo/reset. Scenario switch requires reset/restart.

---

# PART 87 — PHASE 0 — SCAFFOLD

Create repo, docker-compose.yml, .env.example, .gitignore, README.md, backend, frontend.

Backend hello: /health. Frontend hello page.

Gate:

```bash
docker compose up -d
curl -s localhost:8000/health
```

Expected JSON. Open localhost:5173 and verify UI renders.

---

# PART 88–99 — LATER PHASES

Phase 1 Database. Phase 2 Auth + patients. Phase 3 Ingestion. Phase 4 Analytics engines + pytest tests/test_engines.py. Phase 5 Risk + alerts + WebSocket. Phase 6 Simulator. Phase 7 Frontend core. Phase 8 ML. Phase 9 Patient detail + Alert Center. Phase 10 Resilience. Phase 11 P2. Phase 12 Hardening.

Do not start a later phase until the previous gate passes.

---

# PART 100–106 — TESTING

Highest priority: tests/test_engines.py, test_alerts.py, test_auth.py, test_ingestion.py, test_ml.py, test_ws.py.

---

# PART 107–110 — DOCUMENTATION

README, docs/architecture.md, api.md, database.md, ml.md, dataset.md, demo.md, deployment.md, decisions.md, limitations.md. Honest ML and limitations language.

---

# PART 111 — SEED

Users: admin@carepulse.demo, clinician@carepulse.demo. Passwords from environment.

Patients: P101 Stable, P102 Temporary Variation, P103 Deterioration, P104 Recovery, P105 Missing Data. READY baselines.

---

# PART 112 — HEALTH

`/health` verifies subsystems. Missing ML model → model: fallback, status still ok if database is ok.

---

# PART 113–120 — SESSION, DATASET, 3D, OBSERVABILITY, PRIVACY, MODEL VERSIONING, SETTINGS, ERROR RECOVERY

Refresh restores auth or redirects to /login. Public dataset is P3. 3D is P3 with WebGL fallback. structlog; never log passwords/JWTs/secrets or vitals with patient identifiers at INFO. Synthetic data only. Predictions store model_version, feature_version=fv1, feature_vector, computed_at. system_settings seeded and validated. Controlled errors; never 500 because model missing; never fake healthy missing data.

---

# PART 121–124 — ACCEPTANCE, DEMO, JUDGING STORY

Acceptance test must pass twice from `docker compose down -v` then `docker compose up --build`. Five-minute demo. Six demo stories A–F as specified.

---

# PART 125 — KNOWN FAILURE MODES

Breadth over depth, frontend risk, alert spam, flicker, baseline poisoning, missing-as-healthy, ML leakage, circular ML, dataset rabbit hole, Docker-at-the-end, terminal-dependent demo, scattered thresholds, excessive animation, untested claims, clinical overclaiming, races, WS before commit, fake ML confidence, frontend secrets, broken session recovery.

---

# PART 126–132 — FILE STRUCTURE, DOCKER, ENV, PERFORMANCE, VALIDATION, BATCH, MODEL FAILURE

Target tree as specified. `docker compose up --build` starts frontend, backend, postgres. Health checks. Backend waits for PostgreSQL. .env.example includes DATABASE_URL, JWT_SECRET, token expiries, CORS_ALLOWED_ORIGINS, demo passwords, MODEL_PATH. Never commit .env.

Batch max 500 with per-item accepted/deduplicated/rejected.

---

# PART 133–134 — PROGRESS OUTPUT AND BLOCKERS

After each phase respond with PHASE N format. If blocked:

```
BLOCKER:
<exact problem>
OPTION A:
...
OPTION B:
...
```

---

# PART 135–138 — SCHEDULE AND DONE

24-hour plan. When time runs out: cut features, not quality. Build the real pipeline first.
