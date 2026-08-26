-- PulseCare Tiered Public Health & Rural Telemedicine Network Database Schema
PRAGMA foreign_keys = ON;

-- 1. Hospital & Public Health System Settings
CREATE TABLE IF NOT EXISTS hospital_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 2. Health Facilities (Tiered Public Health Hierarchy)
CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    facility_code TEXT NOT NULL UNIQUE,
    tier_type TEXT NOT NULL CHECK(tier_type IN ('Sub-Centre', 'PHC', 'CHC', 'District Hospital')),
    district TEXT NOT NULL,
    block_taluk TEXT,
    pincode TEXT,
    contact_phone TEXT,
    emergency_helpline TEXT,
    teleconsult_enabled INTEGER DEFAULT 1,
    ambulance_available INTEGER DEFAULT 0,
    total_beds INTEGER DEFAULT 0,
    equipment_summary TEXT, -- e.g. "ECG, Point-of-Care Blood Analyzer, Pulse Oximeter, Fetal Doppler"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    head_doctor_name TEXT,
    color TEXT DEFAULT '#0d6efd',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Users & Staff (Specialists, Medical Officers, ASHA/CHO Frontline Health Workers, Nurses, Pharmacists)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'nurse', 'receptionist', 'pharmacist', 'lab_tech', 'patient', 'asha_cho', 'medical_officer')),
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    specialization TEXT,
    qualification TEXT,
    license_number TEXT,
    consultation_fee REAL DEFAULT 0.0,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Patients (With ABHA National Health ID & Rural Demographics)
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_uid TEXT NOT NULL UNIQUE,
    abha_id TEXT UNIQUE, -- 14-digit Ayushman Bharat Health Account ID (e.g. 91-4820-9182-3841)
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob DATE NOT NULL,
    gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
    blood_group TEXT,
    phone TEXT NOT NULL,
    email TEXT,
    village TEXT,
    panchayat TEXT,
    address TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relation TEXT,
    allergies TEXT,
    chronic_conditions TEXT,
    socioeconomic_category TEXT DEFAULT 'BPL' CHECK(socioeconomic_category IN ('BPL', 'APL', 'PM-JAY Scheme', 'Antyodaya', 'General')),
    insurance_provider TEXT,
    insurance_policy_number TEXT,
    is_high_risk INTEGER DEFAULT 0,
    high_risk_category TEXT, -- 'Maternal HRP', 'Child Health', 'NCD', 'Infectious'
    assigned_asha_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'Outpatient' CHECK(status IN ('Outpatient', 'Inpatient', 'Discharged', 'Critical', 'Under Teleconsultation', 'Referred')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Patient Vitals
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recorded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    temperature_c REAL,
    heart_rate_bpm INTEGER,
    blood_pressure_sys INTEGER,
    blood_pressure_dia INTEGER,
    respiratory_rate INTEGER,
    spo2_percent INTEGER,
    weight_kg REAL,
    height_cm REAL,
    bmi REAL,
    blood_sugar_mgdl REAL,
    hemoglobin_gdl REAL,
    fetal_heart_rate INTEGER, -- For pregnant mothers
    triage_color TEXT DEFAULT 'Green' CHECK(triage_color IN ('Red', 'Yellow', 'Green')),
    notes TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. Assisted Teleconsultations (Connecting Frontline ASHA/CHO/PHC to District Specialist)
CREATE TABLE IF NOT EXISTS teleconsultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    initiator_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- ASHA / CHO / Medical Officer
    specialist_id INTEGER REFERENCES users(id) ON DELETE SET NULL, -- District Hospital Specialist
    from_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    target_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    triage_level TEXT DEFAULT 'Routine' CHECK(triage_level IN ('Emergency', 'High-Risk', 'Routine')),
    chief_complaint TEXT NOT NULL,
    clinical_findings TEXT,
    specialist_advice TEXT,
    status TEXT DEFAULT 'Requested' CHECK(status IN ('Requested', 'In-Call', 'Completed', 'Escalated', 'Cancelled')),
    vitals_snapshot_json TEXT,
    prescription_id INTEGER,
    scheduled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME
);

