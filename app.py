"""
PulseCare Hospital Management System - Main Application Server
"""
import os
import json
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, abort, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import (
    query_db, execute_db, execute_many_db, log_audit,
    get_setting, set_setting, get_db_connection
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pulsecare-hms-secret-key-2026-secure")
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Context Processors & Template Filters
@app.context_processor
def inject_global_context():
    """Injects hospital settings, current user, notifications, and active role info into all templates."""
    user = None
    if "user_id" in session:
        user = query_db(
            """SELECT u.*, d.name as department_name, d.code as department_code 
               FROM users u 
               LEFT JOIN departments d ON u.department_id = d.id 
               WHERE u.id = ?""",
            (session["user_id"],),
            one=True
        )

    # Quick system counts for top notification badges
    low_stock_count = 0
    pending_lab_count = 0
    today_apt_count = 0
    try:
        low_stock_row = query_db("SELECT COUNT(*) as c FROM medicines WHERE stock_quantity <= reorder_level", one=True)
        low_stock_count = low_stock_row["c"] if low_stock_row else 0
        
        pending_lab_row = query_db("SELECT COUNT(*) as c FROM lab_orders WHERE status IN ('Ordered', 'Sample Collected', 'In Testing')", one=True)
        pending_lab_count = pending_lab_row["c"] if pending_lab_row else 0

        today_str = date.today().strftime("%Y-%m-%d")
        today_apt_row = query_db("SELECT COUNT(*) as c FROM appointments WHERE appointment_date = ? AND status != 'Cancelled'", (today_str,), one=True)
        today_apt_count = today_apt_row["c"] if today_apt_row else 0
    except Exception:
        pass

    return {
        "current_user": user,
        "hospital_name": get_setting("hospital_name", "PulseCare Multispecialty Hospital"),
        "currency": get_setting("currency", "$"),
        "today_date": date.today().strftime("%Y-%m-%d"),
        "now_datetime": datetime.now(),
        "low_stock_count": low_stock_count,
        "pending_lab_count": pending_lab_count,
        "today_apt_count": today_apt_count
    }

@app.template_filter("fromjson")
def fromjson_filter(value):
    """Template filter to parse JSON strings."""
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

@app.template_filter("format_date")
def format_date_filter(value, fmt="%b %d, %Y"):
    """Formats date strings."""
    if not value:
        return "—"
    try:
        if isinstance(value, (datetime, date)):
            return value.strftime(fmt)
        # Parse ISO or SQLite datetime
        clean_val = str(value).split(".")[0]
        if " " in clean_val:
            dt = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(clean_val, "%Y-%m-%d")
        return dt.strftime(fmt)
    except Exception:
        return str(value)

# Auth Decorator & RBAC Helpers
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access PulseCare HMS.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_accepted(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("login", next=request.url))
            user_role = session.get("user_role")
            if "admin" not in roles and user_role not in roles and user_role != "admin":
                flash(f"Access Denied: Your role ({user_role.title()}) is not authorized to view this page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# -----------------------------------------------------------------------------
# 1. AUTHENTICATION & ROLE SWITCHER
# -----------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = query_db("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_role"] = user["role"]
            session["full_name"] = user["full_name"]
            
            log_audit(user["id"], "User Login", "Auth", f"User {user['username']} logged in as {user['role']}", request.remote_addr)
            flash(f"Welcome back, {user['full_name']}!", "success")
            
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    # Get sample demo accounts for 1-click preview
    demo_users = query_db(
        """SELECT u.*, d.name as department_name 
           FROM users u 
           LEFT JOIN departments d ON u.department_id = d.id 
           WHERE u.username IN ('admin', 'dr.sarah', 'nurse.clara', 'reception.emma', 'pharm.robert', 'lab.lisa', 'patient.john')
           ORDER BY u.id"""
    )
    return render_template("auth/login.html", demo_users=demo_users)

@app.route("/logout")
def logout():
    if "user_id" in session:
        log_audit(session["user_id"], "User Logout", "Auth", f"User {session.get('username')} logged out", request.remote_addr)
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("login"))

@app.route("/switch-role/<role>")
def switch_role(role):
    """Helper route to quickly switch between active demo roles from the top toolbar."""
    role_user_map = {
        "admin": "admin",
        "doctor": "dr.sarah",
        "nurse": "nurse.clara",
        "receptionist": "reception.emma",
        "pharmacist": "pharm.robert",
        "lab_tech": "lab.lisa",
        "patient": "patient.john"
    }
    target_username = role_user_map.get(role, "admin")
    user = query_db("SELECT * FROM users WHERE username = ?", (target_username,), one=True)
    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["user_role"] = user["role"]
        session["full_name"] = user["full_name"]
        flash(f"Switched role to: {user['full_name']} ({user['role'].upper()})", "info")
    return redirect(request.referrer or url_for("dashboard"))


# -----------------------------------------------------------------------------
# 2. DASHBOARDS (ROLE-AWARE)
# -----------------------------------------------------------------------------

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("user_role", "admin")
    today_str = date.today().strftime("%Y-%m-%d")

    # High-level Hospital KPIs
    total_patients = query_db("SELECT COUNT(*) as c FROM patients", one=True)["c"]
    total_inpatient = query_db("SELECT COUNT(*) as c FROM admissions WHERE status = 'Admitted'", one=True)["c"]
    total_beds = query_db("SELECT COUNT(*) as c FROM beds", one=True)["c"]
    occupied_beds = query_db("SELECT COUNT(*) as c FROM beds WHERE status = 'Occupied'", one=True)["c"]
    bed_occupancy_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0

    revenue_total = query_db("SELECT SUM(amount_paid) as s FROM invoices WHERE status IN ('Paid', 'Partially Paid')", one=True)["s"] or 0.0
    pending_revenue = query_db("SELECT SUM(total_amount - amount_paid) as s FROM invoices WHERE status IN ('Unpaid', 'Partially Paid')", one=True)["s"] or 0.0

    # Today's appointments
    today_appointments = query_db(
        """SELECT a.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, 
                  u.full_name as doctor_name, d.name as department_name, d.color as dept_color
           FROM appointments a
           JOIN patients p ON a.patient_id = p.id
           JOIN users u ON a.doctor_id = u.id
           LEFT JOIN departments d ON a.department_id = d.id
           WHERE a.appointment_date = ?
           ORDER BY a.token_number ASC, a.appointment_time ASC""",
        (today_str,)
    )

    # Inpatient ward summary
    wards_summary = query_db(
        """SELECT w.*, 
                  COUNT(b.id) as total_beds_count,
                  SUM(CASE WHEN b.status = 'Occupied' THEN 1 ELSE 0 END) as occupied_count,
                  SUM(CASE WHEN b.status = 'Available' THEN 1 ELSE 0 END) as available_count
           FROM wards w
           LEFT JOIN beds b ON w.id = b.ward_id
           GROUP BY w.id"""
    )

    # Recent admissions
    recent_admissions = query_db(
        """SELECT adm.*, p.first_name, p.last_name, p.patient_uid, b.bed_number, w.name as ward_name, u.full_name as doctor_name
           FROM admissions adm
           JOIN patients p ON adm.patient_id = p.id
           JOIN beds b ON adm.bed_id = b.id
           JOIN wards w ON b.ward_id = w.id
           JOIN users u ON adm.doctor_id = u.id
           WHERE adm.status = 'Admitted'
           ORDER BY adm.admitted_at DESC LIMIT 5"""
    )

    # Doctor-specific data
    doctor_consults_today = []
    doctor_patients = []
    if role == "doctor":
        doctor_id = session.get("user_id")
        doctor_consults_today = query_db(
            """SELECT a.*, p.first_name, p.last_name, p.patient_uid, p.dob, p.gender, p.blood_group, p.allergies
               FROM appointments a
               JOIN patients p ON a.patient_id = p.id
               WHERE a.doctor_id = ? AND a.appointment_date = ?
               ORDER BY a.token_number ASC""",
            (doctor_id, today_str)
        )
        doctor_patients = query_db(
            """SELECT adm.*, p.first_name, p.last_name, p.patient_uid, b.bed_number, w.name as ward_name
               FROM admissions adm
               JOIN patients p ON adm.patient_id = p.id
               JOIN beds b ON adm.bed_id = b.id
               JOIN wards w ON b.ward_id = w.id
               WHERE adm.doctor_id = ? AND adm.status = 'Admitted'""",
            (doctor_id,)
        )

    # Patient-specific data (if logged in as patient)
    patient_data = None
    patient_appointments = []
    patient_prescriptions = []
    patient_lab_orders = []
    patient_invoices = []
    if role == "patient":
        patient_record = query_db("SELECT * FROM patients WHERE user_id = ?", (session.get("user_id"),), one=True)
        if patient_record:
            pid = patient_record["id"]
            patient_data = patient_record
            patient_appointments = query_db(
                """SELECT a.*, u.full_name as doctor_name, d.name as department_name 
                   FROM appointments a
                   JOIN users u ON a.doctor_id = u.id
                   LEFT JOIN departments d ON a.department_id = d.id
                   WHERE a.patient_id = ? ORDER BY a.appointment_date DESC""",
                (pid,)
            )
            patient_prescriptions = query_db(
                """SELECT pr.*, u.full_name as doctor_name,
                          (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = pr.id) as item_count
                   FROM prescriptions pr
                   JOIN users u ON pr.doctor_id = u.id
                   WHERE pr.patient_id = ? ORDER BY pr.created_at DESC""",
                (pid,)
            )
            patient_lab_orders = query_db(
                """SELECT lo.*, u.full_name as doctor_name,
                          (SELECT COUNT(*) FROM lab_order_items WHERE lab_order_id = lo.id) as test_count
                   FROM lab_orders lo
                   JOIN users u ON lo.doctor_id = u.id
                   WHERE lo.patient_id = ? ORDER BY lo.ordered_at DESC""",
                (pid,)
            )
            patient_invoices = query_db(
                "SELECT * FROM invoices WHERE patient_id = ? ORDER BY created_at DESC", (pid,)
            )

    # Recent Audit Activity
    recent_activities = query_db(
        """SELECT a.*, u.full_name as user_name, u.role as user_role, u.avatar_url
           FROM audit_logs a
           LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.timestamp DESC LIMIT 8"""
    )

    return render_template(
        "dashboard/index.html",
        total_patients=total_patients,
        total_inpatient=total_inpatient,
        total_beds=total_beds,
        occupied_beds=occupied_beds,
        bed_occupancy_rate=bed_occupancy_rate,
        revenue_total=revenue_total,
        pending_revenue=pending_revenue,
        today_appointments=today_appointments,
        wards_summary=wards_summary,
        recent_admissions=recent_admissions,
        doctor_consults_today=doctor_consults_today,
        doctor_patients=doctor_patients,
        patient_data=patient_data,
        patient_appointments=patient_appointments,
        patient_prescriptions=patient_prescriptions,
        patient_lab_orders=patient_lab_orders,
        patient_invoices=patient_invoices,
        recent_activities=recent_activities
    )


# -----------------------------------------------------------------------------
# 3. PATIENTS & ELECTRONIC HEALTH RECORDS (EHR)
# -----------------------------------------------------------------------------

@app.route("/patients")
@login_required
def patients_list():
    query_param = request.args.get("q", "").strip()
    status_param = request.args.get("status", "").strip()
    gender_param = request.args.get("gender", "").strip()

    sql = """
        SELECT p.*,
               (SELECT COUNT(*) FROM appointments WHERE patient_id = p.id) as appointment_count,
               (SELECT COUNT(*) FROM admissions WHERE patient_id = p.id AND status = 'Admitted') as is_admitted,
               (SELECT b.bed_number FROM admissions adm JOIN beds b ON adm.bed_id = b.id WHERE adm.patient_id = p.id AND adm.status = 'Admitted' LIMIT 1) as current_bed
        FROM patients p
        WHERE 1=1
    """
    params = []

    if query_param:
        sql += " AND (p.patient_uid LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR p.phone LIKE ? OR p.email LIKE ?)"
        pattern = f"%{query_param}%"
        params.extend([pattern, pattern, pattern, pattern, pattern])

    if status_param:
        sql += " AND p.status = ?"
        params.append(status_param)

    if gender_param:
        sql += " AND p.gender = ?"
        params.append(gender_param)

    sql += " ORDER BY p.created_at DESC"
    patients = query_db(sql, params)

    return render_template("patients/index.html", patients=patients, query=query_param, status_filter=status_param, gender_filter=gender_param)

@app.route("/patients/new", methods=["GET", "POST"])
@login_required
@roles_accepted("admin", "receptionist", "nurse", "doctor")
def patient_create():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        dob = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact_name = request.form.get("emergency_contact_name", "").strip()
        emergency_contact_phone = request.form.get("emergency_contact_phone", "").strip()
        emergency_contact_relation = request.form.get("emergency_contact_relation", "").strip()
        allergies = request.form.get("allergies", "").strip()
        chronic_conditions = request.form.get("chronic_conditions", "").strip()
        insurance_provider = request.form.get("insurance_provider", "").strip()
        insurance_policy_number = request.form.get("insurance_policy_number", "").strip()

        # Generate unique Patient UID
        count_row = query_db("SELECT COUNT(*) as c FROM patients", one=True)
        next_num = (count_row["c"] if count_row else 0) + 1
        patient_uid = f"PC-{date.today().year}-{next_num:04d}"

        patient_id = execute_db(
            """INSERT INTO patients (patient_uid, first_name, last_name, dob, gender, blood_group, phone, email, address,
                                     emergency_contact_name, emergency_contact_phone, emergency_contact_relation,
                                     allergies, chronic_conditions, insurance_provider, insurance_policy_number, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Outpatient')""",
            (patient_uid, first_name, last_name, dob, gender, blood_group, phone, email, address,
             emergency_contact_name, emergency_contact_phone, emergency_contact_relation,
             allergies, chronic_conditions, insurance_provider, insurance_policy_number)
        )

        log_audit(session.get("user_id"), "Create Patient", "Patients", f"Registered new patient {patient_uid} ({first_name} {last_name})", request.remote_addr)
        flash(f"Patient {first_name} {last_name} ({patient_uid}) registered successfully!", "success")
        return redirect(url_for("patient_view", patient_id=patient_id))

    return render_template("patients/form.html", patient=None, title="New Patient Registration")

@app.route("/patients/<int:patient_id>")
@login_required
def patient_view(patient_id):
    patient = query_db("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if not patient:
        abort(404, description="Patient record not found.")

    # Calculate age
    age = "Unknown"
    try:
        dob = datetime.strptime(patient["dob"], "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        pass

    # Vitals history
    vitals = query_db(
        """SELECT v.*, u.full_name as recorded_by_name 
           FROM vitals v 
           LEFT JOIN users u ON v.recorded_by_id = u.id 
           WHERE v.patient_id = ? 
           ORDER BY v.recorded_at DESC""",
        (patient_id,)
    )

    # Appointments history
    appointments = query_db(
        """SELECT a.*, u.full_name as doctor_name, d.name as department_name 
           FROM appointments a
           JOIN users u ON a.doctor_id = u.id
           LEFT JOIN departments d ON a.department_id = d.id
           WHERE a.patient_id = ?
           ORDER BY a.appointment_date DESC, a.appointment_time DESC""",
        (patient_id,)
    )

    # Consultations & SOAP notes
    consultations = query_db(
        """SELECT c.*, u.full_name as doctor_name, u.specialization as doctor_specialization,
                  a.appointment_number
           FROM consultations c
           JOIN users u ON c.doctor_id = u.id
           LEFT JOIN appointments a ON c.appointment_id = a.id
           WHERE c.patient_id = ?
           ORDER BY c.created_at DESC""",
        (patient_id,)
    )

    # Prescriptions
    prescriptions = query_db(
        """SELECT pr.*, u.full_name as doctor_name,
                  (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = pr.id) as item_count
           FROM prescriptions pr
           JOIN users u ON pr.doctor_id = u.id
           WHERE pr.patient_id = ?
           ORDER BY pr.created_at DESC""",
        (patient_id,)
    )
    for p in prescriptions:
        p_items = query_db(
            """SELECT pi.*, m.brand_name, m.generic_name, m.form, m.strength, m.unit_price 
               FROM prescription_items pi
               JOIN medicines m ON pi.medicine_id = m.id
               WHERE pi.prescription_id = ?""",
            (p["id"],)
        )
        p["rx_items"] = p_items
        p["items"] = p_items

    # Lab Orders
    lab_orders = query_db(
        """SELECT lo.*, u.full_name as doctor_name
           FROM lab_orders lo
           JOIN users u ON lo.doctor_id = u.id
           WHERE lo.patient_id = ?
           ORDER BY lo.ordered_at DESC""",
        (patient_id,)
    )
    for lo in lab_orders:
        lo_items = query_db(
            """SELECT loi.*, ltc.code as test_code, ltc.name as test_name, ltc.category as test_category, ltc.cost 
               FROM lab_order_items loi
               JOIN lab_tests_catalog ltc ON loi.test_id = ltc.id
               WHERE loi.lab_order_id = ?""",
            (lo["id"],)
        )
        lo["test_items"] = lo_items
        lo["items"] = lo_items

    # Inpatient Admissions
    admissions = query_db(
        """SELECT adm.*, b.bed_number, w.name as ward_name, w.type as ward_type, u.full_name as doctor_name
           FROM admissions adm
           JOIN beds b ON adm.bed_id = b.id
           JOIN wards w ON b.ward_id = w.id
           JOIN users u ON adm.doctor_id = u.id
           WHERE adm.patient_id = ?
           ORDER BY adm.admitted_at DESC""",
        (patient_id,)
    )

    # Invoices & Bills
    invoices = query_db(
        """SELECT * FROM invoices WHERE patient_id = ? ORDER BY created_at DESC""",
        (patient_id,)
    )

    # Active admission if any
    active_admission = next((adm for adm in admissions if adm["status"] == "Admitted"), None)

    # Available doctors and departments for quick appointment modal
    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")
    departments = query_db("SELECT id, name FROM departments ORDER BY name")
    available_beds = query_db(
        """SELECT b.id, b.bed_number, w.name as ward_name, w.type as ward_type, w.daily_rate 
           FROM beds b 
           JOIN wards w ON b.ward_id = w.id 
           WHERE b.status = 'Available' 
           ORDER BY w.name, b.bed_number"""
    )

    return render_template(
        "patients/view.html",
        patient=patient,
        age=age,
        vitals=vitals,
        appointments=appointments,
        consultations=consultations,
        prescriptions=prescriptions,
        lab_orders=lab_orders,
        admissions=admissions,
        active_admission=active_admission,
        invoices=invoices,
        doctors=doctors,
        departments=departments,
        available_beds=available_beds
    )

@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
@roles_accepted("admin", "receptionist", "nurse", "doctor")
def patient_edit(patient_id):
    patient = query_db("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if not patient:
        abort(404)

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        dob = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact_name = request.form.get("emergency_contact_name", "").strip()
        emergency_contact_phone = request.form.get("emergency_contact_phone", "").strip()
        emergency_contact_relation = request.form.get("emergency_contact_relation", "").strip()
        allergies = request.form.get("allergies", "").strip()
        chronic_conditions = request.form.get("chronic_conditions", "").strip()
        insurance_provider = request.form.get("insurance_provider", "").strip()
        insurance_policy_number = request.form.get("insurance_policy_number", "").strip()
        status = request.form.get("status", patient["status"]).strip()

        execute_db(
            """UPDATE patients SET 
               first_name = ?, last_name = ?, dob = ?, gender = ?, blood_group = ?,
               phone = ?, email = ?, address = ?, emergency_contact_name = ?, emergency_contact_phone = ?,
               emergency_contact_relation = ?, allergies = ?, chronic_conditions = ?,
               insurance_provider = ?, insurance_policy_number = ?, status = ?
               WHERE id = ?""",
            (first_name, last_name, dob, gender, blood_group, phone, email, address,
             emergency_contact_name, emergency_contact_phone, emergency_contact_relation,
             allergies, chronic_conditions, insurance_provider, insurance_policy_number, status, patient_id)
        )

        log_audit(session.get("user_id"), "Update Patient", "Patients", f"Updated details for patient {patient['patient_uid']}", request.remote_addr)
        flash(f"Patient profile for {first_name} {last_name} updated successfully!", "success")
        return redirect(url_for("patient_view", patient_id=patient_id))

    return render_template("patients/form.html", patient=patient, title="Edit Patient Details")

@app.route("/patients/<int:patient_id>/vitals/new", methods=["POST"])
@login_required
@roles_accepted("admin", "doctor", "nurse")
def record_vitals(patient_id):
    temp = request.form.get("temperature_c") or None
    hr = request.form.get("heart_rate_bpm") or None
    bp_sys = request.form.get("blood_pressure_sys") or None
    bp_dia = request.form.get("blood_pressure_dia") or None
    rr = request.form.get("respiratory_rate") or None
    spo2 = request.form.get("spo2_percent") or None
    weight = float(request.form.get("weight_kg")) if request.form.get("weight_kg") else None
    height = float(request.form.get("height_cm")) if request.form.get("height_cm") else None
    blood_sugar = request.form.get("blood_sugar_mgdl") or None
    notes = request.form.get("notes", "").strip()

    # BMI calculation
    bmi = None
    if weight and height and height > 0:
        height_m = height / 100.0
        bmi = round(weight / (height_m * height_m), 1)

    execute_db(
        """INSERT INTO vitals (patient_id, recorded_by_id, temperature_c, heart_rate_bpm, blood_pressure_sys, blood_pressure_dia,
                              respiratory_rate, spo2_percent, weight_kg, height_cm, bmi, blood_sugar_mgdl, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, session.get("user_id"), temp, hr, bp_sys, bp_dia, rr, spo2, weight, height, bmi, blood_sugar, notes)
    )

    log_audit(session.get("user_id"), "Record Vitals", "Vitals", f"Recorded new vitals for patient ID {patient_id}", request.remote_addr)
    flash("Patient vital signs recorded successfully!", "success")
    return redirect(url_for("patient_view", patient_id=patient_id))


# -----------------------------------------------------------------------------
# 4. APPOINTMENTS & OPD QUEUE
# -----------------------------------------------------------------------------

@app.route("/appointments")
@login_required
def appointments_list():
    date_filter = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    doc_filter = request.args.get("doctor_id", "")
    dept_filter = request.args.get("department_id", "")
    status_filter = request.args.get("status", "")

    sql = """
        SELECT a.*, p.first_name, p.last_name, p.patient_uid, p.phone as patient_phone, p.gender, p.dob,
               u.full_name as doctor_name, u.specialization as doctor_spec,
               d.name as department_name, d.color as dept_color
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON a.doctor_id = u.id
        LEFT JOIN departments d ON a.department_id = d.id
        WHERE 1=1
    """
    params = []

    if date_filter:
        sql += " AND a.appointment_date = ?"
        params.append(date_filter)

    if doc_filter:
        sql += " AND a.doctor_id = ?"
        params.append(doc_filter)

    if dept_filter:
        sql += " AND a.department_id = ?"
        params.append(dept_filter)

    if status_filter:
        sql += " AND a.status = ?"
        params.append(status_filter)

    sql += " ORDER BY a.token_number ASC, a.appointment_time ASC"
    appointments = query_db(sql, params)

    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")
    departments = query_db("SELECT id, name FROM departments ORDER BY name")
    patients = query_db("SELECT id, patient_uid, first_name, last_name, phone FROM patients ORDER BY first_name")

    return render_template(
        "appointments/index.html",
        appointments=appointments,
        date_filter=date_filter,
        doc_filter=doc_filter,
        dept_filter=dept_filter,
        status_filter=status_filter,
        doctors=doctors,
        departments=departments,
        patients=patients
    )

@app.route("/appointments/new", methods=["POST"])
@login_required
@roles_accepted("admin", "receptionist", "doctor", "nurse")
def appointment_create():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    department_id = request.form.get("department_id") or None
    apt_date = request.form.get("appointment_date", date.today().strftime("%Y-%m-%d"))
    apt_time = request.form.get("appointment_time", "09:00 AM")
    apt_type = request.form.get("type", "Consultation")
    reason = request.form.get("reason", "").strip()

    # Generate appointment number and token
    count_row = query_db("SELECT COUNT(*) as c FROM appointments", one=True)
    apt_num = f"APT-{date.today().year}-{(count_row['c'] + 1):04d}"

    # Calculate next token number for this doctor and date
    token_row = query_db(
        "SELECT MAX(token_number) as max_token FROM appointments WHERE doctor_id = ? AND appointment_date = ?",
        (doctor_id, apt_date),
        one=True
    )
    next_token = (token_row["max_token"] or 0) + 1

    execute_db(
        """INSERT INTO appointments (appointment_number, patient_id, doctor_id, department_id, appointment_date,
                                    appointment_time, type, status, token_number, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'Booked', ?, ?)""",
        (apt_num, patient_id, doctor_id, department_id, apt_date, apt_time, apt_type, next_token, reason)
    )

    log_audit(session.get("user_id"), "Book Appointment", "Appointments", f"Booked appointment {apt_num} (Token #{next_token}) for patient ID {patient_id}", request.remote_addr)
    flash(f"Appointment {apt_num} booked successfully! Assigned Token #{next_token}.", "success")
    return redirect(request.referrer or url_for("appointments_list"))

@app.route("/appointments/<int:apt_id>/status", methods=["POST"])
@login_required
def appointment_update_status(apt_id):
    new_status = request.form.get("status")
    if new_status in ["Booked", "Checked-in", "In Consultation", "Completed", "Cancelled", "No-Show"]:
        execute_db("UPDATE appointments SET status = ? WHERE id = ?", (new_status, apt_id))
        flash(f"Appointment status updated to '{new_status}'.", "info")
    return redirect(request.referrer or url_for("appointments_list"))

@app.route("/appointments/queue")
@login_required
def opd_queue_screen():
    """Live token display board for OPD waiting rooms / TV monitors."""
    today_str = date.today().strftime("%Y-%m-%d")
    queue = query_db(
        """SELECT a.*, p.first_name, p.last_name, p.patient_uid, u.full_name as doctor_name, d.name as department_name
           FROM appointments a
           JOIN patients p ON a.patient_id = p.id
           JOIN users u ON a.doctor_id = u.id
           LEFT JOIN departments d ON a.department_id = d.id
           WHERE a.appointment_date = ? AND a.status IN ('Checked-in', 'In Consultation', 'Booked')
           ORDER BY CASE a.status 
                        WHEN 'In Consultation' THEN 1 
                        WHEN 'Checked-in' THEN 2 
                        ELSE 3 
                    END, a.token_number ASC""",
        (today_str,)
    )
    return render_template("appointments/queue.html", queue=queue, today_date=today_str)


# -----------------------------------------------------------------------------
# 5. DOCTOR CLINICAL ROOM & CONSULTATIONS
# -----------------------------------------------------------------------------

@app.route("/consultations/new", methods=["GET", "POST"])
@login_required
@roles_accepted("admin", "doctor")
def consultation_create():
    apt_id = request.args.get("appointment_id")
    patient_id = request.args.get("patient_id")

    appointment = None
    if apt_id:
        appointment = query_db(
            """SELECT a.*, p.first_name, p.last_name, p.patient_uid, p.dob, p.gender, p.blood_group, p.allergies, p.chronic_conditions
               FROM appointments a
               JOIN patients p ON a.patient_id = p.id
               WHERE a.id = ?""",
            (apt_id,),
            one=True
        )
        if appointment:
            patient_id = appointment["patient_id"]

    patient = None
    if patient_id:
        patient = query_db("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)

    if not patient:
        flash("Please select a valid patient to start a clinical consultation.", "warning")
        return redirect(url_for("patients_list"))

    # Latest vitals for reference
    latest_vitals = query_db("SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT 1", (patient_id,), one=True)
    past_consultations = query_db(
        """SELECT c.*, u.full_name as doctor_name 
           FROM consultations c 
           JOIN users u ON c.doctor_id = u.id 
           WHERE c.patient_id = ? 
           ORDER BY c.created_at DESC LIMIT 3""",
        (patient_id,)
    )

    # Catalogs for prescription and lab order dropdowns
    medicines = query_db("SELECT * FROM medicines WHERE stock_quantity > 0 ORDER BY brand_name")
    lab_tests = query_db("SELECT * FROM lab_tests_catalog ORDER BY category, name")

    if request.method == "POST":
        doctor_id = session.get("user_id")
        symptoms = request.form.get("symptoms", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        icd_code = request.form.get("icd_code", "").strip()
        examination_notes = request.form.get("examination_notes", "").strip()
        treatment_plan = request.form.get("treatment_plan", "").strip()
        follow_up_date = request.form.get("follow_up_date") or None

        # 1. Insert Consultation
        consult_id = execute_db(
            """INSERT INTO consultations (appointment_id, patient_id, doctor_id, symptoms, diagnosis, icd_code,
                                         examination_notes, treatment_plan, follow_up_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (apt_id, patient_id, doctor_id, symptoms, diagnosis, icd_code, examination_notes, treatment_plan, follow_up_date)
        )

        # Update appointment status if linked
        if apt_id:
            execute_db("UPDATE appointments SET status = 'Completed' WHERE id = ?", (apt_id,))

        # 2. Process Prescribed Medicines
        med_ids = request.form.getlist("med_id[]")
        dosages = request.form.getlist("dosage[]")
        frequencies = request.form.getlist("frequency[]")
        durations = request.form.getlist("duration_days[]")
        instructions = request.form.getlist("instructions[]")
        quantities = request.form.getlist("quantity_prescribed[]")
        special_instructions = request.form.get("special_instructions", "").strip()

        if med_ids and any(med_ids):
            count_rx = query_db("SELECT COUNT(*) as c FROM prescriptions", one=True)["c"]
            rx_num = f"RX-{date.today().year}-{(count_rx + 1):04d}"
            
            rx_id = execute_db(
                """INSERT INTO prescriptions (prescription_number, consultation_id, patient_id, doctor_id, status, special_instructions)
                   VALUES (?, ?, ?, ?, 'Pending', ?)""",
                (rx_num, consult_id, patient_id, doctor_id, special_instructions)
            )

            for i in range(len(med_ids)):
                if med_ids[i]:
                    try:
                        dur = int(durations[i]) if durations[i] else 5
                        qty = int(quantities[i]) if quantities[i] else (dur * 2)
                        execute_db(
                            """INSERT INTO prescription_items (prescription_id, medicine_id, dosage, frequency, duration_days, instructions, quantity_prescribed)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (rx_id, med_ids[i], dosages[i], frequencies[i], dur, instructions[i], qty)
                        )
                    except Exception as e:
                        print(f"Error adding rx item: {e}")

        # 3. Process Lab Diagnostic Orders
        ordered_tests = request.form.getlist("lab_test_ids[]")
        lab_clinical_notes = request.form.get("lab_clinical_notes", "").strip()

        if ordered_tests and any(ordered_tests):
            count_lab = query_db("SELECT COUNT(*) as c FROM lab_orders", one=True)["c"]
            lab_ord_num = f"LAB-ORD-{date.today().year}-{(count_lab + 1):04d}"

            lab_ord_id = execute_db(
                """INSERT INTO lab_orders (order_number, patient_id, doctor_id, consultation_id, status, clinical_notes)
                   VALUES (?, ?, ?, ?, 'Ordered', ?)""",
                (lab_ord_num, patient_id, doctor_id, consult_id, lab_clinical_notes)
            )

            for test_id in ordered_tests:
                if test_id:
                    execute_db(
                        "INSERT INTO lab_order_items (lab_order_id, test_id, status) VALUES (?, ?, 'Pending')",
                        (lab_ord_id, test_id)
                    )

        log_audit(doctor_id, "Save Consultation", "Consultations", f"Recorded clinical consultation for {patient['first_name']} {patient['last_name']} (Diag: {diagnosis})", request.remote_addr)
        flash(f"Clinical consultation saved successfully for {patient['first_name']} {patient['last_name']}!", "success")
        return redirect(url_for("patient_view", patient_id=patient_id))

    return render_template(
        "consultations/form.html",
        appointment=appointment,
        patient=patient,
        latest_vitals=latest_vitals,
        past_consultations=past_consultations,
        medicines=medicines,
        lab_tests=lab_tests
    )


# -----------------------------------------------------------------------------
# 6. WARDS & VISUAL BED OCCUPANCY MATRIX
# -----------------------------------------------------------------------------

@app.route("/wards")
@login_required
def wards_index():
    wards = query_db("SELECT * FROM wards ORDER BY floor, name")
    
    # Enrich each ward with its beds and occupancy
    for ward in wards:
        ward["beds"] = query_db(
            """SELECT b.*, adm.id as admission_id, adm.admission_number, adm.admitted_at, adm.admission_reason,
                      p.id as patient_id, p.patient_uid, p.first_name, p.last_name, p.gender, p.dob, p.blood_group,
                      u.full_name as doctor_name
               FROM beds b
               LEFT JOIN admissions adm ON b.current_admission_id = adm.id
               LEFT JOIN patients p ON adm.patient_id = p.id
               LEFT JOIN users u ON adm.doctor_id = u.id
               WHERE b.ward_id = ?
               ORDER BY b.bed_number""",
            (ward["id"],)
        )
        ward["occupied_count"] = sum(1 for b in ward["beds"] if b["status"] == "Occupied")
        ward["available_count"] = sum(1 for b in ward["beds"] if b["status"] == "Available")
        ward["maintenance_count"] = sum(1 for b in ward["beds"] if b["status"] == "Maintenance")

    patients = query_db("SELECT id, patient_uid, first_name, last_name, status FROM patients WHERE status != 'Inpatient' ORDER BY first_name")
    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")
    available_beds = query_db(
        """SELECT b.id, b.bed_number, w.name as ward_name 
           FROM beds b JOIN wards w ON b.ward_id = w.id 
           WHERE b.status = 'Available' ORDER BY w.name, b.bed_number"""
    )

    return render_template(
        "wards/index.html",
        wards=wards,
        patients=patients,
        doctors=doctors,
        available_beds=available_beds
    )

@app.route("/wards/admit", methods=["POST"])
@login_required
@roles_accepted("admin", "doctor", "nurse", "receptionist")
def ward_admit_patient():
    patient_id = request.form.get("patient_id")
    bed_id = request.form.get("bed_id")
    doctor_id = request.form.get("doctor_id")
    reason = request.form.get("admission_reason", "").strip()

    # Check bed availability
    bed = query_db("SELECT * FROM beds WHERE id = ?", (bed_id,), one=True)
    if not bed or bed["status"] != "Available":
        flash("Error: Selected bed is no longer available.", "danger")
        return redirect(url_for("wards_index"))

    # Generate admission number
    count_adm = query_db("SELECT COUNT(*) as c FROM admissions", one=True)["c"]
    adm_num = f"ADM-{date.today().year}-{(count_adm + 1):04d}"

    adm_id = execute_db(
        """INSERT INTO admissions (admission_number, patient_id, bed_id, doctor_id, admission_reason, status)
           VALUES (?, ?, ?, ?, ?, 'Admitted')""",
        (adm_num, patient_id, bed_id, doctor_id, reason)
    )

    # Update bed status
    execute_db("UPDATE beds SET status = 'Occupied', current_admission_id = ? WHERE id = ?", (adm_id, bed_id))
    # Update patient status
    execute_db("UPDATE patients SET status = 'Inpatient' WHERE id = ?", (patient_id,))

    log_audit(session.get("user_id"), "Admit Patient", "Wards", f"Admitted patient ID {patient_id} into bed ID {bed_id} ({adm_num})", request.remote_addr)
    flash(f"Patient successfully admitted under {adm_num} to Bed #{bed['bed_number']}!", "success")
    return redirect(url_for("wards_index"))

@app.route("/wards/discharge/<int:admission_id>", methods=["POST"])
@login_required
@roles_accepted("admin", "doctor", "nurse")
def ward_discharge_patient(admission_id):
    discharge_summary = request.form.get("discharge_summary", "").strip()
    discharge_condition = request.form.get("discharge_condition", "Stable / Improved").strip()

    adm = query_db("SELECT * FROM admissions WHERE id = ?", (admission_id,), one=True)
    if not adm:
        flash("Admission record not found.", "danger")
        return redirect(url_for("wards_index"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Mark admission discharged
    execute_db(
        """UPDATE admissions SET discharged_at = ?, discharge_summary = ?, discharge_condition = ?, status = 'Discharged'
           WHERE id = ?""",
        (now_str, discharge_summary, discharge_condition, admission_id)
    )

    # Free the bed
    execute_db("UPDATE beds SET status = 'Available', current_admission_id = NULL WHERE id = ?", (adm["bed_id"],))
    # Update patient status
    execute_db("UPDATE patients SET status = 'Discharged' WHERE id = ?", (adm["patient_id"],))

    log_audit(session.get("user_id"), "Discharge Patient", "Wards", f"Discharged admission {adm['admission_number']}", request.remote_addr)
    flash(f"Patient successfully discharged! Bed has been marked Available.", "success")
    return redirect(url_for("wards_index"))

@app.route("/wards/bed/<int:bed_id>/maintenance", methods=["POST"])
@login_required
@roles_accepted("admin", "nurse")
def toggle_bed_maintenance(bed_id):
    bed = query_db("SELECT * FROM beds WHERE id = ?", (bed_id,), one=True)
    if bed:
        if bed["status"] == "Available":
            execute_db("UPDATE beds SET status = 'Maintenance' WHERE id = ?", (bed_id,))
            flash(f"Bed {bed['bed_number']} marked Under Maintenance / Cleaning.", "warning")
        elif bed["status"] == "Maintenance":
            execute_db("UPDATE beds SET status = 'Available' WHERE id = ?", (bed_id,))
            flash(f"Bed {bed['bed_number']} is now Available.", "success")
    return redirect(url_for("wards_index"))


# -----------------------------------------------------------------------------
# 7. PHARMACY & DRUG INVENTORY
# -----------------------------------------------------------------------------

@app.route("/pharmacy")
@login_required
def pharmacy_catalog():
    query_param = request.args.get("q", "").strip()
    category_param = request.args.get("category", "").strip()
    stock_status = request.args.get("stock_status", "").strip()

    sql = "SELECT * FROM medicines WHERE 1=1"
    params = []

    if query_param:
        sql += " AND (brand_name LIKE ? OR generic_name LIKE ? OR code LIKE ? OR manufacturer LIKE ?)"
        pat = f"%{query_param}%"
        params.extend([pat, pat, pat, pat])

    if category_param:
        sql += " AND category = ?"
        params.append(category_param)

    if stock_status == "low":
        sql += " AND stock_quantity <= reorder_level"
    elif stock_status == "out":
        sql += " AND stock_quantity = 0"

    sql += " ORDER BY brand_name ASC"
    medicines = query_db(sql, params)
    categories = query_db("SELECT DISTINCT category FROM medicines ORDER BY category")

    # Prescriptions pending dispensing
    pending_prescriptions = query_db(
        """SELECT pr.*, p.first_name, p.last_name, p.patient_uid, u.full_name as doctor_name,
                  (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = pr.id) as total_items,
                  (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = pr.id AND is_dispensed = 1) as dispensed_items
           FROM prescriptions pr
           JOIN patients p ON pr.patient_id = p.id
           JOIN users u ON pr.doctor_id = u.id
           WHERE pr.status IN ('Pending', 'Partially Dispensed')
           ORDER BY pr.created_at DESC"""
    )
    for rx in pending_prescriptions:
        rx_items = query_db(
            """SELECT pi.*, m.brand_name, m.generic_name, m.unit_price, m.stock_quantity 
               FROM prescription_items pi
               JOIN medicines m ON pi.medicine_id = m.id
               WHERE pi.prescription_id = ?""",
            (rx["id"],)
        )
        rx["rx_items"] = rx_items
        rx["items"] = rx_items

    return render_template(
        "pharmacy/index.html",
        medicines=medicines,
        categories=categories,
        pending_prescriptions=pending_prescriptions,
        query=query_param,
        category_filter=category_param,
        stock_status=stock_status
    )

@app.route("/pharmacy/new", methods=["POST"])
@login_required
@roles_accepted("admin", "pharmacist")
def medicine_create():
    brand_name = request.form.get("brand_name", "").strip()
    generic_name = request.form.get("generic_name", "").strip()
    category = request.form.get("category", "").strip()
    form = request.form.get("form", "Tablet").strip()
    strength = request.form.get("strength", "").strip()
    unit_price = float(request.form.get("unit_price", 0.0))
    stock_quantity = int(request.form.get("stock_quantity", 0))
    reorder_level = int(request.form.get("reorder_level", 20))
    batch_number = request.form.get("batch_number", "").strip()
    expiry_date = request.form.get("expiry_date") or None
    manufacturer = request.form.get("manufacturer", "").strip()
    location_rack = request.form.get("location_rack", "").strip()

    count_med = query_db("SELECT COUNT(*) as c FROM medicines", one=True)["c"]
    code = f"MED-{(count_med + 1):03d}"

    execute_db(
        """INSERT INTO medicines (code, brand_name, generic_name, category, form, strength, unit_price,
                                 stock_quantity, reorder_level, batch_number, expiry_date, manufacturer, location_rack)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, brand_name, generic_name, category, form, strength, unit_price,
         stock_quantity, reorder_level, batch_number, expiry_date, manufacturer, location_rack)
    )

    log_audit(session.get("user_id"), "Add Medicine", "Pharmacy", f"Added medicine {brand_name} ({code})", request.remote_addr)
    flash(f"Medicine {brand_name} ({code}) added to inventory successfully!", "success")
    return redirect(url_for("pharmacy_catalog"))

@app.route("/pharmacy/dispense/<int:rx_id>", methods=["POST"])
@login_required
@roles_accepted("admin", "pharmacist")
def prescription_dispense(rx_id):
    rx = query_db("SELECT * FROM prescriptions WHERE id = ?", (rx_id,), one=True)
    if not rx:
        flash("Prescription not found.", "danger")
        return redirect(url_for("pharmacy_catalog"))

    items = query_db("SELECT * FROM prescription_items WHERE prescription_id = ?", (rx_id,))
    total_amount = 0.0

    for item in items:
        qty_to_dispense = int(request.form.get(f"dispense_qty_{item['id']}", item["quantity_prescribed"]))
        med = query_db("SELECT * FROM medicines WHERE id = ?", (item["medicine_id"],), one=True)
        if med:
            actual_dispense = min(qty_to_dispense, med["stock_quantity"])
            execute_db("UPDATE medicines SET stock_quantity = stock_quantity - ? WHERE id = ?", (actual_dispense, item["medicine_id"]))
            execute_db(
                "UPDATE prescription_items SET quantity_dispensed = ?, is_dispensed = 1 WHERE id = ?",
                (actual_dispense, item["id"])
            )
            total_amount += (actual_dispense * med["unit_price"])

    # Mark prescription as Dispensed
    execute_db("UPDATE prescriptions SET status = 'Dispensed' WHERE id = ?", (rx_id,))
    # Log dispense
    execute_db(
        """INSERT INTO pharmacy_dispenses (prescription_id, patient_id, pharmacist_id, total_amount, notes)
           VALUES (?, ?, ?, ?, 'Prescription fulfilled at central pharmacy counter')""",
        (rx_id, rx["patient_id"], session.get("user_id"), total_amount)
    )

    log_audit(session.get("user_id"), "Dispense Rx", "Pharmacy", f"Fulfilled prescription {rx['prescription_number']} (Total: ${total_amount:.2f})", request.remote_addr)
    flash(f"Prescription {rx['prescription_number']} dispensed successfully! Stock adjusted.", "success")
    return redirect(url_for("pharmacy_catalog"))


# -----------------------------------------------------------------------------
# 8. LABORATORY & DIAGNOSTICS
# -----------------------------------------------------------------------------

@app.route("/laboratory")
@login_required
def laboratory_index():
    status_filter = request.args.get("status", "").strip()

    sql = """
        SELECT lo.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob,
               u.full_name as doctor_name
        FROM lab_orders lo
        JOIN patients p ON lo.patient_id = p.id
        JOIN users u ON lo.doctor_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        sql += " AND lo.status = ?"
        params.append(status_filter)

    sql += " ORDER BY lo.ordered_at DESC"
    orders = query_db(sql, params)

    for o in orders:
        test_items = query_db(
            """SELECT loi.*, ltc.code as test_code, ltc.name as test_name, ltc.category as test_category,
                      ltc.cost, ltc.specimen_type, ltc.parameters_json
               FROM lab_order_items loi
               JOIN lab_tests_catalog ltc ON loi.test_id = ltc.id
               WHERE loi.lab_order_id = ?""",
            (o["id"],)
        )
        o["test_items"] = test_items
        o["items"] = test_items

    test_catalog = query_db("SELECT * FROM lab_tests_catalog ORDER BY category, name")
    patients = query_db("SELECT id, patient_uid, first_name, last_name FROM patients ORDER BY first_name")
    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")

    return render_template(
        "laboratory/index.html",
        orders=orders,
        status_filter=status_filter,
        test_catalog=test_catalog,
        patients=patients,
        doctors=doctors
    )

@app.route("/laboratory/order/new", methods=["POST"])
@login_required
@roles_accepted("admin", "doctor", "lab_tech")
def lab_order_create():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    notes = request.form.get("clinical_notes", "").strip()
    test_ids = request.form.getlist("test_ids[]")

    if not test_ids:
        flash("Please select at least one lab test to order.", "warning")
        return redirect(url_for("laboratory_index"))

    count_lab = query_db("SELECT COUNT(*) as c FROM lab_orders", one=True)["c"]
    order_num = f"LAB-ORD-{date.today().year}-{(count_lab + 1):04d}"

    order_id = execute_db(
        """INSERT INTO lab_orders (order_number, patient_id, doctor_id, status, clinical_notes)
           VALUES (?, ?, ?, 'Ordered', ?)""",
        (order_num, patient_id, doctor_id, notes)
    )

    for tid in test_ids:
        execute_db("INSERT INTO lab_order_items (lab_order_id, test_id, status) VALUES (?, ?, 'Pending')", (order_id, tid))

    log_audit(session.get("user_id"), "Order Lab Tests", "Laboratory", f"Created lab order {order_num} with {len(test_ids)} tests", request.remote_addr)
    flash(f"Lab Order {order_num} created successfully!", "success")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/order/<int:order_id>/collect", methods=["POST"])
@login_required
@roles_accepted("admin", "lab_tech", "nurse")
def lab_collect_sample(order_id):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_db(
        "UPDATE lab_orders SET status = 'Sample Collected', sample_collected_at = ? WHERE id = ?",
        (now_str, order_id)
    )
    execute_db("UPDATE lab_order_items SET status = 'In Progress' WHERE lab_order_id = ?", (order_id,))
    flash("Sample collected status recorded. Tests are now In Progress.", "info")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/item/<int:item_id>/result", methods=["POST"])
@login_required
@roles_accepted("admin", "lab_tech")
def lab_save_result(item_id):
    interpretation = request.form.get("interpretation", "").strip()
    param_names = request.form.getlist("param_name[]")
    param_values = request.form.getlist("param_value[]")
    param_units = request.form.getlist("param_unit[]")
    param_ranges = request.form.getlist("param_range[]")
    param_abnormals = request.form.getlist("param_abnormal[]")

    results = []
    for i in range(len(param_names)):
        is_abn = (str(i) in param_abnormals) or (param_names[i] in param_abnormals)
        results.append({
            "name": param_names[i],
            "value": param_values[i] if i < len(param_values) else "",
            "unit": param_units[i] if i < len(param_units) else "",
            "ref_range": param_ranges[i] if i < len(param_ranges) else "",
            "is_abnormal": is_abn
        })

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_db(
        """UPDATE lab_order_items SET status = 'Completed', results_json = ?, interpretation = ?,
                                    technician_id = ?, verified_by_id = ?, performed_at = ?
           WHERE id = ?""",
        (json.dumps(results), interpretation, session.get("user_id"), session.get("user_id"), now_str, item_id)
    )

    # Check if all items in order are completed
    item = query_db("SELECT lab_order_id FROM lab_order_items WHERE id = ?", (item_id,), one=True)
    if item:
        order_id = item["lab_order_id"]
        pending_items = query_db("SELECT COUNT(*) as c FROM lab_order_items WHERE lab_order_id = ? AND status != 'Completed'", (order_id,), one=True)["c"]
        if pending_items == 0:
            execute_db("UPDATE lab_orders SET status = 'Completed', completed_at = ? WHERE id = ?", (now_str, order_id))

    flash("Lab test results recorded and verified successfully!", "success")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/report/<int:order_id>")
@login_required
def lab_report_view(order_id):
    """Print-ready clinical laboratory diagnostic report."""
    order = query_db(
        """SELECT lo.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.phone as patient_phone,
                  u.full_name as doctor_name, u.specialization as doctor_spec
           FROM lab_orders lo
           JOIN patients p ON lo.patient_id = p.id
           JOIN users u ON lo.doctor_id = u.id
           WHERE lo.id = ?""",
        (order_id,),
        one=True
    )
    if not order:
        abort(404, description="Lab order report not found.")

    items = query_db(
        """SELECT loi.*, ltc.code as test_code, ltc.name as test_name, ltc.category as test_category,
                  ltc.specimen_type, tech.full_name as tech_name, ver.full_name as verifier_name
           FROM lab_order_items loi
           JOIN lab_tests_catalog ltc ON loi.test_id = ltc.id
           LEFT JOIN users tech ON loi.technician_id = tech.id
           LEFT JOIN users ver ON loi.verified_by_id = ver.id
           WHERE loi.lab_order_id = ?""",
        (order_id,)
    )

    return render_template("laboratory/report.html", order=order, items=items)


# -----------------------------------------------------------------------------
# 9. BILLING & INVOICING
# -----------------------------------------------------------------------------

@app.route("/billing")
@login_required
def billing_index():
    status_filter = request.args.get("status", "").strip()
    query_param = request.args.get("q", "").strip()

    sql = """
        SELECT inv.*, p.first_name, p.last_name, p.patient_uid, p.phone as patient_phone
        FROM invoices inv
        JOIN patients p ON inv.patient_id = p.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        sql += " AND inv.status = ?"
        params.append(status_filter)

    if query_param:
        sql += " AND (inv.invoice_number LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR p.patient_uid LIKE ?)"
        pat = f"%{query_param}%"
        params.extend([pat, pat, pat, pat])

    sql += " ORDER BY inv.created_at DESC"
    invoices = query_db(sql, params)

    total_billed = query_db("SELECT SUM(total_amount) as s FROM invoices", one=True)["s"] or 0.0
    total_collected = query_db("SELECT SUM(amount_paid) as s FROM invoices", one=True)["s"] or 0.0
    total_outstanding = total_billed - total_collected

    patients = query_db("SELECT id, patient_uid, first_name, last_name FROM patients ORDER BY first_name")

    return render_template(
        "billing/index.html",
        invoices=invoices,
        total_billed=total_billed,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        status_filter=status_filter,
        query=query_param,
        patients=patients
    )

@app.route("/billing/new", methods=["POST"])
@login_required
@roles_accepted("admin", "receptionist")
def billing_create_invoice():
    patient_id = request.form.get("patient_id")
    admission_id = request.form.get("admission_id") or None
    payment_method = request.form.get("payment_method", "Cash")
    tax_percent = float(request.form.get("tax_percent", 5.0))
    discount_amount = float(request.form.get("discount_amount", 0.0))
    amount_paid = float(request.form.get("amount_paid", 0.0))
    due_date = request.form.get("due_date", (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"))
    notes = request.form.get("notes", "").strip()

    item_types = request.form.getlist("item_type[]")
    descriptions = request.form.getlist("description[]")
    quantities = request.form.getlist("quantity[]")
    unit_prices = request.form.getlist("unit_price[]")

    subtotal = 0.0
    for i in range(len(descriptions)):
        if descriptions[i]:
            qty = float(quantities[i]) if quantities[i] else 1.0
            price = float(unit_prices[i]) if unit_prices[i] else 0.0
            subtotal += (qty * price)

    tax_amount = round((subtotal * (tax_percent / 100.0)), 2)
    total_amount = round(max(0.0, subtotal + tax_amount - discount_amount), 2)

    status = "Unpaid"
    if amount_paid >= total_amount and total_amount > 0:
        status = "Paid"
    elif amount_paid > 0:
        status = "Partially Paid"

    count_inv = query_db("SELECT COUNT(*) as c FROM invoices", one=True)["c"]
    inv_num = f"INV-{date.today().year}-{(count_inv + 1):04d}"

    inv_id = execute_db(
        """INSERT INTO invoices (invoice_number, patient_id, admission_id, subtotal, tax_percent, tax_amount,
                                discount_amount, total_amount, amount_paid, status, payment_method, due_date,
                                paid_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (inv_num, patient_id, admission_id, subtotal, tax_percent, tax_amount,
         discount_amount, total_amount, amount_paid, status, payment_method, due_date,
         (datetime.now().strftime("%Y-%m-%d %H:%M:%S") if amount_paid > 0 else None), notes)
    )

    for i in range(len(descriptions)):
        if descriptions[i]:
            qty = float(quantities[i]) if quantities[i] else 1.0
            price = float(unit_prices[i]) if unit_prices[i] else 0.0
            item_tot = qty * price
            execute_db(
                """INSERT INTO invoice_items (invoice_id, item_type, description, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (inv_id, item_types[i] if i < len(item_types) else "Miscellaneous", descriptions[i], qty, price, item_tot)
            )

    log_audit(session.get("user_id"), "Create Invoice", "Billing", f"Created invoice {inv_num} for patient ID {patient_id} (Total: ${total_amount:.2f})", request.remote_addr)
    flash(f"Invoice {inv_num} created successfully!", "success")
    return redirect(url_for("billing_invoice_view", invoice_id=inv_id))

@app.route("/billing/invoice/<int:invoice_id>")
@login_required
def billing_invoice_view(invoice_id):
    invoice = query_db(
        """SELECT inv.*, p.first_name, p.last_name, p.patient_uid, p.phone as patient_phone, p.email as patient_email,
                  p.address as patient_address, p.insurance_provider, p.insurance_policy_number
           FROM invoices inv
           JOIN patients p ON inv.patient_id = p.id
           WHERE inv.id = ?""",
        (invoice_id,),
        one=True
    )
    if not invoice:
        abort(404, description="Invoice not found.")

    items = query_db("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    return render_template("billing/invoice.html", invoice=invoice, items=items)

@app.route("/billing/invoice/<int:invoice_id>/pay", methods=["POST"])
@login_required
@roles_accepted("admin", "receptionist")
def billing_record_payment(invoice_id):
    invoice = query_db("SELECT * FROM invoices WHERE id = ?", (invoice_id,), one=True)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("billing_index"))

    pay_amount = float(request.form.get("pay_amount", 0.0))
    pay_method = request.form.get("payment_method", "Cash")

    new_paid = invoice["amount_paid"] + pay_amount
    new_status = "Paid" if new_paid >= invoice["total_amount"] else "Partially Paid"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db(
        "UPDATE invoices SET amount_paid = ?, status = ?, payment_method = ?, paid_at = ? WHERE id = ?",
        (new_paid, new_status, pay_method, now_str, invoice_id)
    )

    log_audit(session.get("user_id"), "Record Payment", "Billing", f"Received payment of ${pay_amount:.2f} for invoice {invoice['invoice_number']}", request.remote_addr)
    flash(f"Payment of ${pay_amount:.2f} recorded for {invoice['invoice_number']}!", "success")
    return redirect(url_for("billing_invoice_view", invoice_id=invoice_id))


# -----------------------------------------------------------------------------
# 10. STAFF DIRECTORY & DEPARTMENTS
# -----------------------------------------------------------------------------

@app.route("/staff")
@login_required
def staff_index():
    role_filter = request.args.get("role", "").strip()
    dept_filter = request.args.get("department_id", "").strip()

    sql = """
        SELECT u.*, d.name as department_name, d.color as dept_color
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        WHERE u.is_active = 1
    """
    params = []

    if role_filter:
        sql += " AND u.role = ?"
        params.append(role_filter)

    if dept_filter:
        sql += " AND u.department_id = ?"
        params.append(dept_filter)

    sql += " ORDER BY u.role, u.full_name"
    staff = query_db(sql, params)
    departments = query_db("SELECT * FROM departments ORDER BY name")

    return render_template("staff/index.html", staff=staff, departments=departments, role_filter=role_filter, dept_filter=dept_filter)

@app.route("/staff/new", methods=["POST"])
@login_required
@roles_accepted("admin")
def staff_create():
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "password123").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    role = request.form.get("role", "doctor").strip()
    department_id = request.form.get("department_id") or None
    specialization = request.form.get("specialization", "").strip()
    qualification = request.form.get("qualification", "").strip()
    license_number = request.form.get("license_number", "").strip()
    consultation_fee = float(request.form.get("consultation_fee", 0.0))

    pw_hash = generate_password_hash(password)

    execute_db(
        """INSERT INTO users (username, password_hash, full_name, email, phone, role, department_id,
                             specialization, qualification, license_number, consultation_fee, avatar_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=150')""",
        (username, pw_hash, full_name, email, phone, role, department_id, specialization, qualification, license_number, consultation_fee)
    )

    log_audit(session.get("user_id"), "Add Staff", "Staff", f"Added staff member {full_name} ({role})", request.remote_addr)
    flash(f"Staff member {full_name} ({role.upper()}) added successfully!", "success")
    return redirect(url_for("staff_index"))


# -----------------------------------------------------------------------------
# 11. SETTINGS & AUDIT LOGS
# -----------------------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@login_required
@roles_accepted("admin")
def settings_index():
    if request.method == "POST":
        for key in ["hospital_name", "tagline", "address", "phone", "emergency_hotline", "email", "currency", "tax_rate", "registration_number"]:
            if key in request.form:
                set_setting(key, request.form.get(key, "").strip())

        log_audit(session.get("user_id"), "Update Settings", "Settings", "Updated hospital system settings", request.remote_addr)
        flash("Hospital configuration saved successfully!", "success")
        return redirect(url_for("settings_index"))

    settings = {row["key"]: row["value"] for row in query_db("SELECT * FROM hospital_settings")}
    return render_template("settings/index.html", settings=settings)

@app.route("/audit-logs")
@login_required
@roles_accepted("admin")
def audit_logs_index():
    logs = query_db(
        """SELECT a.*, u.full_name as user_name, u.role as user_role 
           FROM audit_logs a 
           LEFT JOIN users u ON a.user_id = u.id 
           ORDER BY a.timestamp DESC LIMIT 100"""
    )
    return render_template("settings/audit_logs.html", logs=logs)


# -----------------------------------------------------------------------------
# REST API HELPER ENDPOINTS (For dynamic modals and autocomplete)
# -----------------------------------------------------------------------------

@app.route("/api/patients/search")
@login_required
def api_patient_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    pat = f"%{q}%"
    rows = query_db(
        """SELECT id, patient_uid, first_name, last_name, phone, dob, gender 
           FROM patients 
           WHERE patient_uid LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? 
           LIMIT 10""",
        (pat, pat, pat, pat)
    )
    return jsonify(rows)

@app.route("/api/medicines/search")
@login_required
def api_medicine_search():
    q = request.args.get("q", "").strip()
    pat = f"%{q}%"
    rows = query_db(
        """SELECT id, code, brand_name, generic_name, form, strength, unit_price, stock_quantity 
           FROM medicines 
           WHERE (brand_name LIKE ? OR generic_name LIKE ? OR code LIKE ?) AND stock_quantity > 0 
           LIMIT 10""",
        (pat, pat, pat)
    )
    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
