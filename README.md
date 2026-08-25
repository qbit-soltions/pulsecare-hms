# 🏥 PulseCare Hospital Management System (HMS)

**PulseCare HMS** is an enterprise-grade, full-stack Hospital Management & Electronic Health Record (EHR) System built with Python, Flask, SQLite, and modern responsive web technologies. It provides end-to-end management of clinical, administrative, operational, diagnostic, and financial workflows across a multi-specialty hospital.

---

## 🌟 Key Feature Modules

### 1. 👥 Role-Based Access Control (RBAC) & Interactive Persona Switcher
- **7 Pre-configured Healthcare Roles**:
  - **Hospital Administrator** (`admin`): Full operational oversight, KPI analytics, staff directory, hospital profile settings, and security audit logs.
  - **Doctor / Specialist** (`dr.sarah`): Outpatient (OPD) queue, clinical consultation chamber, SOAP notes, ICD-10 diagnosis, electronic prescriptions, and diagnostic lab ordering.
  - **Inpatient Ward Nurse** (`nurse.clara`): Visual bed matrix, vital signs recording (with auto-BMI calculation), patient admission, transfer, and discharge summaries.
  - **Front Desk Receptionist** (`reception.emma`): Patient registration (auto-generated UID), appointment scheduling, OPD token dispatch, and invoice creation.
  - **Pharmacist** (`pharm.robert`): Central drug inventory, reorder threshold alerts, batch & expiry tracking, and 1-click prescription fulfillment/dispensing.
  - **Lab Technician** (`lab.lisa`): Diagnostic test queue, specimen collection status, parameter result entry with abnormal flags, and verified clinical diagnostic report generation.
  - **Patient Portal** (`patient.john`): Personal health record, upcoming appointments, active prescriptions, verified lab reports, and billing receipts.
- **Top Persona Switcher**: Persistent 1-click demo switcher bar at the top of every screen to seamlessly test and showcase all 7 stakeholder perspectives.

### 2. 🗂️ Patient Electronic Health Records (Patient 360° EHR)
- Patient Registration with unique identification format (`PC-YYYY-XXXX`).
- Comprehensive medical profile: Demographics, blood group, allergies (highlighted in alerts), chronic illnesses, next-of-kin emergency contact, and insurance details.
- Longitudinal EHR Tabs: Consultations timeline, prescription history, lab test results, vital signs graphs, admission stays, and billing ledger.

### 3. 🗓️ OPD Appointments & Live TV Waiting Room Display
- Multi-specialty scheduling by doctor, department, and time slot.
- Automated token number assignment.
- **Live OPD Queue Board (`/appointments/queue`)**: High-contrast, auto-refreshing waiting room display designed for hospital lobby monitors and clinic TVs.

### 4. 🩺 Clinical Consultation Chamber & E-Prescriptions
- Standardized **SOAP Clinical Notes** (Subjective complaints, Objective findings, Assessment/Diagnosis with ICD-10, Treatment Plan).
- Dynamic **E-Prescription Builder**: Real-time line-item addition with dosage, frequency, duration, instructions, and pharmacy stock validation.
- Direct **Diagnostic Requisitions**: Select from hematology, biochemistry, cardiology, and radiology test catalogs.

### 5. 🛏️ Hospital Ward & Bed Occupancy Matrix
- Visual grid of hospital wards (ICU, Emergency Trauma, General Ward Male/Female, Private Deluxe, Pediatric).
- Color-coded bed status cards (Available, Occupied, Maintenance/Cleaning).
- Patient details, attending doctor, and length of stay displayed on occupied beds.
- Streamlined Modal Workflows for **Admit Patient**, **Discharge Patient**, and **Maintenance Toggle**.

### 6. 💊 Pharmacy & Inventory Control
- Drug catalog with brand name, generic name, category, strength, formulation, unit pricing, batch number, and expiry date.
- Real-time low-stock and out-of-stock badge alerts.
- Dispensing queue connected to doctor prescriptions with automated stock deduction.

### 7. 🔬 Laboratory Diagnostics & Printable Reports
- Complete diagnostic workflow: Ordered ➔ Sample Collected ➔ In Testing ➔ Completed & Verified.
- Parameter-level result entry with biological reference intervals and automated abnormal flags.
- **Print-ready Verified Diagnostic Report** with hospital letterhead and pathologist sign-off.

### 8. 💳 Integrated Billing, Invoicing & Payments
- Itemized invoice generator rolling up consultation fees, bed stay charges, lab investigations, and pharmacy medications.
- Configurable tax percentage, discount subtotals, and multiple payment modes (Cash, Credit Card, UPI/QR, Insurance Pre-auth).
- **Print-ready Itemized Medical Bill & Receipt** with cashier authentication seal.

---

## 🚀 Deployment Guide

### Option A: Deploy to Netlify (Configured in Project)

