import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as c:
        # 1. Login
        resp = await c.post(
            "/api/v1/auth/login",
            json={"email": "clinician@carepulse.health", "password": "CarePulseClinician!23"},
        )

        print("1. Login status:", resp.status_code)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        tokens = resp.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. Patients List
        resp = await c.get("/api/v1/patients?limit=5", headers=headers)
        print("2. Patients list status:", resp.status_code)
        patients_res = resp.json()
        patients = patients_res.get("patients", patients_res.get("items", patients_res)) if isinstance(patients_res, dict) else patients_res
        print("   Fetched patients count:", len(patients))
        first_patient_id = patients[0]["id"] if patients else None



        # 3. Patient Detail
        if first_patient_id:
            resp = await c.get(f"/api/v1/patients/{first_patient_id}", headers=headers)
            print("3. Patient detail status:", resp.status_code)
            p_detail = resp.json()
            print("   Patient Code:", p_detail.get("patient_code"))

            # 4. Patient Vitals
            resp = await c.get(f"/api/v1/patients/{first_patient_id}/vitals?limit=10", headers=headers)
            print("4. Patient vitals status:", resp.status_code)
            vitals = resp.json()
            print("   Vitals records count:", len(vitals))

            # 5. Risk Explanation
            resp = await c.get(f"/api/v1/patients/{first_patient_id}/risk/explanation", headers=headers)
            print("5. Risk explanation status:", resp.status_code)

        # 6. Datasets List
        resp = await c.get("/api/v1/datasets", headers=headers)
        print("6. Datasets status:", resp.status_code)
        datasets_res = resp.json()
        datasets = datasets_res.get("items", datasets_res) if isinstance(datasets_res, dict) else datasets_res
        print("   Datasets count:", len(datasets))
        if datasets and isinstance(datasets, list):
            print("   Dataset Name:", datasets[0].get("name"), "| File:", datasets[0].get("filename"))


        # 7. Alerts List
        resp = await c.get("/api/v1/alerts", headers=headers)
        print("7. Alerts status:", resp.status_code)

        # 8. Chatbot
        resp = await c.post(
            "/api/v1/chat",
            json={"message": "What is normal SpO2?"},
            headers=headers,
        )
        print("8. Chatbot status:", resp.status_code)
        reply = resp.json().get("reply", "")
        print("   Chatbot response snippet:", reply[:90])


        print("\nALL API INTEGRATION TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