-- 8. Inter-Facility Closed-Loop Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referral_uid TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    from_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    to_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    referring_doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiving_specialist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    specialty_needed TEXT NOT NULL,
    reason TEXT NOT NULL,
    provisional_diagnosis TEXT,
    triage_priority TEXT DEFAULT 'Urgent - Yellow' CHECK(triage_priority IN ('Emergency - Red', 'Urgent - Yellow', 'Routine - Green')),
    transport_mode TEXT DEFAULT '108 Ambulance' CHECK(transport_mode IN ('108 Ambulance', 'Government Health Transport', 'Self / Private Vehicle', 'Public Transit')),
    status TEXT DEFAULT 'Initiated' CHECK(status IN ('Initiated', 'Accepted', 'In-Transit', 'Attended', 'Counter-Referred', 'Cancelled')),
    initiated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    attended_at DATETIME,
    counter_referral_notes TEXT, -- Instructions sent back to rural ASHA/PHC for home follow-up
    assigned_followup_asha_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- 9. High-Risk Patient Surveillance Registry
CREATE TABLE IF NOT EXISTS high_risk_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK(category IN ('Maternal High-Risk (HRP)', 'Child Malnutrition & Immunization', 'Chronic NCD (Diabetes/HTN/COPD)', 'Tuberculosis / Infectious')),
    risk_factors TEXT NOT NULL, -- e.g. "Severe Anemia (Hb < 7.0), Gestational HTN (BP 160/100)"
    severity_score INTEGER DEFAULT 1 CHECK(severity_score BETWEEN 1 AND 5), -- 5 = Critical
    assigned_worker_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    last_assessment_date DATE,
    next_followup_date DATE NOT NULL,
    status TEXT DEFAULT 'Active Surveillance' CHECK(status IN ('Active Surveillance', 'Controlled', 'Critical Escalation', 'Resolved')),
    clinical_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    appointment_date DATE NOT NULL,
    appointment_time TEXT NOT NULL,
    type TEXT DEFAULT 'Consultation' CHECK(type IN ('Consultation', 'Follow-up', 'Emergency', 'Teleconsultation', 'Routine Checkup')),
    status TEXT DEFAULT 'Booked' CHECK(status IN ('Booked', 'Checked-in', 'In Consultation', 'Completed', 'Cancelled', 'No-Show')),
    token_number INTEGER,
    reason TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 11. Consultations
CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER UNIQUE REFERENCES appointments(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    symptoms TEXT,
    diagnosis TEXT NOT NULL,
    icd_code TEXT,
    examination_notes TEXT,
    treatment_plan TEXT,
    follow_up_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 12. Central Medicines Catalog
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    brand_name TEXT NOT NULL,
    generic_name TEXT NOT NULL,
    category TEXT NOT NULL,
    form TEXT NOT NULL,
    strength TEXT,
    unit_price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 20,
    batch_number TEXT,
    expiry_date DATE,
    manufacturer TEXT,
    location_rack TEXT,
    is_essential_life_saving INTEGER DEFAULT 0, -- Anti-snake venom, Oxytocin, Insulin, etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 13. Cross-Facility Medicine Inventory Grid
CREATE TABLE IF NOT EXISTS facility_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER DEFAULT 15,
    last_restocked DATE,
    UNIQUE(facility_id, medicine_id)
);

-- 14. Prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_number TEXT NOT NULL UNIQUE,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Partially Dispensed', 'Dispensed', 'Cancelled')),
    special_instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 15. Prescription Items
CREATE TABLE IF NOT EXISTS prescription_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE RESTRICT,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    instructions TEXT,
    quantity_prescribed INTEGER NOT NULL,
    quantity_dispensed INTEGER DEFAULT 0,
    is_dispensed INTEGER DEFAULT 0
);

-- 16. Pharmacy Dispenses
CREATE TABLE IF NOT EXISTS pharmacy_dispenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER REFERENCES prescriptions(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    pharmacist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    total_amount REAL NOT NULL DEFAULT 0.0,
    notes TEXT,
    dispensed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 17. Wards & Beds
CREATE TABLE IF NOT EXISTS wards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('ICU', 'Emergency', 'General Ward', 'Private Deluxe', 'Semi-Private', 'Pediatric', 'Maternity', 'Surgical Ward')),
    floor TEXT NOT NULL,
    total_beds INTEGER NOT NULL,
    daily_rate REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS beds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
    bed_number TEXT NOT NULL,
    status TEXT DEFAULT 'Available' CHECK(status IN ('Available', 'Occupied', 'Maintenance', 'Reserved')),
    current_admission_id INTEGER,
    UNIQUE(ward_id, bed_number)
);

