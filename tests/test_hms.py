"""
PulseCare Hospital Management System - Automated Verification Test Suite
"""
import os
import sys
import unittest
import json
from datetime import date, datetime, timedelta

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from models import get_db_connection, init_db, query_db, execute_db
from seed_data import seed_database

class TestPulseCareHMS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Seed test database
        seed_database()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def test_01_database_seeded_properly(self):
        """Verify core tables have been populated with expected demo baseline."""
        users = query_db("SELECT COUNT(*) as c FROM users", one=True)["c"]
        self.assertGreaterEqual(users, 10, "Should have at least 10 staff/patient users")

        beds = query_db("SELECT COUNT(*) as c FROM beds", one=True)["c"]
        self.assertGreaterEqual(beds, 30, "Should have at least 30 beds configured")

        medicines = query_db("SELECT COUNT(*) as c FROM medicines", one=True)["c"]
        self.assertGreaterEqual(medicines, 15, "Should have at least 15 medicines in catalog")

        lab_tests = query_db("SELECT COUNT(*) as c FROM lab_tests_catalog", one=True)["c"]
        self.assertGreaterEqual(lab_tests, 8, "Should have at least 8 lab test catalog definitions")

    def test_02_authentication_and_role_login(self):
        """Verify authentication mechanism and role session initialization."""
        # Test valid login
        res = self.client.post("/login", data={"username": "dr.sarah", "password": "password123"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Dr. Sarah Jenkins", res.data)

        # Test invalid password
        res_fail = self.client.post("/login", data={"username": "dr.sarah", "password": "wrongpassword"}, follow_redirects=True)
        self.assertIn(b"Invalid username or password", res_fail.data)

    def test_03_patient_registration_and_ehr_lookup(self):
        """Verify patient creation and comprehensive 360 EHR record lookup."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["user_role"] = "admin"

        # Register new patient
        res = self.client.post("/patients/new", data={
            "first_name": "Alexander",
            "last_name": "Hamilton",
            "dob": "1990-01-11",
            "gender": "Male",
            "blood_group": "O+",
            "phone": "+1-555-9988",
            "email": "alex.hamilton@example.com",
            "address": "57 Wall St, New York, NY",
            "emergency_contact_name": "Elizabeth Hamilton",
            "emergency_contact_phone": "+1-555-9989",
            "emergency_contact_relation": "Spouse",
            "allergies": "Sulfa",
            "chronic_conditions": "Mild Hypertension",
            "insurance_provider": "Aetna",
            "insurance_policy_number": "AET-554433"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alexander Hamilton", res.data)

        # Verify in DB
        patient = query_db("SELECT * FROM patients WHERE first_name = 'Alexander'", one=True)
        self.assertIsNotNone(patient)
        self.assertTrue(patient["patient_uid"].startswith("PC-"))

        # Verify EHR view
        ehr_res = self.client.get(f"/patients/{patient['id']}")
        self.assertEqual(ehr_res.status_code, 200)
        self.assertIn(b"Electronic Health Record", ehr_res.data)

    def test_04_vitals_recording_and_bmi(self):
        """Verify vital signs recording and automatic BMI formula calculation."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Alexander'", one=True)
        res = self.client.post(f"/patients/{patient['id']}/vitals/new", data={
            "temperature_c": "37.2",
            "heart_rate_bpm": "74",
            "blood_pressure_sys": "122",
            "blood_pressure_dia": "82",
            "respiratory_rate": "16",
            "spo2_percent": "99",
            "weight_kg": "80",
            "height_cm": "180",
            "blood_sugar_mgdl": "95",
            "notes": "Normal baseline check"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify calculated BMI (80 / 1.8^2 = 24.7)
        vital = query_db("SELECT * FROM vitals WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(vital)
        self.assertAlmostEqual(vital["bmi"], 24.7, places=1)

    def test_05_appointment_booking_and_queue(self):
        """Verify OPD appointment booking, token dispatching, and queue display."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Alexander'", one=True)
        doctor = query_db("SELECT id FROM users WHERE username = 'dr.sarah'", one=True)
        today_str = date.today().strftime("%Y-%m-%d")

        res = self.client.post("/appointments/new", data={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "appointment_date": today_str,
            "appointment_time": "11:30 AM",
            "type": "Consultation",
            "reason": "Cardiovascular screening"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        apt = query_db("SELECT * FROM appointments WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(apt)
        self.assertGreater(apt["token_number"], 0)

        # Verify OPD queue display screen
        queue_res = self.client.get("/appointments/queue")
        self.assertEqual(queue_res.status_code, 200)
        self.assertIn(b"OPD QUEUE", queue_res.data)

    def test_06_clinical_consultation_prescription_and_lab_order(self):
        """Verify doctor consultation, SOAP note creation, linked e-prescription, and lab ordering."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2 # Dr. Sarah
            sess["user_role"] = "doctor"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Alexander'", one=True)
        med = query_db("SELECT id FROM medicines WHERE code = 'MED-003'", one=True) # Lipitor
        lab_test = query_db("SELECT id FROM lab_tests_catalog WHERE code = 'LAB-CBC'", one=True)

        res = self.client.post(f"/consultations/new?patient_id={patient['id']}", data={
            "symptoms": "Occasional exertional dyspnea",
            "diagnosis": "Hypercholesterolemia with atypical chest pain",
            "icd_code": "E78.00",
            "examination_notes": "Chest clear, normal cardiac rhythm",
            "treatment_plan": "Statin therapy, low cholesterol diet",
            "follow_up_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "med_id[]": [med["id"]],
            "dosage[]": ["20 mg"],
            "frequency[]": ["0-0-1 (Night)"],
            "duration_days[]": ["30"],
            "instructions[]": ["Take after dinner"],
            "quantity_prescribed[]": ["30"],
            "special_instructions": "Avoid grapefruit juice",
            "lab_test_ids[]": [lab_test["id"]],
            "lab_clinical_notes": "Evaluate lipid baselines"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check consultation inserted
        consult = query_db("SELECT * FROM consultations WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(consult)
        self.assertEqual(consult["icd_code"], "E78.00")

        # Check Prescription created
        rx = query_db("SELECT * FROM prescriptions WHERE consultation_id = ?", (consult["id"],), one=True)
        self.assertIsNotNone(rx)
        self.assertEqual(rx["status"], "Pending")

        # Check Lab Order created
        lab_order = query_db("SELECT * FROM lab_orders WHERE consultation_id = ?", (consult["id"],), one=True)
        self.assertIsNotNone(lab_order)
        self.assertEqual(lab_order["status"], "Ordered")

    def test_07_pharmacy_dispensing_and_inventory_decrement(self):
        """Verify pharmacy dispensing workflow and automatic stock deduction."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        # Find the pending prescription from previous test
        rx = query_db("SELECT * FROM prescriptions WHERE status = 'Pending' ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(rx)

        rx_item = query_db("SELECT * FROM prescription_items WHERE prescription_id = ?", (rx["id"],), one=True)
        med_before = query_db("SELECT stock_quantity FROM medicines WHERE id = ?", (rx_item["medicine_id"],), one=True)

        # Dispense prescription
        res = self.client.post(f"/pharmacy/dispense/{rx['id']}", data={
            f"dispense_qty_{rx_item['id']}": "30"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check prescription status is updated
        rx_after = query_db("SELECT status FROM prescriptions WHERE id = ?", (rx["id"],), one=True)
        self.assertEqual(rx_after["status"], "Dispensed")

        # Check medicine stock was deducted by 30
        med_after = query_db("SELECT stock_quantity FROM medicines WHERE id = ?", (rx_item["medicine_id"],), one=True)
        self.assertEqual(med_after["stock_quantity"], med_before["stock_quantity"] - 30)

    def test_08_laboratory_sample_collection_and_result_entry(self):
        """Verify lab specimen collection, test parameter entry, and verified report generation."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        lab_order = query_db("SELECT * FROM lab_orders WHERE status = 'Ordered' ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(lab_order)

        # Collect sample
        res_collect = self.client.post(f"/laboratory/order/{lab_order['id']}/collect", follow_redirects=True)
        self.assertEqual(res_collect.status_code, 200)

        # Enter results for test item
        item = query_db("SELECT * FROM lab_order_items WHERE lab_order_id = ?", (lab_order["id"],), one=True)
        res_result = self.client.post(f"/laboratory/item/{item['id']}/result", data={
            "param_name[]": ["Hemoglobin", "WBC"],
            "param_value[]": ["14.5", "6.8"],
            "param_unit[]": ["g/dL", "10^3/uL"],
            "param_range[]": ["13.5-17.5", "4.5-11.0"],
            "interpretation": "Normal hematological panel."
        }, follow_redirects=True)
        self.assertEqual(res_result.status_code, 200)

        # Check printable report
        report_res = self.client.get(f"/laboratory/report/{lab_order['id']}")
        self.assertEqual(report_res.status_code, 200)
        self.assertIn(b"Official Diagnostic Pathology Report", report_res.data)

    def test_09_ward_bed_occupancy_and_discharge(self):
        """Verify bed allocation, occupancy conflict prevention, and discharge release."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Alexander'", one=True)
        available_bed = query_db("SELECT id, bed_number FROM beds WHERE status = 'Available' LIMIT 1", one=True)
        doctor = query_db("SELECT id FROM users WHERE role = 'doctor' LIMIT 1", one=True)

        # Admit patient to bed
        res_admit = self.client.post("/wards/admit", data={
            "patient_id": patient["id"],
            "bed_id": available_bed["id"],
            "doctor_id": doctor["id"],
            "admission_reason": "Inpatient observation and telemetry"
        }, follow_redirects=True)
        self.assertEqual(res_admit.status_code, 200)

        # Bed should now be Occupied
        bed_check = query_db("SELECT status, current_admission_id FROM beds WHERE id = ?", (available_bed["id"],), one=True)
        self.assertEqual(bed_check["status"], "Occupied")

        # Discharge patient
        adm_id = bed_check["current_admission_id"]
        res_discharge = self.client.post(f"/wards/discharge/{adm_id}", data={
            "discharge_summary": "Patient fully recovered, vitals stable throughout admission stay.",
            "discharge_condition": "Recovered / Stable"
        }, follow_redirects=True)
        self.assertEqual(res_discharge.status_code, 200)

        # Bed should now be Available again
        bed_after = query_db("SELECT status, current_admission_id FROM beds WHERE id = ?", (available_bed["id"],), one=True)
        self.assertEqual(bed_after["status"], "Available")
        self.assertIsNone(bed_after["current_admission_id"])

    def test_10_billing_invoice_generation_and_payment(self):
        """Verify invoice creation with tax calculation, payment receipt, and ledger update."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_role"] = "admin"

        patient = query_db("SELECT id FROM patients WHERE first_name = 'Alexander'", one=True)

        # Generate invoice: Subtotal 200, Tax 5% (10), Discount 10, Total = 200 + 10 - 10 = 200. Paid: 200
        res_inv = self.client.post("/billing/new", data={
            "patient_id": patient["id"],
            "payment_method": "Credit Card",
            "tax_percent": "5.0",
            "discount_amount": "10.00",
            "amount_paid": "200.00",
            "item_type[]": ["Consultation", "Pharmacy"],
            "description[]": ["Specialist Consultation", "Medication Package"],
            "quantity[]": ["1", "1"],
            "unit_price[]": ["150.00", "50.00"],
            "notes": "Full settlement at discharge"
        }, follow_redirects=True)
        self.assertEqual(res_inv.status_code, 200)

        # Verify in DB
        invoice = query_db("SELECT * FROM invoices WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient["id"],), one=True)
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice["total_amount"], 200.00)
        self.assertEqual(invoice["status"], "Paid")

        # Verify printable invoice view
        inv_view_res = self.client.get(f"/billing/invoice/{invoice['id']}")
        self.assertEqual(inv_view_res.status_code, 200)
        self.assertIn(b"Medical Invoice", inv_view_res.data)

if __name__ == "__main__":
    unittest.main()
