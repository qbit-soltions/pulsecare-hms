-- =============================================================================
-- PulseCare Public Health & Rural Telemedicine Network
-- Supabase PostgreSQL Schema & Baseline Seed Data
-- Compatible with Supabase Postgres (Version 15 / 16)
-- =============================================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Hospital & Public Health System Settings
CREATE TABLE IF NOT EXISTS hospital_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
);

-- 2. Health Facilities (Tiered Public Health Hierarchy)
CREATE TABLE IF NOT EXISTS facilities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    facility_code VARCHAR(50) NOT NULL UNIQUE,
    tier_type VARCHAR(50) NOT NULL CHECK(tier_type IN ('Sub-Centre', 'PHC', 'CHC', 'District Hospital')),
    district VARCHAR(100) NOT NULL,
    block_taluk VARCHAR(100),
    pincode VARCHAR(20),
    contact_phone VARCHAR(50),
    emergency_helpline VARCHAR(50),
    teleconsult_enabled INTEGER DEFAULT 1,
    ambulance_available INTEGER DEFAULT 0,
    total_beds INTEGER DEFAULT 0,
    equipment_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Departments
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    head_doctor_name VARCHAR(150),
    color VARCHAR(20) DEFAULT '#0d6efd',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Users & Staff
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(50),
    role VARCHAR(50) NOT NULL CHECK(role IN ('admin', 'doctor', 'nurse', 'receptionist', 'pharmacist', 'lab_tech', 'patient', 'asha_cho', 'medical_officer')),
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    specialization VARCHAR(150),
    qualification VARCHAR(150),
    license_number VARCHAR(100),
    consultation_fee NUMERIC(10, 2) DEFAULT 0.0,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Patients (With ABHA National Health ID & Rural Demographics)
CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    patient_uid VARCHAR(50) NOT NULL UNIQUE,
    abha_id VARCHAR(50) UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(20) CHECK(gender IN ('Male', 'Female', 'Other')),
    blood_group VARCHAR(10),
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(150),
    village VARCHAR(100),
    panchayat VARCHAR(100),
    address TEXT,
    emergency_contact_name VARCHAR(150),
    emergency_contact_phone VARCHAR(50),
    emergency_contact_relation VARCHAR(50),
    allergies TEXT,
    chronic_conditions TEXT,
    socioeconomic_category VARCHAR(50) DEFAULT 'BPL' CHECK(socioeconomic_category IN ('BPL', 'APL', 'PM-JAY Scheme', 'Antyodaya', 'General')),
    insurance_provider VARCHAR(150),
    insurance_policy_number VARCHAR(100),
    is_high_risk INTEGER DEFAULT 0,
    high_risk_category VARCHAR(100),
    assigned_asha_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'Outpatient' CHECK(status IN ('Outpatient', 'Inpatient', 'Discharged', 'Critical', 'Under Teleconsultation', 'Referred')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Patient Vitals
CREATE TABLE IF NOT EXISTS vitals (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recorded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    temperature_c NUMERIC(5, 2),
    heart_rate_bpm INTEGER,
    blood_pressure_sys INTEGER,
    blood_pressure_dia INTEGER,
    respiratory_rate INTEGER,
    spo2_percent INTEGER,
    weight_kg NUMERIC(6, 2),
    height_cm NUMERIC(6, 2),
    bmi NUMERIC(5, 2),
    blood_sugar_mgdl NUMERIC(6, 2),
    hemoglobin_gdl NUMERIC(5, 2),
    fetal_heart_rate INTEGER,
    triage_color VARCHAR(20) DEFAULT 'Green' CHECK(triage_color IN ('Red', 'Yellow', 'Green')),
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Assisted Teleconsultations
CREATE TABLE IF NOT EXISTS teleconsultations (
    id SERIAL PRIMARY KEY,
    session_uid VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    initiator_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    specialist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    from_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    target_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    triage_level VARCHAR(30) DEFAULT 'Routine' CHECK(triage_level IN ('Emergency', 'High-Risk', 'Routine')),
    chief_complaint TEXT NOT NULL,
    clinical_findings TEXT,
    specialist_advice TEXT,
    status VARCHAR(30) DEFAULT 'Requested' CHECK(status IN ('Requested', 'In-Call', 'Completed', 'Escalated', 'Cancelled')),
    vitals_snapshot_json TEXT,
    prescription_id INTEGER,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 8. Inter-Facility Closed-Loop Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referral_uid VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    from_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    to_facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    referring_doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiving_specialist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    specialty_needed VARCHAR(100) NOT NULL,
    reason TEXT NOT NULL,
    provisional_diagnosis TEXT,
    triage_priority VARCHAR(30) DEFAULT 'Urgent - Yellow' CHECK(triage_priority IN ('Emergency - Red', 'Urgent - Yellow', 'Routine - Green')),
    transport_mode VARCHAR(50) DEFAULT '108 Ambulance' CHECK(transport_mode IN ('108 Ambulance', 'Government Health Transport', 'Self / Private Vehicle', 'Public Transit')),
    status VARCHAR(30) DEFAULT 'Initiated' CHECK(status IN ('Initiated', 'Accepted', 'In-Transit', 'Attended', 'Counter-Referred', 'Cancelled')),
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP,
    attended_at TIMESTAMP,
    counter_referral_notes TEXT,
    assigned_followup_asha_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- 9. High-Risk Patient Surveillance Registry
CREATE TABLE IF NOT EXISTS high_risk_registry (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL CHECK(category IN ('Maternal High-Risk (HRP)', 'Child Malnutrition & Immunization', 'Chronic NCD (Diabetes/HTN/COPD)', 'Tuberculosis / Infectious')),
    risk_factors TEXT NOT NULL,
    severity_score INTEGER DEFAULT 1 CHECK(severity_score BETWEEN 1 AND 5),
    assigned_worker_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    last_assessment_date DATE,
    next_followup_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'Active Surveillance' CHECK(status IN ('Active Surveillance', 'Controlled', 'Critical Escalation', 'Resolved')),
    clinical_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    appointment_number VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(20) NOT NULL,
    type VARCHAR(30) DEFAULT 'Consultation' CHECK(type IN ('Consultation', 'Follow-up', 'Emergency', 'Teleconsultation', 'Routine Checkup')),
    status VARCHAR(30) DEFAULT 'Booked' CHECK(status IN ('Booked', 'Checked-in', 'In Consultation', 'Completed', 'Cancelled', 'No-Show')),
    token_number INTEGER,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Consultations
CREATE TABLE IF NOT EXISTS consultations (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER UNIQUE REFERENCES appointments(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    symptoms TEXT,
    diagnosis TEXT NOT NULL,
    icd_code VARCHAR(50),
    examination_notes TEXT,
    treatment_plan TEXT,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Central Medicines Catalog
CREATE TABLE IF NOT EXISTS medicines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    brand_name VARCHAR(150) NOT NULL,
    generic_name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    form VARCHAR(50) NOT NULL,
    strength VARCHAR(50),
    unit_price NUMERIC(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 20,
    batch_number VARCHAR(50),
    expiry_date DATE,
    manufacturer VARCHAR(150),
    location_rack VARCHAR(50),
    is_essential_life_saving INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Cross-Facility Medicine Inventory Grid
CREATE TABLE IF NOT EXISTS facility_inventory (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER DEFAULT 15,
    last_restocked DATE,
    UNIQUE(facility_id, medicine_id)
);

-- 14. Prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id SERIAL PRIMARY KEY,
    prescription_number VARCHAR(50) NOT NULL UNIQUE,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    status VARCHAR(30) DEFAULT 'Pending' CHECK(status IN ('Pending', 'Partially Dispensed', 'Dispensed', 'Cancelled')),
    special_instructions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Prescription Items
CREATE TABLE IF NOT EXISTS prescription_items (
    id SERIAL PRIMARY KEY,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE RESTRICT,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    duration_days INTEGER NOT NULL,
    instructions TEXT,
    quantity_prescribed INTEGER NOT NULL,
    quantity_dispensed INTEGER DEFAULT 0,
    is_dispensed INTEGER DEFAULT 0
);

-- 16. Pharmacy Dispenses
CREATE TABLE IF NOT EXISTS pharmacy_dispenses (
    id SERIAL PRIMARY KEY,
    prescription_id INTEGER REFERENCES prescriptions(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    pharmacist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    notes TEXT,
    dispensed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Wards & Beds
CREATE TABLE IF NOT EXISTS wards (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK(type IN ('ICU', 'Emergency', 'General Ward', 'Private Deluxe', 'Semi-Private', 'Pediatric', 'Maternity', 'Surgical Ward')),
    floor VARCHAR(50) NOT NULL,
    total_beds INTEGER NOT NULL,
    daily_rate NUMERIC(10, 2) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS beds (
    id SERIAL PRIMARY KEY,
    ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
    bed_number VARCHAR(50) NOT NULL,
    status VARCHAR(30) DEFAULT 'Available' CHECK(status IN ('Available', 'Occupied', 'Maintenance', 'Reserved')),
    current_admission_id INTEGER,
    UNIQUE(ward_id, bed_number)
);

-- 18. Admissions (IPD)
CREATE TABLE IF NOT EXISTS admissions (
    id SERIAL PRIMARY KEY,
    admission_number VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    bed_id INTEGER NOT NULL REFERENCES beds(id) ON DELETE RESTRICT,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discharged_at TIMESTAMP,
    admission_reason TEXT NOT NULL,
    discharge_summary TEXT,
    discharge_condition VARCHAR(100),
    status VARCHAR(30) DEFAULT 'Admitted' CHECK(status IN ('Admitted', 'Discharged', 'Transferred'))
);

-- 19. Lab Tests Catalog & Cross-Facility Diagnostic Availability
CREATE TABLE IF NOT EXISTS lab_tests_catalog (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK(category IN ('Hematology', 'Biochemistry', 'Pathology', 'Radiology', 'Microbiology', 'Serology', 'Cardiology')),
    cost NUMERIC(10, 2) NOT NULL,
    turnaround_hours INTEGER DEFAULT 24,
    specimen_type VARCHAR(100),
    parameters_json TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS facility_diagnostics (
    id SERIAL PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES lab_tests_catalog(id) ON DELETE CASCADE,
    is_operational INTEGER DEFAULT 1,
    equipment_status VARCHAR(50) DEFAULT 'Working' CHECK(equipment_status IN ('Working', 'Calibrating', 'Under Maintenance', 'Reagent Out of Stock')),
    average_wait_hours NUMERIC(4, 1) DEFAULT 2.0,
    UNIQUE(facility_id, test_id)
);

-- 20. Lab Orders & Items
CREATE TABLE IF NOT EXISTS lab_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    teleconsult_id INTEGER REFERENCES teleconsultations(id) ON DELETE SET NULL,
    status VARCHAR(30) DEFAULT 'Ordered' CHECK(status IN ('Ordered', 'Sample Collected', 'In Testing', 'Completed', 'Cancelled')),
    clinical_notes TEXT,
    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sample_collected_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_order_items (
    id SERIAL PRIMARY KEY,
    lab_order_id INTEGER NOT NULL REFERENCES lab_orders(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES lab_tests_catalog(id) ON DELETE RESTRICT,
    status VARCHAR(30) DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    results_json TEXT,
    interpretation TEXT,
    technician_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    performed_at TIMESTAMP
);

-- 21. Invoices & Billing
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    admission_id INTEGER REFERENCES admissions(id) ON DELETE SET NULL,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    tax_percent NUMERIC(5, 2) DEFAULT 0.0,
    tax_amount NUMERIC(10, 2) DEFAULT 0.0,
    discount_amount NUMERIC(10, 2) DEFAULT 0.0,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    amount_paid NUMERIC(10, 2) DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'Paid' CHECK(status IN ('Unpaid', 'Partially Paid', 'Paid', 'Cancelled', 'Govt Subsidized (100%)')),
    payment_method VARCHAR(50) CHECK(payment_method IN ('Cash', 'Credit Card', 'Debit Card', 'UPI / QR', 'Insurance', 'PM-JAY Scheme (Cashless)', 'Free Public Service')),
    due_date DATE,
    paid_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL CHECK(item_type IN ('Consultation', 'Lab Test', 'Pharmacy', 'Bed / Ward', 'Nursing Care', 'Teleconsultation', 'Procedure', 'Miscellaneous')),
    description TEXT NOT NULL,
    reference_id INTEGER,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    total_price NUMERIC(10, 2) NOT NULL DEFAULT 0.0
);

-- 22. Audit Trail
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    module VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
