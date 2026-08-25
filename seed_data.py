"""
PulseCare Hospital Management System - Rich Data Seeder
Populates comprehensive, realistic healthcare data across all modules.
"""
import json
import random
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash
from models import get_db_connection, init_db, DB_PATH
import os

def seed_database():
    print(f"Initializing database at {DB_PATH}...")
    init_db("schema.sql")
    conn = get_db_connection()
    cur = conn.cursor()

    tables = [
        "audit_logs", "invoice_items", "invoices", "lab_order_items", "lab_orders",
        "lab_tests_catalog", "admissions", "beds", "wards", "pharmacy_dispenses",
        "prescription_items", "prescriptions", "medicines", "consultations",
        "appointments", "vitals", "patients", "users", "departments", "hospital_settings"
    ]
    for table in tables:
        cur.execute(f"DELETE FROM {table}")
    try:
        cur.execute("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    print("Seeding Hospital Settings...")
    settings = [
        ("hospital_name", "PulseCare Multispecialty Hospital & Research Institute"),
        ("tagline", "Excellence in Clinical Care & Compassion"),
        ("hospital_code", "PCH-METRO-01"),
        ("address", "742 Evergreen Healthcare Blvd, Medical District, NY 10001"),
        ("phone", "+1 (800) 785-7322"),
        ("emergency_hotline", "+1 (800) 911-PULSE"),
        ("email", "info@pulsecare-health.org"),
        ("currency", "$"),
        ("tax_rate", "5.0"),
        ("website", "https://pulsecare-health.org"),
        ("accreditation", "JCI & NABH Accredited Tertiary Care"),
        ("registration_number", "REG-HOSP-2026-9842A")
    ]
    cur.executemany("INSERT INTO hospital_settings (key, value) VALUES (?, ?)", settings)

    print("Seeding Departments...")
    departments_data = [
        ("Cardiology", "CARD", "Heart & Cardiovascular specialty, Cath Lab, Electrophysiology", "Dr. Sarah Jenkins", "#dc3545"),
        ("Neurology", "NEUR", "Brain, Spine, Stroke center, Neuro-critical care", "Dr. Marcus Brody", "#6f42c1"),
        ("Pediatrics", "PED", "Child healthcare, NICU, Pediatric Intensive Care", "Dr. Elena Rostova", "#fd7e14"),
        ("Orthopedics & Joint Surgery", "ORTH", "Bone, Joint Replacement, Sports Injury, Trauma", "Dr. David Chen", "#0d6efd"),
        ("General Medicine & Diabetology", "GENM", "Internal medicine, Infectious diseases, Chronic care", "Dr. Aisha Patel", "#198754"),
        ("Emergency & Critical Care", "EMER", "24x7 Level 1 Trauma & Emergency Resuscitation", "Dr. Arthur Vance", "#d63384"),
        ("Radiology & Imaging", "RAD", "CT Scan, 3T MRI, Digital X-Ray, Doppler Ultrasound", "Dr. Victor Stone", "#0dcaf0"),
        ("Pathology & Clinical Lab", "PATH", "Fully automated biochemical and hematological diagnostics", "Dr. Lisa Ray", "#20c997")
    ]
    cur.executemany(
        "INSERT INTO departments (name, code, description, head_doctor_name, color) VALUES (?, ?, ?, ?, ?)",
        departments_data
    )

    # Department IDs map
    cur.execute("SELECT id, name, code FROM departments")
    dept_map = {row["name"]: row["id"] for row in cur.fetchall()}

    default_pw = generate_password_hash("password123")

    print("Seeding Staff & Role Users...")
    users_data = [
        # Admin
        ("admin", default_pw, "Dr. Arthur Vance", "admin@pulsecare.org", "+1-555-0100", "admin", dept_map["Emergency & Critical Care"], "Chief Medical Officer & Administrator", "MD, MHA, FACS", "MED-LIC-00101", 300.0, "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=150"),
        # Doctors
        ("dr.sarah", default_pw, "Dr. Sarah Jenkins", "sarah.jenkins@pulsecare.org", "+1-555-0101", "doctor", dept_map["Cardiology"], "Senior Interventional Cardiologist", "MD, FACC, FSCAI", "MED-LIC-00102", 180.0, "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150"),
        ("dr.marcus", default_pw, "Dr. Marcus Brody", "marcus.brody@pulsecare.org", "+1-555-0102", "doctor", dept_map["Neurology"], "Consultant Neurologist & Stroke Specialist", "MD, DM (Neuro)", "MED-LIC-00103", 200.0, "https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=150"),
        ("dr.elena", default_pw, "Dr. Elena Rostova", "elena.rostova@pulsecare.org", "+1-555-0103", "doctor", dept_map["Pediatrics"], "Consultant Pediatrician & Neonatologist", "MD (Pediatrics), DCH", "MED-LIC-00104", 140.0, "https://images.unsplash.com/photo-1594824813628-98e60473cf2b?w=150"),
        ("dr.david", default_pw, "Dr. David Chen", "david.chen@pulsecare.org", "+1-555-0104", "doctor", dept_map["Orthopedics & Joint Surgery"], "Orthopedic Surgeon & Arthroscopy Specialist", "MS (Ortho), MCh", "MED-LIC-00105", 175.0, "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150"),
        ("dr.aisha", default_pw, "Dr. Aisha Patel", "aisha.patel@pulsecare.org", "+1-555-0105", "doctor", dept_map["General Medicine & Diabetology"], "Senior Physician & Diabetologist", "MD (General Medicine)", "MED-LIC-00106", 120.0, "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=150"),
        # Nurses
        ("nurse.clara", default_pw, "Clara Oswald", "clara.oswald@pulsecare.org", "+1-555-0107", "nurse", dept_map["Emergency & Critical Care"], "Critical Care Head Nurse (ICU)", "BSN, CCRN", "NUR-LIC-00201", 0.0, "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=150"),
        ("nurse.james", default_pw, "James Wilson", "james.wilson@pulsecare.org", "+1-555-0108", "nurse", dept_map["General Medicine & Diabetology"], "Senior Inpatient Staff Nurse", "BSN, RN", "NUR-LIC-00202", 0.0, "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=150"),
        # Receptionist
        ("reception.emma", default_pw, "Emma Watson", "emma.watson@pulsecare.org", "+1-555-0109", "receptionist", None, "Lead Front Desk & Patient Care Executive", "BA Healthcare Admin", "STF-LIC-00301", 0.0, "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150"),
        # Pharmacist
        ("pharm.robert", default_pw, "Robert Taylor", "robert.taylor@pulsecare.org", "+1-555-0110", "pharmacist", None, "Chief Clinical Pharmacist", "PharmD, RPh", "PHM-LIC-00401", 0.0, "https://images.unsplash.com/photo-1556157382-97eda2d62296?w=150"),
        # Lab Technician
        ("lab.lisa", default_pw, "Lisa Ray", "lisa.ray@pulsecare.org", "+1-555-0111", "lab_tech", dept_map["Pathology & Clinical Lab"], "Senior Clinical Pathologist & Lab Supervisor", "MS Medical Lab Science", "LAB-LIC-00501", 0.0, "https://images.unsplash.com/photo-1590650516494-0c8e4a4dd67e?w=150"),
        # Patient Portals
        ("patient.john", default_pw, "John Doe", "john.doe@email.com", "+1-555-0201", "patient", None, None, None, None, 0.0, "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"),
        ("patient.mary", default_pw, "Mary Smith", "mary.smith@email.com", "+1-555-0202", "patient", None, None, None, None, 0.0, "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150")
    ]
    cur.executemany(
        """INSERT INTO users (username, password_hash, full_name, email, phone, role, department_id, specialization, qualification, license_number, consultation_fee, avatar_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        users_data
    )

    # Doctor IDs map
    cur.execute("SELECT id, username, full_name FROM users WHERE role = 'doctor'")
    doc_map = {row["username"]: row["id"] for row in cur.fetchall()}
    cur.execute("SELECT id, username FROM users")
    user_id_map = {row["username"]: row["id"] for row in cur.fetchall()}

    print("Seeding Wards & Beds...")
    wards_data = [
        ("Intensive Care Unit (ICU)", "ICU", "3rd Floor, West Wing", 8, 450.0, "High-acuity 24/7 monitored telemetry beds with ventilator support"),
        ("Emergency Trauma Ward", "Emergency", "Ground Floor, Rapid Response", 6, 250.0, "Triage and acute resuscitation emergency bays"),
        ("General Ward - Male", "General Ward", "2nd Floor, Block A", 10, 85.0, "Multi-bed inpatient room with central oxygen and nursing stations"),
        ("General Ward - Female", "General Ward", "2nd Floor, Block B", 10, 85.0, "Multi-bed inpatient room with central oxygen and nursing stations"),
        ("Private Deluxe Suites", "Private Deluxe", "4th Floor, Premium Wing", 6, 320.0, "Single-occupancy private suite with ensuite washroom, attendant couch & TV"),
        ("Pediatric Inpatient Unit", "Pediatric", "3rd Floor, East Wing", 6, 120.0, "Child-friendly monitored beds with play area access")
    ]
    cur.executemany(
        "INSERT INTO wards (name, type, floor, total_beds, daily_rate, description) VALUES (?, ?, ?, ?, ?, ?)",
        wards_data
    )

    cur.execute("SELECT id, name, type, total_beds FROM wards")
    wards_rows = cur.fetchall()

    beds_to_insert = []
    for ward in wards_rows:
        prefix = {
            "ICU": "ICU-",
            "Emergency": "ER-",
            "General Ward": "GW-M-" if "Male" in ward["name"] else "GW-F-",
            "Private Deluxe": "PVT-",
            "Pediatric": "PED-"
        }.get(ward["type"], "BED-")
        for i in range(1, ward["total_beds"] + 1):
            bed_num = f"{prefix}{i:02d}"
            # Default all to Available, we'll assign active patients later
            beds_to_insert.append((ward["id"], bed_num, "Available", None))

    cur.executemany("INSERT INTO beds (ward_id, bed_number, status, current_admission_id) VALUES (?, ?, ?, ?)", beds_to_insert)

    print("Seeding Medicines...")
    medicines_data = [
        ("MED-001", "Augmentin 625", "Amoxicillin + Clavulanic Acid", "Antibiotics", "Tablet", "625 mg", 18.50, 240, 30, "AUG-2025-01", "2027-08-30", "GSK Pharma", "Rack A-01"),
        ("MED-002", "Panadol Extra", "Paracetamol + Caffeine", "Analgesics & Antipyretic", "Tablet", "500 mg", 4.20, 500, 50, "PAN-2025-99", "2028-02-15", "Haleon Health", "Rack A-02"),
        ("MED-003", "Lipitor", "Atorvastatin Calcium", "Cardiovascular", "Tablet", "20 mg", 22.00, 180, 25, "LIP-2024-88", "2027-11-20", "Pfizer", "Rack B-03"),
        ("MED-004", "Glucophage XR", "Metformin Hydrochloride", "Antidiabetic", "Tablet", "1000 mg", 12.80, 320, 40, "GLU-2025-44", "2027-06-10", "Merck KGaA", "Rack B-04"),
        ("MED-005", "Ventolin Evohaler", "Salbutamol Inhaler", "Respiratory", "Inhaler", "100 mcg", 15.00, 75, 15, "VEN-2025-12", "2027-04-18", "GSK", "Rack C-01"),
        ("MED-006", "Nexium", "Esomeprazole Magnesium", "Gastrointestinal / Antacid", "Capsule", "40 mg", 19.50, 210, 30, "NEX-2025-07", "2028-01-05", "AstraZeneca", "Rack C-02"),
        ("MED-007", "Norvasc", "Amlodipine Besylate", "Antihypertensive", "Tablet", "5 mg", 11.00, 160, 20, "NOR-2025-33", "2027-09-12", "Pfizer", "Rack B-05"),
        ("MED-008", "Ceftriaxone Inj", "Ceftriaxone Sodium", "Antibiotics", "Injection", "1 g Vial", 28.00, 95, 20, "CEF-2024-55", "2026-12-31", "Roche", "Cold Storage 01"),
        ("MED-009", "Lantus SoloStar", "Insulin Glargine (rDNA)", "Antidiabetic", "Injection Pen", "100 units/ml", 45.00, 60, 15, "LAN-2025-10", "2027-03-25", "Sanofi", "Cold Storage 02"),
        ("MED-010", "Zofran", "Ondansetron HCl", "Antiemetic", "Tablet", "4 mg", 14.20, 110, 20, "ZOF-2025-03", "2027-10-15", "Novartis", "Rack D-01"),
        ("MED-011", "Brufen 400", "Ibuprofen", "NSAID / Anti-inflammatory", "Tablet", "400 mg", 6.50, 400, 50, "BRU-2025-19", "2028-05-10", "Abbott", "Rack A-03"),
        ("MED-012", "Zithromax", "Azithromycin", "Antibiotics", "Tablet", "500 mg", 21.00, 140, 25, "ZIT-2025-82", "2027-07-20", "Pfizer", "Rack A-04"),
        ("MED-013", "Lasix", "Furosemide", "Diuretic", "Tablet", "40 mg", 8.40, 130, 20, "LAS-2025-77", "2027-12-01", "Sanofi", "Rack B-06"),
        ("MED-014", "Normal Saline 0.9%", "Sodium Chloride IV", "IV Fluids", "IV Infusion Bottle", "500 ml", 9.00, 180, 40, "NS-2025-901", "2028-09-30", "Baxter", "IV Bay 01"),
        ("MED-015", "Ringer's Lactate", "Compound Sodium Lactate IV", "IV Fluids", "IV Infusion Bottle", "500 ml", 10.50, 150, 30, "RL-2025-402", "2028-08-15", "Baxter", "IV Bay 02"),
        ("MED-016", "Crestor", "Rosuvastatin", "Cardiovascular", "Tablet", "10 mg", 25.00, 110, 20, "CRE-2025-14", "2027-10-05", "AstraZeneca", "Rack B-07"),
        ("MED-017", "Ciprobay", "Ciprofloxacin", "Antibiotics", "Tablet", "500 mg", 16.80, 12, 25, "CIP-2024-02", "2026-10-01", "Bayer", "Rack A-05"), # Low stock item for alert
        ("MED-018", "Duolin Respules", "Levosalbutamol + Ipratropium", "Respiratory", "Inhalation Soln", "2.5 ml", 12.00, 8, 20, "DUO-2024-91", "2026-11-15", "Cipla", "Rack C-03") # Low stock
    ]
    cur.executemany(
        """INSERT INTO medicines (code, brand_name, generic_name, category, form, strength, unit_price, stock_quantity, reorder_level, batch_number, expiry_date, manufacturer, location_rack)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        medicines_data
    )

    print("Seeding Lab Tests Catalog...")
    lab_catalog_data = [
        (
            "LAB-CBC", "Complete Blood Count with Differential (CBC)", "Hematology", 35.00, 4, "Whole Blood (EDTA)",
            json.dumps([
                {"name": "Hemoglobin", "unit": "g/dL", "ref_range": "13.5 - 17.5 (M), 12.0 - 15.5 (F)"},
                {"name": "Total Leukocyte Count (WBC)", "unit": "10^3/uL", "ref_range": "4.5 - 11.0"},
                {"name": "Platelet Count", "unit": "10^3/uL", "ref_range": "150 - 450"},
                {"name": "RBC Count", "unit": "10^6/uL", "ref_range": "4.5 - 5.9"},
                {"name": "Hematocrit (PCV)", "unit": "%", "ref_range": "40 - 52"},
                {"name": "Neutrophils", "unit": "%", "ref_range": "50 - 70"},
                {"name": "Lymphocytes", "unit": "%", "ref_range": "20 - 40"}
            ]),
            "Comprehensive cellular evaluation of blood components."
        ),
        (
            "LAB-LIPID", "Comprehensive Lipid Profile", "Biochemistry", 55.00, 6, "Serum / Plasma (Fasting)",
            json.dumps([
                {"name": "Total Cholesterol", "unit": "mg/dL", "ref_range": "< 200 (Desirable)"},
                {"name": "HDL Cholesterol", "unit": "mg/dL", "ref_range": "> 40 (M), > 50 (F)"},
                {"name": "LDL Cholesterol", "unit": "mg/dL", "ref_range": "< 100 (Optimal)"},
                {"name": "Triglycerides", "unit": "mg/dL", "ref_range": "< 150 (Normal)"},
                {"name": "VLDL", "unit": "mg/dL", "ref_range": "10 - 30"}
            ]),
            "Assesses cardiovascular risk, arterial plaque buildup, and lipid metabolism."
        ),
        (
            "LAB-LFT", "Liver Function Test (LFT)", "Biochemistry", 60.00, 8, "Serum",
            json.dumps([
                {"name": "Total Bilirubin", "unit": "mg/dL", "ref_range": "0.2 - 1.2"},
                {"name": "Direct Bilirubin", "unit": "mg/dL", "ref_range": "0.0 - 0.3"},
                {"name": "SGPT / ALT", "unit": "U/L", "ref_range": "7 - 56"},
                {"name": "SGOT / AST", "unit": "U/L", "ref_range": "10 - 40"},
                {"name": "Alkaline Phosphatase (ALP)", "unit": "U/L", "ref_range": "44 - 147"},
                {"name": "Serum Albumin", "unit": "g/dL", "ref_range": "3.5 - 5.5"},
                {"name": "Total Protein", "unit": "g/dL", "ref_range": "6.0 - 8.3"}
            ]),
            "Evaluates hepatic enzyme levels, synthetic capacity, and biliary clearance."
        ),
        (
            "LAB-KFT", "Renal / Kidney Function Test (KFT / RFT)", "Biochemistry", 50.00, 6, "Serum",
            json.dumps([
                {"name": "Blood Urea Nitrogen (BUN)", "unit": "mg/dL", "ref_range": "7 - 20"},
                {"name": "Serum Creatinine", "unit": "mg/dL", "ref_range": "0.7 - 1.3 (M), 0.6 - 1.1 (F)"},
                {"name": "eGFR (Estimated)", "unit": "mL/min/1.73m2", "ref_range": "> 90"},
                {"name": "Uric Acid", "unit": "mg/dL", "ref_range": "3.5 - 7.2"},
                {"name": "Sodium (Na+)", "unit": "mmol/L", "ref_range": "136 - 145"},
                {"name": "Potassium (K+)", "unit": "mmol/L", "ref_range": "3.5 - 5.1"}
            ]),
            "Assesses renal filtration and electrolyte balance."
        ),
        (
            "LAB-HBA1C", "Glycated Hemoglobin (HbA1c)", "Biochemistry", 40.00, 4, "Whole Blood",
            json.dumps([
                {"name": "HbA1c Concentration", "unit": "%", "ref_range": "< 5.7 (Normal), 5.7-6.4 (Prediabetes), >= 6.5 (Diabetic)"},
                {"name": "Estimated Avg Glucose (eAG)", "unit": "mg/dL", "ref_range": "70 - 126"}
            ]),
            "Monitors average glycemic control over the past 90 days."
        ),
        (
            "LAB-TROP", "Cardiac Troponin I (High Sensitivity)", "Cardiology", 75.00, 2, "Serum / Plasma",
            json.dumps([
                {"name": "hs-Troponin I", "unit": "ng/L", "ref_range": "< 14.0 (Normal), > 34.0 (Acute Myocardial Infarction)"}
            ]),
            "Rapid biomarker for acute coronary syndrome and myocardial necrosis."
        ),
        (
            "LAB-CXR", "Digital Chest X-Ray (PA View)", "Radiology", 65.00, 2, "Radiographic Image",
            json.dumps([
                {"name": "Lung Fields", "unit": "Observation", "ref_range": "Clear, no active infiltrates or consolidation"},
                {"name": "Cardiothoracic Ratio", "unit": "Ratio", "ref_range": "< 0.50 (Normal Heart Size)"},
                {"name": "Costophrenic Angles", "unit": "Observation", "ref_range": "Sharp and clear bilaterally"},
                {"name": "Bony Thorax", "unit": "Observation", "ref_range": "Intact, no fracture seen"}
            ]),
            "Diagnostic radiographic evaluation of chest, pulmonary fields, and cardiac silhouette."
        ),
        (
            "LAB-ECG", "12-Lead Electrocardiogram (ECG / EKG)", "Cardiology", 30.00, 1, "Surface Bio-potential",
            json.dumps([
                {"name": "Rhythm", "unit": "Pattern", "ref_range": "Normal Sinus Rhythm"},
                {"name": "Heart Rate", "unit": "bpm", "ref_range": "60 - 100"},
                {"name": "PR Interval", "unit": "ms", "ref_range": "120 - 200"},
                {"name": "QRS Duration", "unit": "ms", "ref_range": "80 - 120"},
                {"name": "QTc Interval", "unit": "ms", "ref_range": "< 450 (M), < 460 (F)"},
                {"name": "ST Segment", "unit": "Pattern", "ref_range": "Isoelectric, no ST elevation/depression"}
            ]),
            "Diagnostic recording of cardiac electrical conductivity and rhythm."
        ),
        (
            "LAB-URINE", "Urinalysis Routine & Microscopy", "Pathology", 25.00, 3, "Midstream Urine",
            json.dumps([
                {"name": "Color / Appearance", "unit": "Text", "ref_range": "Pale Yellow / Clear"},
                {"name": "Specific Gravity", "unit": "Value", "ref_range": "1.005 - 1.030"},
                {"name": "pH", "unit": "pH", "ref_range": "4.6 - 8.0"},
                {"name": "Protein", "unit": "mg/dL", "ref_range": "Negative / Nil"},
                {"name": "Glucose", "unit": "mg/dL", "ref_range": "Negative / Nil"},
                {"name": "Ketones", "unit": "mg/dL", "ref_range": "Negative"},
                {"name": "Pus Cells (WBC)", "unit": "/HPF", "ref_range": "0 - 4"},
                {"name": "RBCs", "unit": "/HPF", "ref_range": "0 - 2"}
            ]),
            "Routine screening for renal disease, metabolic disorders, and urinary tract infections."
        )
    ]
    cur.executemany(
        """INSERT INTO lab_tests_catalog (code, name, category, cost, turnaround_hours, specimen_type, parameters_json, description)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        lab_catalog_data
    )

    print("Seeding Patients...")
    patients_data = [
        ("PC-2026-0001", user_id_map["patient.john"], "John", "Doe", "1982-05-14", "Male", "O+", "+1-555-0201", "john.doe@email.com", "124 Maple St, Brooklyn, NY", "Jane Doe", "+1-555-0299", "Spouse", "Penicillin", "Hypertension, Hyperlipidemia", "BlueCross BlueShield", "BCBS-8849201", "Inpatient"),
        ("PC-2026-0002", user_id_map["patient.mary"], "Mary", "Smith", "1975-11-28", "Female", "A+", "+1-555-0202", "mary.smith@email.com", "89 Park Ave, Manhattan, NY", "Robert Smith", "+1-555-0298", "Brother", "Sulfa drugs", "Type 2 Diabetes, Mild Asthma", "UnitedHealthcare", "UHC-9928172", "Inpatient"),
        ("PC-2026-0003", None, "Robert", "Johnson", "1960-03-22", "Male", "B+", "+1-555-0203", "r.johnson@example.com", "45 Oak Lane, Queens, NY", "Emily Johnson", "+1-555-0297", "Daughter", "None", "Coronary Artery Disease, Hypertension", "Aetna Health", "AET-7718293", "Inpatient"),
        ("PC-2026-0004", None, "Emily", "Williams", "1994-08-19", "Female", "AB-", "+1-555-0204", "emily.w@example.com", "230 River Rd, Bronx, NY", "Michael Williams", "+1-555-0296", "Father", "Peanuts, Aspirin", "None", "Cigna Global", "CIG-3382910", "Outpatient"),
        ("PC-2026-0005", None, "Michael", "Brown", "1988-02-10", "Male", "O-", "+1-555-0205", "mbrown88@example.com", "55 Elm St, Staten Island, NY", "Sarah Brown", "+1-555-0295", "Wife", "None", "Migraines", "Medicare Advantage", "MED-5548190", "Outpatient"),
        ("PC-2026-0006", None, "Jessica", "Taylor", "2015-09-04", "Female", "A-", "+1-555-0206", "parent.taylor@example.com", "77 Broadway, Manhattan, NY", "David Taylor", "+1-555-0294", "Father", "Amoxicillin", "Allergic Rhinitis", "Kaiser Permanente", "KP-1182736", "Inpatient"),
        ("PC-2026-0007", None, "James", "Wilson", "1954-12-01", "Male", "B-", "+1-555-0207", "jwilson54@example.com", "12 High St, Jersey City, NJ", "Patricia Wilson", "+1-555-0293", "Wife", "Iodine Contrast", "Chronic Kidney Disease Stage 2", "BlueCross BlueShield", "BCBS-4472819", "Outpatient"),
        ("PC-2026-0008", None, "Sophia", "Martinez", "1991-07-16", "Female", "O+", "+1-555-0208", "smartinez@example.com", "304 5th Ave, New York, NY", "Carlos Martinez", "+1-555-0292", "Brother", "Latex", "Hypothyroidism", "Aetna Health", "AET-9938217", "Outpatient"),
        ("PC-2026-0009", None, "Daniel", "Anderson", "1979-04-30", "Male", "A+", "+1-555-0209", "d.anderson@example.com", "620 Central Park West, NY", "Laura Anderson", "+1-555-0291", "Wife", "None", "Gout, Hypertension", "UnitedHealthcare", "UHC-2291038", "Outpatient"),
        ("PC-2026-0010", None, "Olivia", "Thomas", "2000-01-25", "Female", "B+", "+1-555-0210", "olivia.t@example.com", "180 Hudson St, New York, NY", "Grace Thomas", "+1-555-0290", "Mother", "Codeine", "None", "Cigna Global", "CIG-6651829", "Discharged"),
        ("PC-2026-0011", None, "William", "Jackson", "1968-10-12", "Male", "AB+", "+1-555-0211", "wjackson@example.com", "91 Atlantic Ave, Brooklyn, NY", "Susan Jackson", "+1-555-0289", "Spouse", "None", "Osteoarthritis, GERD", "BlueCross BlueShield", "BCBS-5529180", "Outpatient"),
        ("PC-2026-0012", None, "Ava", "White", "1985-06-08", "Female", "O+", "+1-555-0212", "ava.white@example.com", "410 Flatbush Ave, Brooklyn, NY", "Brian White", "+1-555-0288", "Husband", "Shellfish", "Iron Deficiency Anemia", "Aetna Health", "AET-1102938", "Outpatient")
    ]
    cur.executemany(
        """INSERT INTO patients (patient_uid, user_id, first_name, last_name, dob, gender, blood_group, phone, email, address, emergency_contact_name, emergency_contact_phone, emergency_contact_relation, allergies, chronic_conditions, insurance_provider, insurance_policy_number, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        patients_data
    )

    cur.execute("SELECT id, patient_uid, first_name, last_name FROM patients")
    patients_map = {row["patient_uid"]: row["id"] for row in cur.fetchall()}

    print("Seeding Inpatient Admissions & Bed Occupancy...")
    # Beds list
    cur.execute("SELECT id, ward_id, bed_number FROM beds WHERE bed_number IN ('ICU-01', 'GW-M-01', 'PVT-01', 'PED-01')")
    allocated_beds = {row["bed_number"]: row["id"] for row in cur.fetchall()}

    admissions_data = [
        # John Doe in ICU-01
        ("ADM-2026-001", patients_map["PC-2026-0001"], allocated_beds.get("ICU-01", 1), doc_map["dr.sarah"], (datetime.now() - timedelta(days=2, hours=5)).strftime("%Y-%m-%d %H:%M:%S"), None, "Unstable Angina with acute chest discomfort and ST elevation", None, None, "Admitted"),
        # Mary Smith in PVT-01
        ("ADM-2026-002", patients_map["PC-2026-0002"], allocated_beds.get("PVT-01", 15), doc_map["dr.aisha"], (datetime.now() - timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M:%S"), None, "Uncontrolled Hyperglycemia with mild ketoacidosis", None, None, "Admitted"),
        # Robert Johnson in GW-M-01
        ("ADM-2026-003", patients_map["PC-2026-0003"], allocated_beds.get("GW-M-01", 9), doc_map["dr.marcus"], (datetime.now() - timedelta(days=3, hours=12)).strftime("%Y-%m-%d %H:%M:%S"), None, "Transient Ischemic Attack (TIA) evaluation", None, None, "Admitted"),
        # Jessica Taylor in PED-01
        ("ADM-2026-004", patients_map["PC-2026-0006"], allocated_beds.get("PED-01", 25), doc_map["dr.elena"], (datetime.now() - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"), None, "Severe acute viral bronchiolitis with respiratory distress", None, None, "Admitted"),
        # Olivia Thomas - Discharged earlier
        ("ADM-2026-005", patients_map["PC-2026-0010"], allocated_beds.get("PVT-01", 15), doc_map["dr.david"], (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S"), (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), "Post-arthroscopic ACL reconstruction recovery", "Patient mobilized on crutches, surgical wound clean and dry, pain well managed.", "Stable / Ambulatory", "Discharged")
    ]
    adm_map = {}
    for adm in admissions_data:
        cur.execute(
            """INSERT INTO admissions (admission_number, patient_id, bed_id, doctor_id, admitted_at, discharged_at, admission_reason, discharge_summary, discharge_condition, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            adm
        )
        adm_id = cur.lastrowid
        adm_map[adm[0]] = adm_id
        # If admitted, mark bed as Occupied
        if adm[9] == "Admitted":
            cur.execute("UPDATE beds SET status = 'Occupied', current_admission_id = ? WHERE id = ?", (adm_id, adm[2]))

    print("Seeding Vitals...")
    vitals_data = [
        # John Doe (ICU)
        (patients_map["PC-2026-0001"], user_id_map["nurse.clara"], 37.2, 88, 142, 92, 18, 97, 84.5, 178.0, 26.7, 112.0, "Stable on low-flow nasal cannula. Continuous telemetry active.", (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (patients_map["PC-2026-0001"], user_id_map["nurse.clara"], 37.6, 96, 155, 98, 20, 95, 84.5, 178.0, 26.7, 128.0, "Patient reported mild palpitation. Doctor notified.", (datetime.now() - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")),
        (patients_map["PC-2026-0001"], user_id_map["nurse.clara"], 37.8, 102, 160, 100, 22, 94, 84.5, 178.0, 26.7, 140.0, "Admission baseline vitals in emergency bay.", (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        # Mary Smith (Private Ward)
        (patients_map["PC-2026-0002"], user_id_map["nurse.james"], 36.8, 76, 126, 82, 16, 99, 68.0, 162.0, 25.9, 165.0, "Post-prandial blood sugar check. Insulin administered per sliding scale.", (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")),
        (patients_map["PC-2026-0002"], user_id_map["nurse.james"], 37.0, 84, 134, 86, 16, 98, 68.0, 162.0, 25.9, 245.0, "Fasting blood sugar high upon admission.", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
        # Robert Johnson
        (patients_map["PC-2026-0003"], user_id_map["nurse.james"], 36.7, 72, 138, 88, 16, 98, 79.0, 172.0, 26.7, 108.0, "Neurological checks Q4H: Alert, oriented x 3, speech clear.", (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")),
        # Emily Williams (Outpatient)
        (patients_map["PC-2026-0004"], user_id_map["nurse.james"], 36.9, 74, 118, 76, 14, 99, 58.0, 165.0, 21.3, 92.0, "Routine pre-consultation vitals check.", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
        # Michael Brown
        (patients_map["PC-2026-0005"], user_id_map["nurse.james"], 37.1, 80, 124, 80, 16, 98, 82.0, 180.0, 25.3, 98.0, "Pre-consultation vitals.", (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cur.executemany(
        """INSERT INTO vitals (patient_id, recorded_by_id, temperature_c, heart_rate_bpm, blood_pressure_sys, blood_pressure_dia, respiratory_rate, spo2_percent, weight_kg, height_cm, bmi, blood_sugar_mgdl, notes, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        vitals_data
    )

    print("Seeding Appointments...")
    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    appointments_data = [
        # Today's appointments
        ("APT-2026-101", patients_map["PC-2026-0004"], doc_map["dr.sarah"], dept_map["Cardiology"], today_str, "09:30 AM", "Consultation", "In Consultation", 1, "Exertional shortness of breath and chest tightness", "Follow-up echocardiogram review"),
        ("APT-2026-102", patients_map["PC-2026-0005"], doc_map["dr.marcus"], dept_map["Neurology"], today_str, "10:15 AM", "Consultation", "Checked-in", 2, "Recurrent unilateral throbbing headaches with visual aura", "Patient waiting in OPD area"),
        ("APT-2026-103", patients_map["PC-2026-0007"], doc_map["dr.aisha"], dept_map["General Medicine & Diabetology"], today_str, "11:00 AM", "Follow-up", "Booked", 3, "Routine kidney function and blood pressure review", "Awaiting arrival"),
        ("APT-2026-104", patients_map["PC-2026-0008"], doc_map["dr.david"], dept_map["Orthopedics & Joint Surgery"], today_str, "11:45 AM", "Consultation", "Booked", 4, "Right knee joint pain after jogging", "First consultation"),
        ("APT-2026-105", patients_map["PC-2026-0009"], doc_map["dr.aisha"], dept_map["General Medicine & Diabetology"], today_str, "02:00 PM", "Consultation", "Booked", 5, "Acute flare-up of first MTP joint inflammation (Gout)", None),
        ("APT-2026-106", patients_map["PC-2026-0011"], doc_map["dr.david"], dept_map["Orthopedics & Joint Surgery"], today_str, "02:45 PM", "Follow-up", "Booked", 6, "Chronic bilateral knee osteoarthritis review", None),
        ("APT-2026-107", patients_map["PC-2026-0012"], doc_map["dr.aisha"], dept_map["General Medicine & Diabetology"], today_str, "03:30 PM", "Consultation", "Booked", 7, "General fatigue, dizziness, and pale conjunctiva", None),
        # Tomorrow's appointments
        ("APT-2026-108", patients_map["PC-2026-0001"], doc_map["dr.sarah"], dept_map["Cardiology"], tomorrow_str, "10:00 AM", "Follow-up", "Booked", 1, "Post-discharge cardiac rehab plan", None),
        ("APT-2026-109", patients_map["PC-2026-0002"], doc_map["dr.aisha"], dept_map["General Medicine & Diabetology"], tomorrow_str, "10:45 AM", "Follow-up", "Booked", 2, "HbA1c titration check", None),
        # Yesterday's completed appointments
        ("APT-2026-090", patients_map["PC-2026-0004"], doc_map["dr.sarah"], dept_map["Cardiology"], yesterday_str, "09:00 AM", "Consultation", "Completed", 1, "Initial assessment for atypical chest discomfort", "ECG and Lipid panel ordered")
    ]
    cur.executemany(
        """INSERT INTO appointments (appointment_number, patient_id, doctor_id, department_id, appointment_date, appointment_time, type, status, token_number, reason, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        appointments_data
    )

    cur.execute("SELECT id, appointment_number FROM appointments")
    apt_map = {row["appointment_number"]: row["id"] for row in cur.fetchall()}

    print("Seeding Consultations & SOAP Clinical Notes...")
    consultations_data = [
        (
            apt_map["APT-2026-090"],
            patients_map["PC-2026-0004"],
            doc_map["dr.sarah"],
            "Patient reports intermittent sharp chest discomfort on strenuous exertion, no radiation to arm, no diaphoresis.",
            "Atypical Chest Pain - Non-ischemic suspected",
            "R07.89",
            "Heart sounds S1/S2 present, no murmurs. Lungs clear to auscultation bilaterally. No peripheral edema.",
            "1. Order 12-Lead ECG and Comprehensive Lipid Profile\n2. Prescribe lifestyle changes and low-dose statin\n3. Follow up in 1 week.",
            (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            yesterday_str + " 09:45:00"
        ),
        (
            None, # Direct Inpatient consultation
            patients_map["PC-2026-0001"],
            doc_map["dr.sarah"],
            "Patient presented with crushing retrosternal chest pain radiating to left jaw, accompanied by diaphoresis and shortness of breath.",
            "Acute Coronary Syndrome (Non-STEMI) / Unstable Angina",
            "I20.0",
            "Blood pressure 142/92, HR 88 bpm. Elevated Troponin I (48 ng/L). ECG reveals transient ST depression in V4-V6.",
            "1. Immediate dual antiplatelet therapy (Aspirin + Clopidogrel)\n2. Atorvastatin 40mg nocte\n3. Sublingual nitroglycerin PRN\n4. Continuous telemetry in ICU\n5. Coronary angiogram scheduled for tomorrow.",
            (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            None,
            patients_map["PC-2026-0002"],
            doc_map["dr.aisha"],
            "Patient presented with polyuria, polydipsia, fatigue, and blurred vision over past 2 weeks.",
            "Type 2 Diabetes Mellitus with Hyperglycemia (Uncontrolled)",
            "E11.65",
            "BMI 25.9, dehydration signs present. Fasting Blood Glucose 245 mg/dL, HbA1c 9.4%. No diabetic ketoacidosis.",
            "1. Initiate basal insulin (Lantus 10 units at bedtime)\n2. Metformin XR 1000mg with dinner\n3. Strict diabetic diet consultation & BG logging QID.",
            (date.today() + timedelta(days=14)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]
    cur.executemany(
        """INSERT INTO consultations (appointment_id, patient_id, doctor_id, symptoms, diagnosis, icd_code, examination_notes, treatment_plan, follow_up_date, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        consultations_data
    )

    cur.execute("SELECT id, patient_id, diagnosis FROM consultations")
    consults = cur.fetchall()

    print("Seeding Prescriptions & Line Items...")
    # Medicine map
    cur.execute("SELECT id, code, brand_name, unit_price FROM medicines")
    med_map = {row["code"]: row["id"] for row in cur.fetchall()}

    prescriptions_data = [
        ("RX-2026-001", consults[0]["id"], patients_map["PC-2026-0004"], doc_map["dr.sarah"], "Dispensed", "Take medication after food. Avoid heavy greasy meals."),
        ("RX-2026-002", consults[1]["id"], patients_map["PC-2026-0001"], doc_map["dr.sarah"], "Dispensed", "Strict adherence. Report any chest tightness immediately."),
        ("RX-2026-003", consults[2]["id"], patients_map["PC-2026-0002"], doc_map["dr.aisha"], "Pending", "Monitor fasting and post-prandial blood glucose daily.")
    ]
    for rx in prescriptions_data:
        cur.execute(
            """INSERT INTO prescriptions (prescription_number, consultation_id, patient_id, doctor_id, status, special_instructions)
               VALUES (?, ?, ?, ?, ?, ?)""",
            rx
        )
        rx_id = cur.lastrowid
        
        # Prescription items
        if rx[0] == "RX-2026-001":
            items = [
                (rx_id, med_map["MED-003"], "20 mg", "0-0-1 (Night)", 30, "Take after dinner", 30, 30, 1),
                (rx_id, med_map["MED-002"], "500 mg", "1-0-1 (As needed)", 5, "Take for pain/headache", 10, 10, 1)
            ]
        elif rx[0] == "RX-2026-002":
            items = [
                (rx_id, med_map["MED-003"], "40 mg", "0-0-1 (Night)", 30, "Statin therapy", 30, 30, 1),
                (rx_id, med_map["MED-007"], "5 mg", "1-0-0 (Morning)", 30, "Blood pressure control", 30, 30, 1),
                (rx_id, med_map["MED-006"], "40 mg", "1-0-0 (Before Breakfast)", 30, "Gastric protection", 30, 30, 1)
            ]
        else: # RX-2026-003
            items = [
                (rx_id, med_map["MED-004"], "1000 mg", "0-0-1 (With Dinner)", 30, "Take with food", 30, 0, 0),
                (rx_id, med_map["MED-009"], "10 Units", "0-0-1 (At Bedtime)", 30, "Subcutaneous injection pen", 1, 0, 0)
            ]
        
        cur.executemany(
            """INSERT INTO prescription_items (prescription_id, medicine_id, dosage, frequency, duration_days, instructions, quantity_prescribed, quantity_dispensed, is_dispensed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            items
        )

    print("Seeding Lab Orders & Diagnostic Reports...")
    cur.execute("SELECT id, code, cost FROM lab_tests_catalog")
    test_map = {row["code"]: row["id"] for row in cur.fetchall()}

    # Lab Order 1: John Doe (Completed)
    cur.execute(
        """INSERT INTO lab_orders (order_number, patient_id, doctor_id, consultation_id, status, clinical_notes, ordered_at, sample_collected_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "LAB-ORD-2026-001",
            patients_map["PC-2026-0001"],
            doc_map["dr.sarah"],
            consults[1]["id"],
            "Completed",
            "Rule out acute MI and dyslipidemia",
            (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=2, hours=-1)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=2, hours=-3)).strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    order1_id = cur.lastrowid
    
    order1_items = [
        (
            order1_id, test_map["LAB-TROP"], "Completed",
            json.dumps([{"name": "hs-Troponin I", "value": "48.2", "unit": "ng/L", "ref_range": "< 14.0 (Normal), > 34.0 (Acute MI)", "is_abnormal": True}]),
            "Markedly elevated cardiac troponin I consistent with acute myocardial injury/NSTEMI.",
            user_id_map["lab.lisa"], doc_map["dr.sarah"], (datetime.now() - timedelta(days=2, hours=-3)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            order1_id, test_map["LAB-ECG"], "Completed",
            json.dumps([
                {"name": "Rhythm", "value": "Sinus Rhythm with ST depression in V4-V6", "unit": "Pattern", "ref_range": "Normal Sinus Rhythm", "is_abnormal": True},
                {"name": "Heart Rate", "value": "88", "unit": "bpm", "ref_range": "60 - 100", "is_abnormal": False},
                {"name": "PR Interval", "value": "160", "unit": "ms", "ref_range": "120 - 200", "is_abnormal": False},
                {"name": "QRS Duration", "value": "95", "unit": "ms", "ref_range": "80 - 120", "is_abnormal": False},
                {"name": "QTc Interval", "value": "430", "unit": "ms", "ref_range": "< 450 (M)", "is_abnormal": False}
            ]),
            "Subendocardial ischemia in anterolateral leads. Correlates with clinical presentation.",
            user_id_map["lab.lisa"], doc_map["dr.sarah"], (datetime.now() - timedelta(days=2, hours=-3)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            order1_id, test_map["LAB-LIPID"], "Completed",
            json.dumps([
                {"name": "Total Cholesterol", "value": "238", "unit": "mg/dL", "ref_range": "< 200", "is_abnormal": True},
                {"name": "HDL Cholesterol", "value": "34", "unit": "mg/dL", "ref_range": "> 40", "is_abnormal": True},
                {"name": "LDL Cholesterol", "value": "162", "unit": "mg/dL", "ref_range": "< 100", "is_abnormal": True},
                {"name": "Triglycerides", "value": "210", "unit": "mg/dL", "ref_range": "< 150", "is_abnormal": True},
                {"name": "VLDL", "value": "42", "unit": "mg/dL", "ref_range": "10 - 30", "is_abnormal": True}
            ]),
            "Mixed dyslipidemia with elevated atherogenic LDL and low protective HDL.",
            user_id_map["lab.lisa"], doc_map["dr.sarah"], (datetime.now() - timedelta(days=2, hours=-2)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]
    cur.executemany(
        """INSERT INTO lab_order_items (lab_order_id, test_id, status, results_json, interpretation, technician_id, verified_by_id, performed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        order1_items
    )

    # Lab Order 2: Mary Smith (Completed HbA1c, KFT)
    cur.execute(
        """INSERT INTO lab_orders (order_number, patient_id, doctor_id, consultation_id, status, clinical_notes, ordered_at, sample_collected_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "LAB-ORD-2026-002",
            patients_map["PC-2026-0002"],
            doc_map["dr.aisha"],
            consults[2]["id"],
            "Completed",
            "Diabetic monitoring and renal baseline",
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=1, hours=-1)).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.now() - timedelta(days=1, hours=-4)).strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    order2_id = cur.lastrowid
    order2_items = [
        (
            order2_id, test_map["LAB-HBA1C"], "Completed",
            json.dumps([
                {"name": "HbA1c Concentration", "value": "9.4", "unit": "%", "ref_range": "< 5.7 (Normal), >= 6.5 (Diabetic)", "is_abnormal": True},
                {"name": "Estimated Avg Glucose (eAG)", "value": "223", "unit": "mg/dL", "ref_range": "70 - 126", "is_abnormal": True}
            ]),
            "Uncontrolled glycemia requiring immediate medical and insulin adjustment.",
            user_id_map["lab.lisa"], doc_map["dr.aisha"], (datetime.now() - timedelta(days=1, hours=-4)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            order2_id, test_map["LAB-KFT"], "Completed",
            json.dumps([
                {"name": "Blood Urea Nitrogen (BUN)", "value": "18", "unit": "mg/dL", "ref_range": "7 - 20", "is_abnormal": False},
                {"name": "Serum Creatinine", "value": "0.9", "unit": "mg/dL", "ref_range": "0.6 - 1.1", "is_abnormal": False},
                {"name": "eGFR (Estimated)", "value": "94", "unit": "mL/min/1.73m2", "ref_range": "> 90", "is_abnormal": False},
                {"name": "Uric Acid", "value": "4.8", "unit": "mg/dL", "ref_range": "3.5 - 7.2", "is_abnormal": False},
                {"name": "Sodium (Na+)", "value": "139", "unit": "mmol/L", "ref_range": "136 - 145", "is_abnormal": False},
                {"name": "Potassium (K+)", "value": "4.2", "unit": "mmol/L", "ref_range": "3.5 - 5.1", "is_abnormal": False}
            ]),
            "Renal function within normal physiological limits.",
            user_id_map["lab.lisa"], doc_map["dr.aisha"], (datetime.now() - timedelta(days=1, hours=-4)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]
    cur.executemany(
        """INSERT INTO lab_order_items (lab_order_id, test_id, status, results_json, interpretation, technician_id, verified_by_id, performed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        order2_items
    )

    # Lab Order 3: Emily Williams (Ordered today, pending testing)
    cur.execute(
        """INSERT INTO lab_orders (order_number, patient_id, doctor_id, consultation_id, status, clinical_notes, ordered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "LAB-ORD-2026-003",
            patients_map["PC-2026-0004"],
            doc_map["dr.sarah"],
            consults[0]["id"],
            "Sample Collected",
            "Routine cardiovascular risk screening",
            today_str + " 09:30:00"
        )
    )
    order3_id = cur.lastrowid
    cur.execute(
        """INSERT INTO lab_order_items (lab_order_id, test_id, status)
           VALUES (?, ?, 'In Progress')""",
        (order3_id, test_map["LAB-CBC"])
    )

    print("Seeding Invoices & Payments...")
    invoices_data = [
        # John Doe - Inpatient Active Bill
        (
            "INV-2026-0001", patients_map["PC-2026-0001"], adm_map["ADM-2026-001"], None, 1345.00, 5.0, 67.25, 50.00, 1362.25, 1000.00,
            "Partially Paid", "Insurance", (date.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), "Emergency admission initial deposit paid via BlueCross Pre-authorization."
        ),
        # Mary Smith - Inpatient Bill
        (
            "INV-2026-0002", patients_map["PC-2026-0002"], adm_map["ADM-2026-002"], None, 680.00, 5.0, 34.00, 0.00, 714.00, 714.00,
            "Paid", "Credit Card", today_str,
            today_str + " 11:30:00", "Private Deluxe ward admission advance full settlement."
        ),
        # Emily Williams - Outpatient Consultation & Lab Bill
        (
            "INV-2026-0003", patients_map["PC-2026-0004"], None, apt_map["APT-2026-090"], 215.00, 5.0, 10.75, 0.00, 225.75, 225.75,
            "Paid", "UPI / QR", yesterday_str,
            yesterday_str + " 10:15:00", "OPD Consultation fee + CBC Lab investigation fee."
        ),
        # Olivia Thomas - Post discharge cleared bill
        (
            "INV-2026-0004", patients_map["PC-2026-0010"], adm_map["ADM-2026-005"], None, 1850.00, 5.0, 92.50, 100.00, 1842.50, 1842.50,
            "Paid", "Insurance", (date.today() - timedelta(days=2)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), "ACL Knee Surgery post-op room and surgical discharge summary cleared."
        )
    ]
    for inv in invoices_data:
        cur.execute(
            """INSERT INTO invoices (invoice_number, patient_id, admission_id, appointment_id, subtotal, tax_percent, tax_amount, discount_amount, total_amount, amount_paid, status, payment_method, due_date, paid_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            inv
        )
        inv_id = cur.lastrowid
        
        # Add Invoice Line items
        if inv[0] == "INV-2026-0001": # John Doe
            items = [
                (inv_id, "Bed / Ward", "ICU Bed Charges (2 Days @ $450/day)", None, 2, 450.0, 900.0),
                (inv_id, "Consultation", "Critical Care Specialist Consultation - Dr. Sarah Jenkins", None, 1, 180.0, 180.0),
                (inv_id, "Lab Test", "Cardiac hs-Troponin I & 12-Lead ECG", None, 1, 105.0, 105.0),
                (inv_id, "Lab Test", "Comprehensive Lipid Profile", None, 1, 55.0, 55.0),
                (inv_id, "Pharmacy", "Atorvastatin, Amlodipine, Esomeprazole, IV Saline", None, 1, 105.0, 105.0)
            ]
        elif inv[0] == "INV-2026-0002": # Mary Smith
            items = [
                (inv_id, "Bed / Ward", "Private Deluxe Suite (1 Day)", None, 1, 320.0, 320.0),
                (inv_id, "Consultation", "Consultant Diabetologist - Dr. Aisha Patel", None, 1, 120.0, 120.0),
                (inv_id, "Lab Test", "Glycated Hemoglobin (HbA1c) & Renal Function Test", None, 1, 90.0, 90.0),
                (inv_id, "Pharmacy", "Lantus Insulin Solostar & Metformin XR", None, 1, 150.0, 150.0)
            ]
        elif inv[0] == "INV-2026-0003": # Emily Williams
            items = [
                (inv_id, "Consultation", "Cardiology OPD Consultation - Dr. Sarah Jenkins", None, 1, 180.0, 180.0),
                (inv_id, "Lab Test", "Complete Blood Count (CBC)", None, 1, 35.0, 35.0)
            ]
        else: # Olivia Thomas
            items = [
                (inv_id, "Bed / Ward", "Private Deluxe Room (4 Days @ $320/day)", None, 4, 320.0, 1280.0),
                (inv_id, "Consultation", "Orthopedic Surgeon Visit - Dr. David Chen", None, 2, 175.0, 350.0),
                (inv_id, "Pharmacy", "Analgesics, Antibiotics & Wound Dressing Packs", None, 1, 220.0, 220.0)
            ]
            
        cur.executemany(
            """INSERT INTO invoice_items (invoice_id, item_type, description, reference_id, quantity, unit_price, total_price)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            items
        )

    print("Seeding Audit Logs...")
    logs = [
        (user_id_map["admin"], "System Initialization", "System", "PulseCare HMS database initialized with schema v2.0", "127.0.0.1", (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_id_map["reception.emma"], "Patient Registered", "Patients", "Registered new patient PC-2026-0001 (John Doe)", "192.168.1.10", (datetime.now() - timedelta(days=2, hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_id_map["nurse.clara"], "Bed Allocated", "Wards", "Allocated Bed ICU-01 to Admission ADM-2026-001 (John Doe)", "192.168.1.15", (datetime.now() - timedelta(days=2, hours=5)).strftime("%Y-%m-%d %H:%M:%S")),
        (doc_map["dr.sarah"], "Consultation Saved", "Consultations", "Recorded clinical SOAP note for patient John Doe", "192.168.1.20", (datetime.now() - timedelta(days=2, hours=4)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_id_map["lab.lisa"], "Lab Results Verified", "Laboratory", "Verified Troponin I and Lipid panel for order LAB-ORD-2026-001", "192.168.1.30", (datetime.now() - timedelta(days=2, hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_id_map["pharm.robert"], "Prescription Dispensed", "Pharmacy", "Dispensed RX-2026-002 to patient John Doe", "192.168.1.40", (datetime.now() - timedelta(days=2, hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        (user_id_map["reception.emma"], "Invoice Generated", "Billing", "Created invoice INV-2026-0001 for John Doe (Total: $1,362.25)", "192.168.1.10", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cur.executemany(
        """INSERT INTO audit_logs (user_id, action, module, details, ip_address, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        logs
    )

    conn.commit()
    conn.close()
    print("Database successfully initialized and seeded with rich medical dataset!")

if __name__ == "__main__":
    seed_database()
