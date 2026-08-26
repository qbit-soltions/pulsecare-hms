"""
PulseCare Public Health & Rural Telemedicine Network - Comprehensive Test Suite
Verifies:
1. Multi-tier Public Health Facility Network (Sub-Centre, PHC, CHC, District Hospital)
2. Frontline Health Worker (ASHA/CHO) Assisted Teleconsultations & Live Chamber
3. Specialist Teleconsultation Treatment Advice & Digital E-Prescriptions
4. 108 Emergency Ambulance Escalation Protocol & Triage
5. Inter-Facility Closed-Loop Referrals & ASHA Counter-Referrals
6. High-Risk Maternal (HRP), Child Malnutrition & Chronic NCD Registries
7. Cross-Facility Essential Drug & Diagnostic Equipment Availability
8. ABHA National Health ID & HL7 FHIR Clinical Bundle Export
9. Multilingual Localization Engine
10. Low-Connectivity Offline Record Synchronization API
"""
import unittest
import json
from datetime import date, datetime, timedelta
from app import app
from models import query_db, execute_db
from seed_data import seed_database

class TestPulseCarePublicHealthNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        seed_database()

    def setUp(self):
        self.client = app.test_client()

    def test_01_public_health_network_hierarchy(self):
        """Verify tiered public health facilities setup across Sub-Centres, PHCs, CHCs, and District Hospital."""
        facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")
        self.assertGreaterEqual(len(facilities), 4)

        tiers = [f["tier_type"] for f in facilities]
        self.assertIn("Sub-Centre", tiers)
        self.assertIn("PHC", tiers)
        self.assertIn("CHC", tiers)
        self.assertIn("District Hospital", tiers)

        # Check frontline workers exist
        asha = query_db("SELECT * FROM users WHERE role = 'asha_cho'", one=True)
        self.assertIsNotNone(asha)
        self.assertIn("Sunita", asha["full_name"])

    def test_02_frontline_worker_assisted_teleconsultation(self):
        """Verify ASHA worker can initiate an assisted teleconsultation with vitals snapshot from Sub-Centre."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7 # asha.sunita
            sess["user_role"] = "asha_cho"
            sess["facility_id"] = 4 # Rampur Sub-Centre

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Meena'", one=True)
        specialist = query_db("SELECT id FROM users WHERE username = 'dr.anita'", one=True)

        res = self.client.post("/teleconsult/new", data={
            "patient_id": patient["id"],
            "specialist_id": specialist["id"],
            "from_facility_id": "4",
            "target_facility_id": "1",
            "triage_level": "Emergency",
            "chief_complaint": "Severe headache and blurred vision in 28-week pregnancy",
            "clinical_findings": "BP 162/105, FHR 152 bpm regular, 2+ pedal edema",
            "vitals_bp": "162/105",
            "vitals_pulse": "98",
            "vitals_spo2": "97",
            "vitals_temp": "37.0"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify created teleconsult session
        tele = query_db("SELECT * FROM teleconsultations WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(tele)
        self.assertEqual(tele["triage_level"], "Emergency")
        self.assertIn("TELE-", tele["session_uid"])

    def test_03_teleconsultation_advice_and_prescription(self):
        """Verify District Specialist joins teleconsult room, records clinical advice, and issues digital e-prescription."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 3 # dr.anita
            sess["user_role"] = "doctor"
            sess["facility_id"] = 1 # District Hospital

        tele = query_db("SELECT * FROM teleconsultations ORDER BY id DESC LIMIT 1", one=True)
        med = query_db("SELECT id FROM medicines WHERE code = 'MED-003'", one=True) # Mag Sulfate

        res = self.client.post(f"/teleconsult/session/{tele['id']}/update", data={
            "specialist_advice": "Administer loading dose of Magnesium Sulfate 4g IV. Immediate transfer to District Obstetric ICU.",
            "status": "Completed",
            "med_id[]": [med["id"]],
            "dosage[]": ["4g IV"],
            "frequency[]": ["Stat Dose"],
            "duration_days[]": ["1"],
            "instructions[]": ["Over 15 minutes under ASHA supervision"],
            "quantity_prescribed[]": ["2"]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB updates
        tele_after = query_db("SELECT * FROM teleconsultations WHERE id = ?", (tele["id"],), one=True)
        self.assertEqual(tele_after["status"], "Completed")
        self.assertIsNotNone(tele_after["prescription_id"])

        rx = query_db("SELECT * FROM prescriptions WHERE id = ?", (tele_after["prescription_id"],), one=True)
        self.assertIsNotNone(rx)
        self.assertIn("RX-TELE-", rx["prescription_number"])

    def test_04_emergency_108_escalation_protocol(self):
        """Verify 108 Emergency Ambulance Escalation fast-tracks patient to District Hospital Emergency Bay."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7 # asha.sunita
            sess["user_role"] = "asha_cho"
            sess["facility_id"] = 4

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Meena'", one=True)
        res = self.client.post("/emergency/escalate", data={
            "patient_id": patient["id"],
            "from_facility_id": "4",
            "emergency_reason": "Severe Pre-eclampsia with impending eclampsia symptoms"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify emergency referral created with 108 Ambulance
        emer_ref = query_db("SELECT * FROM referrals WHERE patient_id = ? AND triage_priority = 'Emergency - Red' ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(emer_ref)
        self.assertEqual(emer_ref["transport_mode"], "108 Ambulance")
        self.assertEqual(emer_ref["to_facility_id"], 1) # District Hospital

    def test_05_closed_loop_referral_and_counter_referral(self):
        """Verify inter-facility referral initiation, specialist acceptance, and counter-referral instructions sent back to ASHA."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 6 # dr.rajesh (Medical Officer)
            sess["user_role"] = "medical_officer"
            sess["facility_id"] = 3 # Chandpur PHC

        patient = query_db("SELECT id FROM patients WHERE first_name = 'John'", one=True)
        asha = query_db("SELECT id FROM users WHERE username = 'asha.sunita'", one=True)

        # 1. Create Referral
        res = self.client.post("/referrals/new", data={
            "patient_id": patient["id"],
            "from_facility_id": "3",
            "to_facility_id": "1",
            "specialty_needed": "Diabetology & Cardiology",
            "reason": "Uncontrolled glycemic levels with peripheral neuropathy symptoms",
            "provisional_diagnosis": "Type 2 Diabetes with Neuropathy",
            "triage_priority": "Urgent - Yellow",
            "transport_mode": "Government Health Transport",
            "assigned_followup_asha_id": asha["id"]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        ref = query_db("SELECT * FROM referrals WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(ref)

        # 2. Specialist issues Counter-Referral Advice
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2 # dr.sarah
            sess["user_role"] = "doctor"

        res_counter = self.client.post(f"/referrals/{ref['id']}/status", data={
            "status": "Counter-Referred",
            "counter_referral_notes": "Patient stabilized on Metformin 1000mg. ASHA Sunita to conduct weekly home BP checks and monthly fasting glucose."
        }, follow_redirects=True)
        self.assertEqual(res_counter.status_code, 200)

        ref_after = query_db("SELECT * FROM referrals WHERE id = ?", (ref["id"],), one=True)
        self.assertEqual(ref_after["status"], "Counter-Referred")
        self.assertIn("ASHA Sunita", ref_after["counter_referral_notes"])

    def test_06_high_risk_maternal_and_ncd_registry(self):
        """Verify high-risk surveillance cohort enrollment and home visit logging."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7
            sess["user_role"] = "asha_cho"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Kamla'", one=True)
        follow_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")

        # Enroll in High-Risk Cohort
        res = self.client.post("/high-risk/new", data={
            "patient_id": patient["id"],
            "category": "Chronic NCD (Diabetes/HTN/COPD)",
            "risk_factors": "Severe COPD with exertional dyspnea, SpO2 93%",
            "severity_score": "4",
            "assigned_worker_id": "7",
            "facility_id": "3",
            "next_followup_date": follow_date,
            "clinical_notes": "Salbutamol nebulization provided at PHC. Monthly home follow-up."
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        hr_entry = query_db("SELECT * FROM high_risk_registry WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(hr_entry)
        self.assertEqual(hr_entry["severity_score"], 4)

        # Log follow-up visit
        res_fu = self.client.post(f"/high-risk/followup/{hr_entry['id']}", data={
            "status": "Controlled",
            "severity_score": "2",
            "next_followup_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "clinical_notes": "Home visit completed. Patient using inhaler properly, SpO2 improved to 96%."
        }, follow_redirects=True)
        self.assertEqual(res_fu.status_code, 200)

        hr_after = query_db("SELECT * FROM high_risk_registry WHERE id = ?", (hr_entry["id"],), one=True)
        self.assertEqual(hr_after["status"], "Controlled")
        self.assertEqual(hr_after["severity_score"], 2)

    def test_07_cross_facility_medicine_and_diagnostic_availability(self):
        """Verify cross-facility search for essential life-saving drugs and diagnostic equipment."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        # Search for Anti-Snake Venom across network
        res = self.client.get("/network/availability?q=Snake")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Anti-Snake Venom", res.data)
        self.assertIn(b"Metro District Multi-Specialty Hospital", res.data)

        # Search diagnostics
        res_diag = self.client.get("/network/availability")
        self.assertEqual(res_diag.status_code, 200)
        self.assertIn(b"Obstetric Ultrasound", res_diag.data)

    def test_08_abha_id_generation_and_fhir_export(self):
        """Verify 14-digit ABHA National Health ID generation and HL7 FHIR Bundle JSON export."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        patient = query_db("SELECT * FROM patients WHERE abha_id IS NOT NULL LIMIT 1", one=True)
        self.assertIsNotNone(patient["abha_id"])
        self.assertTrue(patient["abha_id"].startswith("91-"))

        # Test FHIR Bundle Export
        res_fhir = self.client.get(f"/api/patients/{patient['id']}/fhir")
        self.assertEqual(res_fhir.status_code, 200)
        self.assertEqual(res_fhir.content_type, "application/json")

        fhir_data = json.loads(res_fhir.data)
        self.assertEqual(fhir_data["resourceType"], "Bundle")
        self.assertEqual(fhir_data["type"], "document")
        self.assertEqual(fhir_data["entry"][0]["resource"]["resourceType"], "Patient")

    def test_09_multilingual_localization(self):
        """Verify multilingual translation filter and language switcher."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        # Switch to Hindi
        res_hi = self.client.get("/set-language/hi", follow_redirects=True)
        self.assertEqual(res_hi.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["lang"], "hi")

        # Switch to Tamil
        res_ta = self.client.get("/set-language/ta", follow_redirects=True)
        self.assertEqual(res_ta.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["lang"], "ta")

    def test_10_offline_data_sync_api(self):
        """Verify offline-cached records synchronization API for low-connectivity rural health workers."""
        patient = query_db("SELECT id FROM patients LIMIT 1", one=True)
        offline_payload = {
            "vitals": [
                {
                    "patient_id": patient["id"],
                    "recorded_by_id": 7,
                    "facility_id": 4,
                    "temp": 37.1,
                    "pulse": 80,
                    "sys": 130,
                    "dia": 85,
                    "spo2": 98,
                    "sugar": 120.0,
                    "triage": "Green",
                    "notes": "Offline field screening in remote hamlet"
                }
            ]
        }

        res = self.client.post("/api/sync/offline-records", data=json.dumps(offline_payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        res_data = json.loads(res.data)
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["synced_records"], 1)

if __name__ == "__main__":
    unittest.main()