Your repository is now pre-configured for Netlify with [`netlify.toml`](file:///d:/antigravity/netlify.toml) and [`netlify/functions/app.py`](file:///d:/antigravity/netlify/functions/app.py).

#### 1. Push to GitHub:
```bash
git init
git add .
git commit -m "Initial PulseCare HMS release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pulsecare-hms.git
git push -u origin main
```

#### 2. Deploy on Netlify:
1. Go to [app.netlify.com](https://app.netlify.com) and log in.
2. Click **"Add new site"** ➔ **"Import an existing project"**.
3. Select **GitHub** and pick your `pulsecare-hms` repository.
4. Netlify will automatically detect `netlify.toml`:
   - **Build command**: `pip install -r requirements.txt && python seed_data.py`
   - **Publish directory**: `static`
   - **Functions directory**: `netlify/functions`
5. Click **"Deploy Site"** — your app is live!

---

### Option B: Deploy to Render (Alternative 1-Click Python Hosting)

Render provides a native persistent Python environment for Flask + SQLite:
1. Go to [Render.com](https://render.com) and create a free account.
2. Click **New +** ➔ **Web Service** and select your GitHub repository.
3. Render will auto-detect [`render.yaml`](file:///d:/antigravity/render.yaml) or set:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python seed_data.py`
   - **Start Command**: `gunicorn app:app`
4. Click **Create Web Service**.

---

## 💻 Local Development Setup

---

## 🔑 Demo Login Accounts

| Role | Username | Password | Persona & Department |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `password123` | Dr. Arthur Vance (Chief Medical Officer) |
| **Doctor** | `dr.sarah` | `password123` | Dr. Sarah Jenkins (Cardiology OPD) |
| **Doctor** | `dr.marcus` | `password123` | Dr. Marcus Brody (Neurology) |
| **Doctor** | `dr.aisha` | `password123` | Dr. Aisha Patel (General Medicine & Diabetology) |
| **Nurse** | `nurse.clara` | `password123` | Clara Oswald (ICU Head Nurse) |
| **Receptionist** | `reception.emma` | `password123` | Emma Watson (Front Desk Lead) |
| **Pharmacist** | `pharm.robert` | `password123` | Robert Taylor (Chief Pharmacist) |
| **Lab Tech** | `lab.lisa` | `password123` | Lisa Ray (Senior Pathologist) |
| **Patient** | `patient.john` | `password123` | John Doe (Patient Portal) |

*(Note: You can also switch roles anytime using the top navigation switcher bar or the 1-click login buttons on the Sign In page).*

---

## 🧪 Running Automated Tests

Run the complete 10-point end-to-end automated test suite:
```bash
python -m unittest -v tests/test_hms.py
```

---

## 📁 Project Architecture

```
d:\antigravity\
├── app.py                     # Main Flask web application & API routing
├── models.py                  # Database connection, query helpers & audit logger
├── schema.sql                 # Complete relational SQLite schema (20 tables)
├── seed_data.py               # Comprehensive realistic medical dataset generator
├── requirements.txt           # Python dependencies (Flask, Werkzeug)
├── README.md                  # System documentation & usage guide
├── pulsecare.db               # SQLite relational database
├── static/
│   ├── css/
│   │   └── styles.css         # Medical UI design system & @media print styles
│   └── js/
│       └── main.js            # Dynamic prescription & invoice builder, search filters
├── templates/
│   ├── base.html              # Master layout with sidebar, topbar & role switcher
│   ├── auth/
│   │   └── login.html         # Login page with 1-click persona quick selector
│   ├── dashboard/
│   │   └── index.html         # Role-aware operational & clinical KPI dashboard
│   ├── patients/
│   │   ├── index.html         # Patient directory & multi-filter search
│   │   ├── view.html          # Comprehensive Patient 360° EHR Profile
│   │   └── form.html          # Patient registration & edit form
│   ├── appointments/
│   │   ├── index.html         # Appointment scheduler & status pipeline
│   │   └── queue.html         # Live OPD TV waiting room display board
│   ├── consultations/
│   │   └── form.html          # Clinical consultation room & e-prescription builder
│   ├── wards/
│   │   └── index.html         # Visual bed occupancy matrix (ICU, ER, General, Private)
│   ├── pharmacy/
│   │   └── index.html         # Medicine inventory, low-stock alerts & dispense queue
│   ├── laboratory/
│   │   ├── index.html         # Lab orders queue & parameter result entry
│   │   └── report.html        # Print-ready verified diagnostic lab report
│   ├── billing/
│   │   ├── index.html         # Invoices ledger & dynamic bill creator
│   │   └── invoice.html       # Print-ready itemized medical invoice & receipt
│   ├── staff/
│   │   └── index.html         # Medical staff directory & department management
│   └── settings/
│       ├── index.html         # Hospital profile & tax configuration
│       └── audit_logs.html    # Security activity & audit log trail
└── tests/
    ├── __init__.py
    └── test_hms.py            # Automated integration & unit test suite
```
