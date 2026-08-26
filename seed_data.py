"""
PulseCare Public Health & Rural Telemedicine Network - Comprehensive Data Seeder
Populates tiered public health facilities, frontline ASHA/CHO workers, specialists,
assisted teleconsultations, inter-facility referrals, high-risk maternal/NCD registries,
and cross-facility supply chain data.
"""
import json
import random
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash
from models import get_db_connection, init_db, DB_PATH
import os

def seed_database():
    print(f"Initializing Public Health Network Database at {DB_PATH}...")
    db_file = DB_PATH
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    init_db("schema.sql")
    conn = get_db_connection()
    cur = conn.cursor()

    # Clear existing data
    tables = [
        "audit_logs", "invoice_items", "invoices", "lab_order_items", "lab_orders",
        "facility_diagnostics", "lab_tests_catalog", "admissions", "beds", "wards",
        "pharmacy_dispenses", "prescription_items", "prescriptions", "facility_inventory",
        "medicines", "consultations", "appointments", "high_risk_registry",
        "referrals", "teleconsultations", "vitals", "patients", "users",
        "departments", "facilities", "hospital_settings"
    ]
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
        except Exception:
            pass
    try:
        cur.execute("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    print("Seeding Public Health System Settings...")
    settings = [
        ("hospital_name", "PulseCare National Public Health & Telemedicine Network"),
        ("tagline", "Equitable, Continuous & Specialist-Enabled Primary Healthcare for All"),
        ("hospital_code", "PCH-PUBHLTH-NET-01"),
        ("address", "District Health Administration Complex, Medical Enclave, Metro District"),
        ("phone", "+1 (800) 785-CARE"),
        ("emergency_hotline", "108 (National Health & Ambulance Emergency)"),
        ("email", "support@pulsecare-publichealth.gov"),
        ("currency", "$"),
        ("tax_rate", "0.0"), # Public healthcare is subsidized/free
        ("website", "https://pulsecare-publichealth.gov"),
        ("accreditation", "ABDM Integrated • IPHS Standards Certified • JCI Accredited"),
        ("registration_number", "REG-PUBHLTH-2026-NITI-881A")
    ]
    cur.executemany("INSERT INTO hospital_settings (key, value) VALUES (?, ?)", settings)

    print("Seeding Tiered Health Facilities (Sub-Centres, PHCs, CHCs, District Hospital)...")
    facilities_data = [
        (
            "Metro District Multi-Specialty Hospital", "DH-METRO-01", "District Hospital", "Metro District", "District Central Block", "100001",
            "+1-555-0100", "108 / 102", 1, 3, 60,
            "Cath Lab, 3T MRI, Digital X-Ray, 24x7 Blood Bank, Level 3 ICU, NICU, Dialysis Unit, Specialized OT, Central Pathology"
        ),
        (
            "Greenfield Community Health Centre & FRU", "CHC-GRN-02", "CHC", "Metro District", "Greenfield Rural Block", "100045",
            "+1-555-0200", "108", 1, 2, 30,
            "Emergency Resuscitation Bay, Labour Room, Digital X-Ray, Ultrasonography, Basic Hematology & Biochemistry Lab, Minor OT"
        ),
        (
            "Chandpur Primary Health Centre", "PHC-CHD-03", "PHC", "Metro District", "Chandpur Block", "100088",
            "+1-555-0300", "108", 1, 1, 6,
            "Teleconsultation Chamber, 24x7 Delivery Room, Cold Chain Vaccine Storage, Point-of-Care Diagnostic Kiosk, 6 Day-Care Observation Beds"
        ),
        (
            "Rampur Health & Wellness Centre - Sub-Centre", "SC-RMP-04", "Sub-Centre", "Metro District", "Chandpur Block", "100092",
            "+1-555-0400", "108", 1, 0, 2,
            "ASHA Assisted Teleconsultation Kit, Digital Blood Pressure Monitor, Fetal Doppler, Glucometer, Hemoglobinometer, Pulse Oximeter"
        ),
        (
            "Bilaspur Health & Wellness Centre - Sub-Centre", "SC-BLS-05", "Sub-Centre", "Metro District", "Greenfield Rural Block", "100049",
            "+1-555-0500", "108", 1, 0, 2,
            "Community Health Officer Teleconsult Station, Point-of-Care Blood & Urine Strips, Digital Vitals Monitor, First-Aid Emergency Box"
        )
    ]
    cur.executemany(
        """INSERT INTO facilities (name, facility_code, tier_type, district, block_taluk, pincode, contact_phone, emergency_helpline, teleconsult_enabled, ambulance_available, total_beds, equipment_summary)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        facilities_data
    )

    cur.execute("SELECT id, name, facility_code, tier_type FROM facilities")
    facility_map = {row["facility_code"]: row["id"] for row in cur.fetchall()}

    print("Seeding Clinical Departments...")
    departments_data = [
        ("Cardiology & Vascular Medicine", "CARD", "Specialist cardiac care, ECG review, Tele-cardiology", "Dr. Sarah Jenkins", "#dc3545"),
        ("Obstetrics, Gynecology & Maternal Care", "OBGYN", "High-Risk Pregnancy (HRP), Safe Delivery, Antenatal/Postnatal Care", "Dr. Anita Desai", "#d63384"),
        ("Pediatrics & Neonatal Health", "PED", "Child growth monitoring, Immunization, Infant nutrition, Pediatric teleconsult", "Dr. Elena Rostova", "#fd7e14"),
        ("General Medicine & Diabetology", "GENM", "Non-Communicable Diseases (NCD), Hypertension, Diabetes, Infectious disease", "Dr. Aisha Patel", "#198754"),
        ("Neurology & Stroke Triage", "NEUR", "Brain, Stroke early detection, Neurological evaluation", "Dr. Marcus Brody", "#6f42c1"),
        ("Emergency & Critical Referral Triage", "EMER", "108 Ambulance triage, acute trauma, toxicological emergencies", "Dr. Arthur Vance", "#ef4444"),
        ("Radiology & Teleradiology", "RAD", "X-Ray, Ultrasound tele-reporting", "Dr. Victor Stone", "#0dcaf0"),
        ("Community Health & Preventive Outreach", "COMM", "ASHA/ANM field surveillance, village health sanitation, NCD screening", "Sunita Devi", "#20c997")
    ]
    cur.executemany(
        "INSERT INTO departments (name, code, description, head_doctor_name, color) VALUES (?, ?, ?, ?, ?)",
        departments_data
    )
    cur.execute("SELECT id, name FROM departments")
    dept_map = {row["name"]: row["id"] for row in cur.fetchall()}

    default_pw = generate_password_hash("password123")

    print("Seeding Multi-Tiered Staff (Frontline ASHA/CHO, Medical Officers, District Specialists)...")
    users_data = [
        # 1. District Hospital CMO / Admin
        ("admin", default_pw, "Dr. Arthur Vance", "admin@pulsecare-publichealth.gov", "+1-555-0100", "admin", facility_map["DH-METRO-01"], dept_map["Emergency & Critical Referral Triage"], "Chief Medical Officer & District Health Director", "MD, MHA, FACS", "MED-LIC-00101", 0.0, "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=150"),
        # 2. District Hospital Specialists
        ("dr.sarah", default_pw, "Dr. Sarah Jenkins", "sarah.jenkins@pulsecare.org", "+1-555-0101", "doctor", facility_map["DH-METRO-01"], dept_map["Cardiology & Vascular Medicine"], "Senior Interventional Cardiologist & Tele-Cardiology Lead", "MD, FACC", "MED-LIC-00102", 0.0, "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150"),
        ("dr.anita", default_pw, "Dr. Anita Desai", "anita.desai@pulsecare.org", "+1-555-0106", "doctor", facility_map["DH-METRO-01"], dept_map["Obstetrics, Gynecology & Maternal Care"], "Consultant Obstetrician & High-Risk Pregnancy Specialist", "MS (OBG), DGO", "MED-LIC-00107", 0.0, "https://images.unsplash.com/photo-1594824813628-98e60473cf2b?w=150"),
        ("dr.elena", default_pw, "Dr. Elena Rostova", "elena.rostova@pulsecare.org", "+1-555-0103", "doctor", facility_map["DH-METRO-01"], dept_map["Pediatrics & Neonatal Health"], "Consultant Pediatrician & Child Health Specialist", "MD (Pediatrics)", "MED-LIC-00104", 0.0, "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150"),
        ("dr.marcus", default_pw, "Dr. Marcus Brody", "marcus.brody@pulsecare.org", "+1-555-0102", "doctor", facility_map["DH-METRO-01"], dept_map["Neurology & Stroke Triage"], "Consultant Neurologist", "MD, DM (Neuro)", "MED-LIC-00103", 0.0, "https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=150"),
        # 3. Rural PHC Medical Officer
        ("dr.rajesh", default_pw, "Dr. Rajesh Verma", "rajesh.verma@phc-chandpur.gov", "+1-555-0301", "medical_officer", facility_map["PHC-CHD-03"], dept_map["General Medicine & Diabetology"], "Medical Officer In-Charge - Chandpur PHC", "MBBS, DNB (Fam Med)", "MED-LIC-00301", 0.0, "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150"),
        # 4. Frontline Health Workers (ASHA & Community Health Officer - CHO)
        ("asha.sunita", default_pw, "Sunita Devi", "sunita.asha@subcentre-rampur.gov", "+1-555-0401", "asha_cho", facility_map["SC-RMP-04"], dept_map["Community Health & Preventive Outreach"], "Accredited Social Health Activist (ASHA Worker) - Rampur Village", "Certified Frontline Health Worker", "ASHA-REG-2024-88", 0.0, "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150"),
        ("cho.priya", default_pw, "Priya Sharma", "priya.cho@subcentre-bilaspur.gov", "+1-555-0501", "asha_cho", facility_map["SC-BLS-05"], dept_map["Community Health & Preventive Outreach"], "Community Health Officer (CHO) - Bilaspur HWC", "B.Sc Nursing, CPHC", "CHO-REG-2025-12", 0.0, "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=150"),
        # 5. Nurses, Pharmacists, Lab Techs, Reception
        ("nurse.clara", default_pw, "Clara Oswald", "clara.nurse@pulsecare.org", "+1-555-0107", "nurse", facility_map["DH-METRO-01"], dept_map["Emergency & Critical Referral Triage"], "Lead Inpatient & Triage Nurse", "BSN, RN", "NUR-LIC-00201", 0.0, "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=150"),
        ("pharm.robert", default_pw, "Robert Taylor", "robert.pharm@pulsecare.org", "+1-555-0110", "pharmacist", facility_map["DH-METRO-01"], None, "District Essential Medicine Logistics Officer", "PharmD", "PHM-LIC-00401", 0.0, "https://images.unsplash.com/photo-1556157382-97eda2d62296?w=150"),
        ("lab.lisa", default_pw, "Lisa Ray", "lisa.lab@pulsecare.org", "+1-555-0111", "lab_tech", facility_map["DH-METRO-01"], None, "Senior Pathologist & Teleradiology Coordinator", "MS MLS", "LAB-LIC-00501", 0.0, "https://images.unsplash.com/photo-1590650516494-0c8e4a4dd67e?w=150"),
        ("reception.emma", default_pw, "Emma Watson", "emma.helpdesk@pulsecare.org", "+1-555-0109", "receptionist", facility_map["DH-METRO-01"], None, "Helpdesk & Ayushman Mitra Coordinator", "BA Admin", "REC-LIC-00601", 0.0, "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150"),
        # 6. Patients
        ("patient.john", default_pw, "John Doe", "john.doe@rural.org", "+1-555-0201", "patient", facility_map["SC-RMP-04"], None, None, None, None, 0.0, "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"),
        ("patient.meena", default_pw, "Meena Devi", "meena.devi@rural.org", "+1-555-0202", "patient", facility_map["SC-RMP-04"], None, None, None, None, 0.0, "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150")
    ]
    cur.executemany(
        """INSERT INTO users (username, password_hash, full_name, email, phone, role, facility_id, department_id, specialization, qualification, license_number, consultation_fee, avatar_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        users_data
    )
    cur.execute("SELECT id, username, role FROM users")
    user_map = {row["username"]: row["id"] for row in cur.fetchall()}

    print("Seeding Wards & Beds across Network Facilities...")
    wards_data = [
        (facility_map["DH-METRO-01"], "Intensive Care Unit (ICU)", "ICU", "3rd Floor", 12, 0.0, "Level 3 Tertiary Telemetry & Ventilator ICU"),
        (facility_map["DH-METRO-01"], "Maternal & High-Risk Obstetric Ward", "Maternity", "2nd Floor", 16, 0.0, "Post-natal and high-risk ante-natal monitored beds"),
        (facility_map["DH-METRO-01"], "General Medicine Ward", "General Ward", "1st Floor", 20, 0.0, "Inpatient medical beds with oxygen manifolds"),
        (facility_map["CHC-GRN-02"], "Emergency Stabilization Bay", "Emergency", "Ground Floor", 6, 0.0, "Acute resuscitation beds with 108 ambulance transfer ramp"),
        (facility_map["CHC-GRN-02"], "Maternity & Newborn Care Unit", "Maternity", "1st Floor", 12, 0.0, "Institutional delivery & phototherapy unit"),
        (facility_map["PHC-CHD-03"], "Day Care Observation Unit", "General Ward", "Ground Floor", 6, 0.0, "Daytime hydration, nebulization & fever observation beds")
    ]
    cur.executemany(
        "INSERT INTO wards (facility_id, name, type, floor, total_beds, daily_rate, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
        wards_data
    )
    cur.execute("SELECT id, facility_id, name, total_beds FROM wards")
    wards_rows = cur.fetchall()

    beds_to_insert = []
    for w in wards_rows:
        prefix = "BED-"
        if "ICU" in w["name"]: prefix = "ICU-"
        elif "Matern" in w["name"]: prefix = "MAT-"
        elif "Emerg" in w["name"]: prefix = "EMER-"
        elif "Day" in w["name"]: prefix = "PHC-OBS-"
        else: prefix = "GEN-"

        for i in range(1, w["total_beds"] + 1):
            beds_to_insert.append((w["id"], f"{prefix}{i:02d}", "Available", None))
    cur.executemany("INSERT INTO beds (ward_id, bed_number, status, current_admission_id) VALUES (?, ?, ?, ?)", beds_to_insert)

    print("Seeding Essential Life-Saving Medicines Catalog & Cross-Facility Supply Chain...")
    medicines_data = [
        ("MED-001", "Anti-Snake Venom (Polyvalent)", "Polyvalent Snake Antivenom IP", "Antidotes & Emergency", "Injection Vial", "10 ml (Lyophilized)", 0.00, 150, 20, "ASV-2025-901", "2027-12-31", "Serum Institute", "Cold Chain Bay A", 1),
        ("MED-002", "Oxytocin Injection", "Oxytocin 10 IU/ml", "Maternal Health & Labor", "Injection Ampoule", "10 IU/ml", 0.00, 320, 40, "OXY-2025-412", "2027-08-15", "Bharat Biotech", "Cold Storage 02", 1),
        ("MED-003", "Magnesium Sulfate 50%", "Magnesium Sulfate Injection", "Maternal Health (Pre-eclampsia)", "Injection Ampoule", "50% w/v (5g/10ml)", 0.00, 180, 25, "MAG-2025-104", "2028-01-30", "Neon Labs", "Emergency Tray", 1),
        ("MED-004", "Lantus Insulin Pen", "Insulin Glargine (rDNA)", "Chronic NCD (Diabetes)", "Cartridge Pen", "100 IU/ml", 0.00, 95, 20, "LAN-2025-88", "2027-04-10", "Sanofi India", "Cold Storage 01", 1),
        ("MED-005", "Iron Folic Acid (IFA) Tablets", "Ferrous Sulfate + Folic Acid", "Maternal Health & Anemia", "Tablet", "100mg Elemental Iron + 500mcg FA", 0.00, 2500, 200, "IFA-2025-661", "2028-06-30", "Karnataka Antibiotics", "Rack A-01", 1),
        ("MED-006", "Oral Rehydration Salts (ORS)", "Sodium Chloride + Glucose + Potassium", "Child Health & Diarrhea", "Sachet (WHO Formula)", "20.5 g sachet", 0.00, 1800, 150, "ORS-2025-992", "2028-09-10", "FDC Pharma", "Rack A-02", 1),
        ("MED-007", "Zinc Sulfate Dispersible", "Zinc Sulfate 20mg", "Child Health & Nutrition", "Dispersible Tablet", "20 mg", 0.00, 900, 80, "ZIN-2025-331", "2027-11-20", "Cipla Public Health", "Rack A-03", 1),
        ("MED-008", "Amlodipine 5mg", "Amlodipine Besylate", "Chronic NCD (Hypertension)", "Tablet", "5 mg", 0.00, 1400, 100, "AML-2025-502", "2027-10-15", "Sun Pharma", "Rack B-01", 1),
        ("MED-009", "Metformin 500mg", "Metformin Hydrochloride", "Chronic NCD (Diabetes)", "Tablet", "500 mg", 0.00, 1600, 120, "MET-2025-774", "2027-12-05", "Cadila Health", "Rack B-02", 1),
        ("MED-010", "Amoxicillin 500mg", "Amoxicillin Trihydrate", "Essential Antibiotics", "Capsule", "500 mg", 0.00, 850, 90, "AMX-2025-112", "2027-05-18", "Alkem Labs", "Rack C-01", 1),
        ("MED-011", "Salbutamol Respirator Solution", "Salbutamol Sulfate", "Emergency Respiratory", "Respules", "2.5 mg / 2.5 ml", 0.00, 220, 30, "SAL-2025-48", "2027-03-22", "Cipla", "Emergency Bay", 1),
        ("MED-012", "Paracetamol 500mg", "Paracetamol IP", "Analgesic & Antipyretic", "Tablet", "500 mg", 0.00, 3000, 300, "PCM-2025-001", "2028-12-31", "GSK", "Rack A-04", 1)
    ]
    cur.executemany(
        """INSERT INTO medicines (code, brand_name, generic_name, category, form, strength, unit_price, stock_quantity, reorder_level, batch_number, expiry_date, manufacturer, location_rack, is_essential_life_saving)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        medicines_data
    )
    cur.execute("SELECT id, code FROM medicines")
    med_id_map = {row["code"]: row["id"] for row in cur.fetchall()}

    # Populate Cross-Facility Inventory (Showing realistic rural stock levels)
    facility_inventory_data = [
        # District Hospital (Full Stock)
        (facility_map["DH-METRO-01"], med_id_map["MED-001"], 80, 20, "2026-08-01"),
        (facility_map["DH-METRO-01"], med_id_map["MED-002"], 180, 30, "2026-08-01"),
        (facility_map["DH-METRO-01"], med_id_map["MED-003"], 100, 20, "2026-08-01"),
        (facility_map["DH-METRO-01"], med_id_map["MED-004"], 60, 15, "2026-08-01"),
        # CHC Greenfield (Adequate Emergency Stock)
        (facility_map["CHC-GRN-02"], med_id_map["MED-001"], 15, 10, "2026-07-20"),
        (facility_map["CHC-GRN-02"], med_id_map["MED-002"], 50, 20, "2026-07-20"),
        (facility_map["CHC-GRN-02"], med_id_map["MED-003"], 35, 15, "2026-07-20"),
        (facility_map["CHC-GRN-02"], med_id_map["MED-004"], 20, 10, "2026-07-20"),
        # Chandpur PHC (Essential Primary Stock)
        (facility_map["PHC-CHD-03"], med_id_map["MED-001"], 4, 5, "2026-07-15"), # Low stock alert at PHC!
        (facility_map["PHC-CHD-03"], med_id_map["MED-002"], 25, 15, "2026-07-15"),
        (facility_map["PHC-CHD-03"], med_id_map["MED-005"], 400, 100, "2026-07-15"),
        (facility_map["PHC-CHD-03"], med_id_map["MED-006"], 300, 80, "2026-07-15"),
        # Rampur Sub-Centre (ASHA Kit)
        (facility_map["SC-RMP-04"], med_id_map["MED-005"], 200, 50, "2026-08-10"),
        (facility_map["SC-RMP-04"], med_id_map["MED-006"], 150, 40, "2026-08-10"),
        (facility_map["SC-RMP-04"], med_id_map["MED-007"], 80, 20, "2026-08-10"),
        (facility_map["SC-RMP-04"], med_id_map["MED-012"], 250, 50, "2026-08-10"),
        # Bilaspur Sub-Centre
        (facility_map["SC-BLS-05"], med_id_map["MED-005"], 180, 50, "2026-08-05"),
        (facility_map["SC-BLS-05"], med_id_map["MED-006"], 120, 40, "2026-08-05"),
        (facility_map["SC-BLS-05"], med_id_map["MED-008"], 60, 20, "2026-08-05"),
        (facility_map["SC-BLS-05"], med_id_map["MED-009"], 80, 20, "2026-08-05")
    ]
    cur.executemany(
        """INSERT INTO facility_inventory (facility_id, medicine_id, stock_quantity, reorder_threshold, last_restocked)
           VALUES (?, ?, ?, ?, ?)""",
        facility_inventory_data
    )

    print("Seeding Lab Tests Catalog & Diagnostic Equipment Grid...")
    lab_catalog_data = [
        ("LAB-CBC", "Complete Blood Count & Differential (CBC)", "Hematology", 0.00, 2, "Whole Blood (EDTA)", json.dumps([{"name": "Hemoglobin", "unit": "g/dL", "ref_range": "12.0 - 16.0"}, {"name": "WBC Count", "unit": "10^3/uL", "ref_range": "4.0 - 11.0"}, {"name": "Platelets", "unit": "10^3/uL", "ref_range": "150 - 450"}]), "Assesses anemia, infection, and platelet count."),
        ("LAB-HBA1C", "Glycated Hemoglobin (HbA1c)", "Biochemistry", 0.00, 3, "Whole Blood", json.dumps([{"name": "HbA1c", "unit": "%", "ref_range": "< 5.7% Normal, >= 6.5% Diabetic"}]), "Quarterly monitoring for rural diabetic patients."),
        ("LAB-LIPID", "Comprehensive Lipid Profile", "Biochemistry", 0.00, 4, "Serum", json.dumps([{"name": "Total Cholesterol", "unit": "mg/dL", "ref_range": "< 200"}, {"name": "Triglycerides", "unit": "mg/dL", "ref_range": "< 150"}, {"name": "HDL", "unit": "mg/dL", "ref_range": "> 40"}]), "Cardiovascular risk evaluation."),
        ("LAB-USG-OBS", "Obstetric Ultrasound (Fetal Wellbeing & Dating)", "Radiology", 0.00, 1, "Radiological Sonogram", json.dumps([{"name": "Gestational Age", "unit": "Weeks", "ref_range": "By LMP"}, {"name": "Fetal Heart Rate", "unit": "bpm", "ref_range": "120 - 160"}, {"name": "Placental Location", "unit": "Position", "ref_range": "Fundal / Posterior (No Previa)"}]), "Critical maternal antenatal ultrasound scan."),
        ("LAB-ECG", "12-Lead Electrocardiogram (ECG)", "Cardiology", 0.00, 1, "Surface Bio-potential", json.dumps([{"name": "Cardiac Rhythm", "unit": "Observation", "ref_range": "Normal Sinus Rhythm"}, {"name": "ST Segment", "unit": "Observation", "ref_range": "Isoelectric, No Elevation"}]), "Point-of-care tele-ECG transmitted to District Cardiologist."),
        ("LAB-CXR", "Digital Chest X-Ray (PA View)", "Radiology", 0.00, 2, "Radiograph", json.dumps([{"name": "Lung Parenchyma", "unit": "Observation", "ref_range": "Clear, No Infiltrate / TB Cavitation"}]), "Diagnostic screening for TB and respiratory infections.")
    ]
    cur.executemany(
        """INSERT INTO lab_tests_catalog (code, name, category, cost, turnaround_hours, specimen_type, parameters_json, description)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        lab_catalog_data
    )
    cur.execute("SELECT id, code FROM lab_tests_catalog")
    test_id_map = {row["code"]: row["id"] for row in cur.fetchall()}

    # Cross-Facility Diagnostic Equipment Matrix
    facility_diagnostics_data = [
        # District Hospital (All functional)
        (facility_map["DH-METRO-01"], test_id_map["LAB-CBC"], 1, "Working", 1.0),
        (facility_map["DH-METRO-01"], test_id_map["LAB-HBA1C"], 1, "Working", 2.0),
        (facility_map["DH-METRO-01"], test_id_map["LAB-USG-OBS"], 1, "Working", 0.5),
        (facility_map["DH-METRO-01"], test_id_map["LAB-ECG"], 1, "Working", 0.2),
        (facility_map["DH-METRO-01"], test_id_map["LAB-CXR"], 1, "Working", 0.5),
        # Greenfield CHC
        (facility_map["CHC-GRN-02"], test_id_map["LAB-CBC"], 1, "Working", 1.5),
        (facility_map["CHC-GRN-02"], test_id_map["LAB-USG-OBS"], 1, "Working", 1.0),
        (facility_map["CHC-GRN-02"], test_id_map["LAB-ECG"], 1, "Working", 0.3),
        (facility_map["CHC-GRN-02"], test_id_map["LAB-CXR"], 1, "Working", 1.0),
        # Chandpur PHC
        (facility_map["PHC-CHD-03"], test_id_map["LAB-CBC"], 1, "Working", 2.0),
        (facility_map["PHC-CHD-03"], test_id_map["LAB-ECG"], 1, "Working", 0.2),
        (facility_map["PHC-CHD-03"], test_id_map["LAB-USG-OBS"], 0, "Under Maintenance", 0.0), # Ultrasound out of service at PHC
        # Rampur Sub-Centre
        (facility_map["SC-RMP-04"], test_id_map["LAB-CBC"], 1, "Working", 0.5), # Point of care Hemoglobin
        (facility_map["SC-RMP-04"], test_id_map["LAB-ECG"], 1, "Working", 0.2)  # Portable tele-ECG device
    ]
    cur.executemany(
        """INSERT INTO facility_diagnostics (facility_id, test_id, is_operational, equipment_status, average_wait_hours)
           VALUES (?, ?, ?, ?, ?)""",
        facility_diagnostics_data
    )

    print("Seeding Rural Patients with ABHA National Health IDs & High-Risk Cohorts...")
    patients_data = [
        (
            "PC-2026-0001", "91-4820-9182-3841", user_map["patient.john"], facility_map["SC-RMP-04"],
            "John", "Doe", "1978-04-12", "Male", "O+", "+1-555-0201", "john.doe@rural.org",
            "Rampur Village", "Rampur Gram Panchayat", "House #24, Near Primary School, Rampur",
            "Jane Doe", "+1-555-0299", "Spouse",
            "Penicillin", "Type 2 Diabetes Mellitus, Hypertension", "PM-JAY Scheme", "PMJAY-9948201", "PMJAY-AB-01",
            1, "Chronic NCD (Diabetes/HTN/COPD)", user_map["asha.sunita"], "Under Teleconsultation"
        ),
        (
            "PC-2026-0002", "91-7729-1029-4821", user_map["patient.meena"], facility_map["SC-RMP-04"],
            "Meena", "Devi", "1997-09-18", "Female", "B+", "+1-555-0202", "meena.devi@rural.org",
            "Rampur Village", "Rampur Gram Panchayat", "House #52, West Hamlet, Rampur",
            "Ramesh Kumar", "+1-555-0298", "Husband",
            "None", "28-Week Pregnancy, Gestational Hypertension, Severe Anemia (Hb 7.2)", "BPL", "BPL-MCH-4819", "RCH-MCH-9921",
            1, "Maternal High-Risk (HRP)", user_map["asha.sunita"], "Critical"
        ),
        (
            "PC-2026-0003", "91-5510-4491-0023", None, facility_map["PHC-CHD-03"],
            "Gopal", "Singh", "1956-02-20", "Male", "A+", "+1-555-0203", "gopal.singh@rural.org",
            "Chandpur Village", "Chandpur Panchayat", "Station Road, Chandpur",
            "Savitri Singh", "+1-555-0297", "Spouse",
            "Sulfa Drugs", "Acute Coronary Syndrome, CAD, Chronic Smoker", "PM-JAY Scheme", "PMJAY-881920", "PMJAY-AB-02",
            1, "Chronic NCD (Diabetes/HTN/COPD)", user_map["asha.sunita"], "Referred"
        ),
        (
            "PC-2026-0004", "91-9921-3382-7714", None, facility_map["SC-BLS-05"],
            "Aarav", "Kumar", "2024-03-10", "Male", "O+", "+1-555-0204", "parent.aarav@rural.org",
            "Bilaspur Village", "Bilaspur Panchayat", "North Tola, Bilaspur",
            "Radha Kumar", "+1-555-0296", "Mother",
            "None", "Severe Acute Malnutrition (SAM), Missed 9-Month Measles-Rubella Dose", "Antyodaya", "AAY-118290", "RCH-CH-4412",
            1, "Child Malnutrition & Immunization", user_map["cho.priya"], "Outpatient"
        ),
        (
            "PC-2026-0005", "91-3329-8812-5501", None, facility_map["PHC-CHD-03"],
            "Kamla", "Bai", "1968-11-04", "Female", "AB+", "+1-555-0205", "kamla.bai@rural.org",
            "Chandpur Village", "Chandpur Panchayat", "Near Temple, Chandpur",
            "Mohan Lal", "+1-555-0295", "Son",
            "None", "Chronic Obstructive Pulmonary Disease (COPD), Cataract", "BPL", "BPL-882910", "PMJAY-AB-03",
            1, "Chronic NCD (Diabetes/HTN/COPD)", user_map["asha.sunita"], "Outpatient"
        )
    ]
    cur.executemany(
        """INSERT INTO patients (patient_uid, abha_id, user_id, facility_id, first_name, last_name, dob, gender, blood_group, phone, email, village, panchayat, address, emergency_contact_name, emergency_contact_phone, emergency_contact_relation, allergies, chronic_conditions, socioeconomic_category, insurance_provider, insurance_policy_number, is_high_risk, high_risk_category, assigned_asha_id, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        patients_data
    )
    cur.execute("SELECT id, patient_uid, first_name, last_name FROM patients")
    pat_map = {row["patient_uid"]: row["id"] for row in cur.fetchall()}

    print("Seeding Point-of-Care Vitals & Digital Triage Scores...")
    vitals_data = [
        # Meena Devi - High-Risk Maternal Triage (Red Flag: BP 162/105, FHR 152, Hb 7.2)
        (pat_map["PC-2026-0002"], user_map["asha.sunita"], facility_map["SC-RMP-04"], 37.0, 98, 162, 105, 22, 97, 52.0, 154.0, 21.9, 110.0, 7.2, 152, "Red", "Pre-eclampsia danger sign: Severe headache, pedal edema 2+, BP markedly elevated. Initiating emergency assisted teleconsult with OBGYN specialist.", (datetime.now() - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")),
        # John Doe - NCD Follow-up (Yellow Flag: Sugar 230 mg/dL, BP 148/92)
        (pat_map["PC-2026-0001"], user_map["asha.sunita"], facility_map["SC-RMP-04"], 36.8, 82, 148, 92, 16, 98, 74.0, 172.0, 25.0, 230.0, 13.5, None, "Yellow", "Fasting blood sugar elevated. Teleconsult scheduled with Dr. Sarah/Diabetology.", (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        # Gopal Singh - Emergency Cardiac (Red Flag: BP 175/110, Pulse 110, SpO2 93%)
        (pat_map["PC-2026-0003"], user_map["dr.rajesh"], facility_map["PHC-CHD-03"], 37.2, 110, 175, 110, 24, 93, 68.0, 168.0, 24.1, 145.0, 12.8, None, "Red", "Substernal crushing chest pain. 12-Lead ECG uploaded showing ST elevation in II, III, aVF. 108 Ambulance dispatch requested for District Hospital.", (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")),
        # Aarav Kumar - Child Malnutrition (Yellow Flag: Weight 6.8kg @ 17m - Severely Underweight)
        (pat_map["PC-2026-0004"], user_map["cho.priya"], facility_map["SC-BLS-05"], 37.4, 115, 90, 60, 28, 99, 6.8, 72.0, 13.1, 85.0, 8.4, None, "Yellow", "Severe Acute Malnutrition (SAM). Mid-Upper Arm Circumference (MUAC) < 11.5 cm. Enrolled in Nutritional Rehabilitation Support.", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cur.executemany(
        """INSERT INTO vitals (patient_id, recorded_by_id, facility_id, temperature_c, heart_rate_bpm, blood_pressure_sys, blood_pressure_dia, respiratory_rate, spo2_percent, weight_kg, height_cm, bmi, blood_sugar_mgdl, hemoglobin_gdl, fetal_heart_rate, triage_color, notes, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        vitals_data
    )

    print("Seeding High-Risk Patient Surveillance Registry...")
    high_risk_data = [
        # Meena Devi - High-Risk Pregnancy
        (pat_map["PC-2026-0002"], "Maternal High-Risk (HRP)", "Severe Gestational HTN (BP 162/105), Severe Anemia (Hb 7.2 g/dL), Pedal Edema", 5, user_map["asha.sunita"], facility_map["SC-RMP-04"], date.today().strftime("%Y-%m-%d"), (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"), "Critical Escalation", "Immediate specialist teleconsult conducted. 108 Ambulance on standby for District Hospital Maternity referral."),
        # John Doe - Diabetic Neuropathy Risk
        (pat_map["PC-2026-0001"], "Chronic NCD (Diabetes/HTN/COPD)", "Uncontrolled Glycemia (HbA1c > 9.0), Stage 2 Hypertension", 3, user_map["asha.sunita"], facility_map["SC-RMP-04"], (date.today() - timedelta(days=5)).strftime("%Y-%m-%d"), (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"), "Active Surveillance", "Monthly home glucose logging by ASHA. Oral hypoglycemic dosage titration in progress."),
        # Aarav Kumar - SAM Child & Dropout
        (pat_map["PC-2026-0004"], "Child Malnutrition & Immunization", "Severe Acute Malnutrition (MUAC < 11.5cm), Missed Measles-Rubella MR-1 Vaccine", 4, user_map["cho.priya"], facility_map["SC-BLS-05"], (date.today() - timedelta(days=2)).strftime("%Y-%m-%d"), (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"), "Active Surveillance", "Energy Dense Nutritional Supplement (EDNS) provided. Immunization catch-up session scheduled at Bilaspur HWC.")
    ]
    cur.executemany(
        """INSERT INTO high_risk_registry (patient_id, category, risk_factors, severity_score, assigned_worker_id, facility_id, last_assessment_date, next_followup_date, status, clinical_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        high_risk_data
    )

    print("Seeding Assisted Teleconsultation Sessions...")
    teleconsults_data = [
        (
            "TELE-2026-001", pat_map["PC-2026-0002"], user_map["asha.sunita"], user_map["dr.anita"],
            facility_map["SC-RMP-04"], facility_map["DH-METRO-01"], "Emergency",
            "28-Week pregnant mother with sudden onset blurred vision, severe occipital headache, and BP 162/105 mmHg.",
            "Bilateral pitting pedal edema 2+, FHR 152 bpm regular. Hemocue Hb 7.2 g/dL. Urine protein positive.",
            "Administer initial loading dose of Labetalol 100mg PO stat. Fast-track emergency referral to District Hospital Obstetric ICU via 108 Ambulance.",
            "In-Call",
            json.dumps({"bp": "162/105", "fhr": 152, "hb": 7.2, "spo2": 97, "triage": "Red"}),
            (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            "TELE-2026-002", pat_map["PC-2026-0001"], user_map["asha.sunita"], user_map["dr.sarah"],
            facility_map["SC-RMP-04"], facility_map["DH-METRO-01"], "High-Risk",
            "Routine NCD Tele-review for chronic diabetes & exertional heaviness.",
            "Vitals stable, FBS 230 mg/dL. Tele-ECG within acceptable limits, no acute ST change.",
            "Titrate Metformin to 1000mg with dinner. Add Amlodipine 5mg morning. Continue lifestyle monitoring with ASHA.",
            "Completed",
            json.dumps({"bp": "148/92", "pulse": 82, "fbs": 230, "triage": "Yellow"}),
            (datetime.now() - timedelta(days=1, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]
    cur.executemany(
        """INSERT INTO teleconsultations (session_uid, patient_id, initiator_user_id, specialist_id, from_facility_id, target_facility_id, triage_level, chief_complaint, clinical_findings, specialist_advice, status, vitals_snapshot_json, scheduled_at, started_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        teleconsults_data
    )

    print("Seeding Inter-Facility Closed-Loop Referrals...")
    referrals_data = [
        # Gopal Singh: Chandpur PHC -> Metro District Hospital (Emergency Cardiac Referral)
        (
            "REF-2026-001", pat_map["PC-2026-0003"], facility_map["PHC-CHD-03"], facility_map["DH-METRO-01"],
            user_map["dr.rajesh"], user_map["dr.sarah"], "Cardiology & Cath Lab",
            "Acute Inferior Wall Myocardial Infarction requiring emergency primary coronary intervention (PCI).",
            "STEMI in Leads II, III, aVF. BP 175/110, pulse 110.", "Emergency - Red", "108 Ambulance", "In-Transit",
            (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(hours=1, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            None, "Awaiting arrival at District Hospital Emergency Bay. Cath Lab team activated.",
            user_map["asha.sunita"]
        ),
        # Meena Devi: Rampur Sub-Centre -> Metro District Hospital (High-Risk Obstetric Referral)
        (
            "REF-2026-002", pat_map["PC-2026-0002"], facility_map["SC-RMP-04"], facility_map["DH-METRO-01"],
            user_map["asha.sunita"], user_map["dr.anita"], "Obstetrics & High-Risk Pregnancy",
            "Severe Pre-eclampsia in third trimester with impending eclampsia symptoms.",
            "BP 162/105, proteinuria, severe headache.", "Emergency - Red", "108 Ambulance", "Initiated",
            (datetime.now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
            None, None, "ASHA worker Sunita Devi accompanying patient in ambulance.",
            user_map["asha.sunita"]
        ),
        # Past Completed Referral with Counter-Referral Back to ASHA
        (
            "REF-2026-000", pat_map["PC-2026-0001"], facility_map["SC-RMP-04"], facility_map["DH-METRO-01"],
            user_map["asha.sunita"], user_map["dr.sarah"], "Diabetology & Cardiology",
            "Suspected diabetic neuropathy and atypical exertional tightness.",
            "Elevated HbA1c 9.4%, normal stress ECG.", "Routine - Green", "Self / Private Vehicle", "Counter-Referred",
            (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=5, hours=-1)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=5, hours=-3)).strftime("%Y-%m-%d %H:%M:%S"),
            "Counter-Referral Plan: Patient stabilized. Prescribed oral Metformin + Amlodipine. ASHA Sunita to conduct weekly home BP check and monthly fasting blood sugar test.",
            user_map["asha.sunita"]
        )
    ]
    cur.executemany(
        """INSERT INTO referrals (referral_uid, patient_id, from_facility_id, to_facility_id, referring_doctor_id, receiving_specialist_id, specialty_needed, reason, provisional_diagnosis, triage_priority, transport_mode, status, initiated_at, accepted_at, attended_at, counter_referral_notes, assigned_followup_asha_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        referrals_data
    )

    print("Seeding Prescriptions, Invoices & Audit Trail...")
    # John Doe prescription
    cur.execute(
        """INSERT INTO prescriptions (prescription_number, patient_id, doctor_id, facility_id, status, special_instructions)
           VALUES ('RX-PUB-2026-001', ?, ?, ?, 'Dispensed', 'Take medications regularly. Follow up with ASHA worker Sunita Devi.')""",
        (pat_map["PC-2026-0001"], user_map["dr.sarah"], facility_map["SC-RMP-04"])
    )
    rx_id = cur.lastrowid
    cur.execute(
        """INSERT INTO prescription_items (prescription_id, medicine_id, dosage, frequency, duration_days, instructions, quantity_prescribed, quantity_dispensed, is_dispensed)
           VALUES (?, ?, '5 mg', '1-0-0 (Morning)', 30, 'Take with water after breakfast', 30, 30, 1)""",
        (rx_id, med_id_map["MED-008"])
    )

    # Invoices (Under Universal Public Health / PM-JAY 100% Subsidized)
    cur.execute(
        """INSERT INTO invoices (invoice_number, patient_id, facility_id, subtotal, total_amount, amount_paid, status, payment_method, notes)
           VALUES ('INV-PUB-2026-001', ?, ?, 0.00, 0.00, 0.00, 'Govt Subsidized (100%)', 'PM-JAY Scheme (Cashless)', 'Universal Public Health Care Coverage - Cashless Service under PM-JAY & State Health Mission')""",
        (pat_map["PC-2026-0001"], facility_map["SC-RMP-04"])
    )

    # Audit Logs
    audit_events = [
        (user_map["asha.sunita"], facility_map["SC-RMP-04"], "Teleconsult Requested", "Teleconsultation", "ASHA Sunita initiated emergency teleconsult TELE-2026-001 for high-risk maternal patient Meena Devi", "192.168.4.10", (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_map["dr.anita"], facility_map["DH-METRO-01"], "Teleconsult Connected", "Teleconsultation", "Specialist Dr. Anita Desai joined teleconsult room and advised immediate Labetalol loading dose", "192.168.1.15", (datetime.now() - timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_map["dr.rajesh"], facility_map["PHC-CHD-03"], "Referral Initiated", "Referrals", "Medical Officer Dr. Rajesh initiated emergency referral REF-2026-001 with 108 Ambulance dispatch for STEMI patient", "192.168.3.10", (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cur.executemany(
        """INSERT INTO audit_logs (user_id, facility_id, action, module, details, ip_address, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        audit_events
    )

    conn.commit()
    conn.close()
    print("Public Health Network database successfully initialized with rich rural & clinical dataset!")

if __name__ == "__main__":
    seed_database()
