# 🏥 PulseCare Public Health & Rural Telemedicine Network

**PulseCare** is an integrated care-access, telemedicine, and quality support platform designed specifically for **Rural & Tiered Public Health Delivery Networks**. It strengthens the public health system by connecting **Sub-Centres (Health & Wellness Centres), Primary Health Centres (PHCs), Community Health Centres (CHCs)**, and **District Multi-Specialty Hospitals** into an interoperable continuum of care.

---

## 🎯 Addressing Rural & Primary Healthcare Challenges

| Rural Healthcare Challenge | PulseCare Solution Module |
| :--- | :--- |
| **Long travel distances & specialist shortages** | **Assisted Teleconsultations**: Frontline ASHA/CHO workers connect rural patients directly to District Specialists via HD WebRTC video & telemetry vitals. |
| **Delayed emergency referrals & transport bottlenecks** | **108 Emergency Escalation & Closed-Loop Referral Tracking**: Real-time ambulance dispatch with specialist pre-arrival notification and counter-referral instructions sent back to ASHA workers for home follow-up. |
| **Fragmented records across sub-centres & hospitals** | **Longitudinal Patient 360° EHR & ABHA / FHIR Interoperability**: 14-digit National Health Account (`91-XXXX-XXXX-XXXX`) with 1-click HL7 FHIR Bundle JSON export. |
| **High maternal/infant mortality & chronic NCD dropouts** | **High-Risk Patient Surveillance Registry**: Active cohort monitoring for High-Risk Pregnancies (Pre-eclampsia, Severe Anemia), Child Malnutrition (SAM/MAM), and Chronic NCDs (Diabetes, Hypertension). |
| **Irregular diagnostics & drug stockouts** | **Cross-Facility Availability Grid**: Real-time visibility of essential life-saving drugs (Anti-Snake Venom, Oxytocin, Insulin) and working diagnostic equipment (Ultrasound, ECG, X-Ray) across nearby facilities. |
| **Low connectivity & digital literacy barriers** | **Low-Connectivity Offline Sync & Multilingual Support**: Built-in 6-language switcher (English, Hindi, Tamil, Telugu, Bengali, Spanish) and automated offline data synchronization. |

---

## 🌟 Key Functional Modules

```mermaid
graph TD
    subgraph Tiered Healthcare Network
        SC[Sub-Centre / Health & Wellness Centre<br/>ASHA / ANM / CHO]
        PHC[Primary Health Centre - PHC<br/>Medical Officer / Staff Nurse]
        CHC[Community Health Centre / Rural Hospital<br/>General Specialists & Labs]
        DH[District Hospital / Tertiary Hub<br/>Super-specialists & ICU]
    end

    SC -->|Assisted Teleconsult & Triage| PHC
    SC -->|High-Risk Escalation| DH
    PHC -->|Teleconsult & Closed-Loop Referral| DH
    CHC -->|Diagnostic & Bed Coordination| DH
    DH -->|Counter-Referral & Follow-up Protocols| SC

    subgraph Core Platform Capabilities
        Teleconsult[Assisted Teleconsultation Suite with Live Vitals & Audio/Video]
        Triage[Digital Triage & Red/Yellow/Green Emergency Escalation]
        ReferralEngine[Inter-Facility Closed-Loop Referral Tracking]
        HighRiskRegistry[High-Risk Registry: Maternal ANC/PNC, Child Immunization, NCDs]
        SupplyChain[Cross-Facility Medicine & Diagnostic Availability Grid]
        ABDM[ABHA / ABDM & FHIR Interoperable Health Records]
        Multilingual[Multilingual Support & Low-Literacy Voice/Visual Aids]
        OfflineSync[Low-Connectivity Offline Mode & Data Sync]
    end

    Tiered Healthcare Network <--> Core Platform Capabilities
    Core Platform Capabilities <--> DB[(SQLite Database: pulsecare.db)]
```

### 1. 👥 Multi-Role Stakeholder Personas & 1-Click Role Switcher
- **Frontline Health Worker (ASHA / CHO)** (`asha.sunita` / `cho.priya`): Field registration, point-of-care vitals telemetry, assisted teleconsultation initiation, and home surveillance logs.
- **PHC Medical Officer** (`dr.rajesh`): Primary OPD consultations, digital triage, laboratory requisitions, and secondary/tertiary referral initiation.
- **District Hospital Specialist** (`dr.sarah` / `dr.anita` / `dr.elena`): Teleconsultation chamber, specialized SOAP diagnosis, e-prescriptions, and counter-referral guidance.
- **District Health Director / Admin** (`admin`): Network quality analytics, facility capacity tracking, staff directory, and audit logs.
- **Inpatient Ward Nurse** (`nurse.clara`): Visual bed matrix, patient admission, transfer, and discharge.
- **Pharmacist** (`pharm.robert`): Central drug catalog, stockout alerts, and prescription dispensing.
- **Lab Technician** (`lab.lisa`): Specimen collection, parameter result entry, and verified diagnostic reports.
- **Patient Portal** (`patient.meena` / `patient.john`): Personal health record, upcoming teleconsultations, active prescriptions, and ABHA card.

---

## 🚀 Getting Started

### 1. Installation
```bash
cd d:\antigravity
python -m pip install -r requirements.txt
```

### 2. Initialize Database & Seed Network Data
```bash
python seed_data.py
```

### 3. Start the Web Server
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🔑 Demo Login Accounts

| Role | Username | Password | Persona & Facility |
| :--- | :--- | :--- | :--- |
| **ASHA Worker** | `asha.sunita` | `password123` | Sunita Devi (Rampur Sub-Centre) |
| **Community Health Officer** | `cho.priya` | `password123` | Priya Sharma (Bilaspur HWC) |
| **PHC Medical Officer** | `dr.rajesh` | `password123` | Dr. Rajesh Verma (Chandpur PHC) |
| **District Specialist (OBGYN)** | `dr.anita` | `password123` | Dr. Anita Desai (District Hospital) |
| **District Specialist (Cardiology)** | `dr.sarah` | `password123` | Dr. Sarah Jenkins (District Hospital) |
| **Chief Medical Officer (Admin)** | `admin` | `password123` | Dr. Arthur Vance (District Health Complex) |
| **Ward Nurse** | `nurse.clara` | `password123` | Clara Oswald (District Hospital) |
| **Pharmacist** | `pharm.robert` | `password123` | Robert Taylor (District Central Pharmacy) |
| **Lab Pathologist** | `lab.lisa` | `password123` | Lisa Ray (District Pathology Lab) |
| **Rural Patient (HRP)** | `patient.meena` | `password123` | Meena Devi (Rampur Village • ABHA Linked) |

---

## 🧪 Running Automated Tests

Run the complete 10-point test suite verifying all public health network capabilities:
```bash
python -m unittest -v tests/test_public_health.py
```

---

## 🚀 Deployment to Render / Cloud Hosting

- **Render**: Pre-configured with [`render.yaml`](file:///d:/antigravity/render.yaml) and [`Procfile`](file:///d:/antigravity/Procfile). Connect your GitHub repo on [Render](https://render.com).
- **WSGI / Gunicorn**: Run with `gunicorn app:app --bind 0.0.0.0:8000`.