-- 18. Admissions (IPD)
CREATE TABLE IF NOT EXISTS admissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    bed_id INTEGER NOT NULL REFERENCES beds(id) ON DELETE RESTRICT,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discharged_at DATETIME,
    admission_reason TEXT NOT NULL,
    discharge_summary TEXT,
    discharge_condition TEXT,
    status TEXT DEFAULT 'Admitted' CHECK(status IN ('Admitted', 'Discharged', 'Transferred'))
);

-- 19. Lab Tests Catalog & Cross-Facility Diagnostic Availability
CREATE TABLE IF NOT EXISTS lab_tests_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Hematology', 'Biochemistry', 'Pathology', 'Radiology', 'Microbiology', 'Serology', 'Cardiology')),
    cost REAL NOT NULL,
    turnaround_hours INTEGER DEFAULT 24,
    specimen_type TEXT,
    parameters_json TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS facility_diagnostics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES lab_tests_catalog(id) ON DELETE CASCADE,
    is_operational INTEGER DEFAULT 1,
    equipment_status TEXT DEFAULT 'Working' CHECK(equipment_status IN ('Working', 'Calibrating', 'Under Maintenance', 'Reagent Out of Stock')),
    average_wait_hours REAL DEFAULT 2.0,
    UNIQUE(facility_id, test_id)
);

-- 20. Lab Orders & Items
CREATE TABLE IF NOT EXISTS lab_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'Ordered' CHECK(status IN ('Ordered', 'Sample Collected', 'In Testing', 'Completed', 'Cancelled')),
    clinical_notes TEXT,
    ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sample_collected_at DATETIME,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS lab_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_order_id INTEGER NOT NULL REFERENCES lab_orders(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES lab_tests_catalog(id) ON DELETE RESTRICT,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    results_json TEXT,
    interpretation TEXT,
    technician_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    performed_at DATETIME
);

-- 21. Invoices & Billing (Supports Free Public Health / PM-JAY Schemes)
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    admission_id INTEGER REFERENCES admissions(id) ON DELETE SET NULL,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    subtotal REAL NOT NULL DEFAULT 0.0,
    tax_percent REAL DEFAULT 0.0,
    tax_amount REAL DEFAULT 0.0,
    discount_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    amount_paid REAL DEFAULT 0.0,
    status TEXT DEFAULT 'Paid' CHECK(status IN ('Unpaid', 'Partially Paid', 'Paid', 'Cancelled', 'Govt Subsidized (100%)')),
    payment_method TEXT CHECK(payment_method IN ('Cash', 'Credit Card', 'Debit Card', 'UPI / QR', 'Insurance', 'PM-JAY Scheme (Cashless)', 'Free Public Service')),
    due_date DATE,
    paid_at DATETIME,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK(item_type IN ('Consultation', 'Lab Test', 'Pharmacy', 'Bed / Ward', 'Nursing Care', 'Teleconsultation', 'Procedure', 'Miscellaneous')),
    description TEXT NOT NULL,
    reference_id INTEGER,
    quantity REAL NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    total_price REAL NOT NULL DEFAULT 0.0
);

-- 22. Audit Trail
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    module TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_patients_uid ON patients(patient_uid);
CREATE INDEX IF NOT EXISTS idx_patients_abha ON patients(abha_id);
CREATE INDEX IF NOT EXISTS idx_patients_high_risk ON patients(is_high_risk);
CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status);
CREATE INDEX IF NOT EXISTS idx_teleconsult_status ON teleconsultations(status);
CREATE INDEX IF NOT EXISTS idx_highrisk_next ON high_risk_registry(next_followup_date);
CREATE INDEX IF NOT EXISTS idx_facility_inventory ON facility_inventory(facility_id, medicine_id);
CREATE INDEX IF NOT EXISTS idx_facility_diagnostics ON facility_diagnostics(facility_id, test_id);
