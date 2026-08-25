-- PulseCare Hospital Management System Database Schema
PRAGMA foreign_keys = ON;

-- 1. Hospital Settings
CREATE TABLE IF NOT EXISTS hospital_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 2. Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    head_doctor_name TEXT,
    color TEXT DEFAULT '#0d6efd',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users & Staff
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'nurse', 'receptionist', 'pharmacist', 'lab_tech', 'patient')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    specialization TEXT,
    qualification TEXT,
    license_number TEXT,
    consultation_fee REAL DEFAULT 0.0,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Patients
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_uid TEXT NOT NULL UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob DATE NOT NULL,
    gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
    blood_group TEXT,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relation TEXT,
    allergies TEXT,
    chronic_conditions TEXT,
    insurance_provider TEXT,
    insurance_policy_number TEXT,
    status TEXT DEFAULT 'Outpatient' CHECK(status IN ('Outpatient', 'Inpatient', 'Discharged', 'Critical')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Patient Vitals
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recorded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
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
    notes TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    appointment_date DATE NOT NULL,
    appointment_time TEXT NOT NULL,
    type TEXT DEFAULT 'Consultation' CHECK(type IN ('Consultation', 'Follow-up', 'Emergency', 'Routine Checkup')),
    status TEXT DEFAULT 'Booked' CHECK(status IN ('Booked', 'Checked-in', 'In Consultation', 'Completed', 'Cancelled', 'No-Show')),
    token_number INTEGER,
    reason TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. Consultations
CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER UNIQUE REFERENCES appointments(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symptoms TEXT,
    diagnosis TEXT NOT NULL,
    icd_code TEXT,
    examination_notes TEXT,
    treatment_plan TEXT,
    follow_up_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. Pharmacy Catalog (Medicines)
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_number TEXT NOT NULL UNIQUE,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Partially Dispensed', 'Dispensed', 'Cancelled')),
    special_instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. Prescription Items
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

-- 11. Pharmacy Dispense Logs
CREATE TABLE IF NOT EXISTS pharmacy_dispenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER REFERENCES prescriptions(id) ON DELETE SET NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    pharmacist_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    total_amount REAL NOT NULL DEFAULT 0.0,
    notes TEXT,
    dispensed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 12. Hospital Wards
CREATE TABLE IF NOT EXISTS wards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('ICU', 'Emergency', 'General Ward', 'Private Deluxe', 'Semi-Private', 'Pediatric', 'Maternity', 'Surgical Ward')),
    floor TEXT NOT NULL,
    total_beds INTEGER NOT NULL,
    daily_rate REAL NOT NULL,
    description TEXT
);

-- 13. Beds
CREATE TABLE IF NOT EXISTS beds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
    bed_number TEXT NOT NULL,
    status TEXT DEFAULT 'Available' CHECK(status IN ('Available', 'Occupied', 'Maintenance', 'Reserved')),
    current_admission_id INTEGER,
    UNIQUE(ward_id, bed_number)
);

-- 14. Admissions (IPD)
CREATE TABLE IF NOT EXISTS admissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    bed_id INTEGER NOT NULL REFERENCES beds(id) ON DELETE RESTRICT,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discharged_at DATETIME,
    admission_reason TEXT NOT NULL,
    discharge_summary TEXT,
    discharge_condition TEXT,
    status TEXT DEFAULT 'Admitted' CHECK(status IN ('Admitted', 'Discharged', 'Transferred'))
);

-- 15. Lab Tests Catalog
CREATE TABLE IF NOT EXISTS lab_tests_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Hematology', 'Biochemistry', 'Pathology', 'Radiology', 'Microbiology', 'Serology', 'Cardiology')),
    cost REAL NOT NULL,
    turnaround_hours INTEGER DEFAULT 24,
    specimen_type TEXT,
    parameters_json TEXT, -- JSON structure of sub-parameters with units and reference ranges
    description TEXT
);

-- 16. Lab Orders
CREATE TABLE IF NOT EXISTS lab_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consultation_id INTEGER REFERENCES consultations(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'Ordered' CHECK(status IN ('Ordered', 'Sample Collected', 'In Testing', 'Completed', 'Cancelled')),
    clinical_notes TEXT,
    ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sample_collected_at DATETIME,
    completed_at DATETIME
);

-- 17. Lab Order Items
CREATE TABLE IF NOT EXISTS lab_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_order_id INTEGER NOT NULL REFERENCES lab_orders(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES lab_tests_catalog(id) ON DELETE RESTRICT,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    results_json TEXT, -- JSON structure of recorded test values
    interpretation TEXT,
    technician_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    performed_at DATETIME
);

-- 18. Invoices & Billing
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    admission_id INTEGER REFERENCES admissions(id) ON DELETE SET NULL,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    subtotal REAL NOT NULL DEFAULT 0.0,
    tax_percent REAL DEFAULT 5.0,
    tax_amount REAL DEFAULT 0.0,
    discount_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    amount_paid REAL DEFAULT 0.0,
    status TEXT DEFAULT 'Unpaid' CHECK(status IN ('Unpaid', 'Partially Paid', 'Paid', 'Cancelled')),
    payment_method TEXT CHECK(payment_method IN ('Cash', 'Credit Card', 'Debit Card', 'UPI / QR', 'Insurance', 'Net Banking', 'Cheque')),
    due_date DATE,
    paid_at DATETIME,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 19. Invoice Items
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK(item_type IN ('Consultation', 'Lab Test', 'Pharmacy', 'Bed / Ward', 'Nursing Care', 'Procedure', 'Miscellaneous')),
    description TEXT NOT NULL,
    reference_id INTEGER,
    quantity REAL NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    total_price REAL NOT NULL DEFAULT 0.0
);

-- 20. Audit Trail
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    module TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_patients_uid ON patients(patient_uid);
CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_beds_ward ON beds(ward_id);
CREATE INDEX IF NOT EXISTS idx_admissions_patient ON admissions(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_orders_patient ON lab_orders(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoices_patient ON invoices(patient_id);
