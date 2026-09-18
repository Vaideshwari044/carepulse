import asyncio
import time
import httpx
import os
from sqlalchemy import text, select, func
from app.database import get_session_factory
from app.models import VitalReading, Patient, DatasetRecord, Alert

async def measure():
    print("=== BEFORE OPTIMIZATION PERFORMANCE BENCHMARK ===")
    
    # 1. Database Query Times
    factory = get_session_factory()
    async with factory() as db:
        t0 = time.perf_counter()
        count_rec = await db.scalar(select(func.count(DatasetRecord.id)))
        t_count_rec = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        # Query patient vitals ordered by recorded_at
        pt = (await db.execute(select(Patient).limit(1))).scalar_one_or_none()
        pt_id = pt.id if pt else None
        if pt_id:
            vitals = (await db.execute(select(VitalReading).where(VitalReading.patient_id == pt_id).order_by(VitalReading.recorded_at.desc()).limit(100))).scalars().all()
        t_vitals = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        # Query alerts filter by status
        alerts = (await db.execute(select(Alert).where(Alert.status == "OPEN").limit(50))).scalars().all()
        t_alerts = (time.perf_counter() - t0) * 1000

    print(f"DB DatasetRecords Count Query: {t_count_rec:.2f} ms (Rows: {count_rec})")
    print(f"DB Patient Vitals Query:       {t_vitals:.2f} ms")
    print(f"DB Alerts Filter Query:        {t_alerts:.2f} ms")

    # 2. API Response Times
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:

        # Login
        r_login = await client.post("/api/v1/auth/login", json={"email": "clinician@carepulse.health", "password": "CarePulseClinician!23"})
        token = r_login.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            ("/api/v1/analytics", "Dashboard Analytics API"),
            ("/api/v1/patients?page=1&size=20", "Patient List API"),
            (f"/api/v1/patients/{pt_id}" if pt_id else "/api/v1/patients", "Patient Detail API"),
            (f"/api/v1/patients/{pt_id}/vitals?limit=50" if pt_id else "/api/v1/vitals", "Patient Vitals API"),
            ("/api/v1/datasets", "Dataset Explorer API"),
            ("/api/v1/alerts", "Alerts API"),
            ("/api/v1/reports/summary", "Reports Summary API"),
            ("/api/v1/audit", "Audit Logs API"),
        ]

        print("\n--- API ENDPOINT RESPONSE TIMES ---")
        for ep, label in endpoints:
            t0 = time.perf_counter()
            r = await client.get(ep, headers=headers)
            dt = (time.perf_counter() - t0) * 1000
            print(f"{label:26s} [{ep:40s}]: {dt:.2f} ms (Status: {r.status_code})")

    # 3. Frontend Bundle Size
    dist_path = "C:\\Users\\gvish\\carepulse\\frontend\\dist\\assets"
    if os.path.exists(dist_path):
        js_files = [os.path.join(dist_path, f) for f in os.listdir(dist_path) if f.endswith(".js")]
        total_js_bytes = sum(os.path.getsize(f) for f in js_files)
        print(f"\nFrontend JS Bundle Total Size: {total_js_bytes / 1024:.2f} KB across {len(js_files)} file(s)")

if __name__ == "__main__":
    asyncio.run(measure())
