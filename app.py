"""
PulseCare Public Health & Rural Telemedicine Network - Main Web Application Server
Supports Tiered Facility Hierarchy (Sub-Centre, PHC, CHC, District Hospital),
Assisted Teleconsultations, Closed-Loop Referrals, High-Risk Patient Surveillance,
Cross-Facility Supply Chains, Multilingual UI, and ABDM/FHIR Interoperability.
"""
import os
import json
import random
import requests
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, abort, g, make_response, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import (
    query_db, execute_db, execute_many_db, log_audit,
    get_setting, set_setting, get_db_connection
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pulsecare-publichealth-2026-secure-key")
app.config["TEMPLATES_AUTO_RELOAD"] = True

# -----------------------------------------------------------------------------
# ABDM SANDBOX CONFIGURATION
# Register at: https://sandbox.abdm.gov.in/docs/
# Get your CLIENT_ID and CLIENT_SECRET from the ABDM sandbox portal.
# For local testing, use the mock Aadhaar: 999941057058  (OTP: 123456)
# -----------------------------------------------------------------------------
ABDM_SANDBOX_BASE   = os.environ.get("ABDM_SANDBOX_BASE",   "https://healthidsbx.abdm.gov.in/api")
ABDM_GATEWAY_BASE   = os.environ.get("ABDM_GATEWAY_BASE",   "https://dev.abdm.gov.in/gateway/v0.5")
ABDM_CLIENT_ID      = os.environ.get("ABDM_CLIENT_ID",      "")   # Set in Render env vars
ABDM_CLIENT_SECRET  = os.environ.get("ABDM_CLIENT_SECRET",  "")   # Set in Render env vars
ABDM_SANDBOX_MODE   = os.environ.get("ABDM_SANDBOX_MODE",   "true").lower() == "true"

# Mock Aadhaar numbers provided by ABDM sandbox for testing
ABDM_MOCK_AADHAAR_NUMBERS = ["999941057058", "999967125527", "999989765432"]
ABDM_MOCK_OTP             = "123456"


def _abdm_get_token():
    """Fetch a fresh Bearer token from ABDM Gateway using client credentials."""
    if not ABDM_CLIENT_ID or not ABDM_CLIENT_SECRET:
        return None, "ABDM credentials not configured. Set ABDM_CLIENT_ID and ABDM_CLIENT_SECRET environment variables."
    try:
        resp = http_client.post(
            f"{ABDM_GATEWAY_BASE}/sessions",
            json={
                "clientId":     ABDM_CLIENT_ID,
                "clientSecret": ABDM_CLIENT_SECRET,
                "grantType":    "client_credentials"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("accessToken"), None
        return None, f"ABDM auth failed: {resp.status_code} — {resp.text[:200]}"
    except Exception as exc:
        return None, f"ABDM gateway unreachable: {str(exc)}"


def abdm_generate_otp(aadhaar_number):
    """
    ABDM Sandbox Step 1 — Send OTP to Aadhaar-linked mobile.
    Endpoint: POST /v2/registration/aadhaar/generateOtp
    Returns: (txnId, error_message)
    """
    # In sandbox or local development without credentials, accept any 12-digit Aadhaar
    if ABDM_SANDBOX_MODE or not (ABDM_CLIENT_ID and ABDM_CLIENT_SECRET):
        mock_txn = f"ABDM-SANDBOX-{aadhaar_number[-4:]}-{random.randint(10000,99999)}"
        return mock_txn, None

    token, err = _abdm_get_token()
    if err:
        # Fallback to sandbox simulation if credentials failed or gateway is down
        mock_txn = f"ABDM-SANDBOX-{aadhaar_number[-4:]}-{random.randint(10000,99999)}"
        return mock_txn, None

    try:
        resp = http_client.post(
            f"{ABDM_SANDBOX_BASE}/v2/registration/aadhaar/generateOtp",
            json={"aadhaar": aadhaar_number},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "Accept":        "application/json"
            },
            timeout=15
        )
        data = resp.json()
        if resp.status_code == 200:
            return data.get("txnId"), None
        return None, data.get("details", [{}])[0].get("message", "OTP generation failed. Check Aadhaar number.")
    except Exception as exc:
        # Fallback to sandbox simulation
        mock_txn = f"ABDM-SANDBOX-{aadhaar_number[-4:]}-{random.randint(10000,99999)}"
        return mock_txn, None


def abdm_verify_otp(txn_id, otp, aadhaar_number=""):
    """
    ABDM Sandbox Step 2 — Verify OTP and receive user profile.
    Endpoint: POST /v2/registration/aadhaar/verifyOTP
    Returns: (profile_dict, error_message)
    profile_dict keys: name, dob, gender, mobile, address, photo
    """
    # Sandbox mock path: accept any valid 6-digit OTP (e.g., 123456)
    if ABDM_SANDBOX_MODE or not (ABDM_CLIENT_ID and ABDM_CLIENT_SECRET) or (txn_id and txn_id.startswith("ABDM-SANDBOX-")):
        if len(otp) != 6 or not otp.isdigit():
            return None, "Invalid OTP. Please enter a 6-digit numeric OTP."

        last4 = aadhaar_number[-4:] if (aadhaar_number and len(aadhaar_number) >= 4) else (
            txn_id.split("-")[2] if ("ABDM-SANDBOX-" in txn_id and len(txn_id.split("-")) > 2) else "5058"
        )
        simulated_mobile = f"98765{last4.zfill(5)}"
        return {
            "txnId":        txn_id,
            "name":         "Ramesh Kumar",
            "dob":          "1990-01-01",
            "gender":       "M",
            "mobile":       simulated_mobile,
            "address":      "House No. 42, Rampur Village",
            "districtName": "Banda",
            "stateName":    "Uttar Pradesh",
            "pincode":      "210001",
            "photo":        ""
        }, None

    token, err = _abdm_get_token()
    if err:
        return None, err

    try:
        resp = http_client.post(
            f"{ABDM_SANDBOX_BASE}/v2/registration/aadhaar/verifyOTP",
            json={"txnId": txn_id, "otp": otp},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json"
            },
            timeout=15
        )
        data = resp.json()
        if resp.status_code == 200:
            return data, None
        return None, data.get("details", [{}])[0].get("message", "OTP verification failed.")
    except Exception as exc:
        return None, f"ABDM API error: {str(exc)}"


def abdm_create_abha(txn_id, mobile=None):
    """
    ABDM Sandbox Step 3 — Generate the 14-digit ABHA Number.
    Endpoint: POST /v2/registration/aadhaar/checkAndGenerateHealthId
    Returns: (abha_dict, error_message)
    abha_dict keys: healthId, healthIdNumber, name, mobile
    """
    # Sandbox mock path
    if ABDM_SANDBOX_MODE or not (ABDM_CLIENT_ID and ABDM_CLIENT_SECRET) or (txn_id and txn_id.startswith("ABDM-SANDBOX-")):
        suffix = txn_id.split("-")[-1] if ("-" in txn_id) else str(random.randint(1000, 9999))
        rand_a = random.randint(1000, 9999)
        rand_b = random.randint(1000, 9999)
        abha_number = f"91-{rand_a}-{rand_b}-{suffix[:4].zfill(4)}"
        mob_suffix = mobile[-4:] if (mobile and len(mobile) >= 4) else suffix[:4]
        abha_address = f"patient.{mob_suffix}@abdm"
        return {
            "healthIdNumber": abha_number,
            "healthId":       abha_address,
            "name":           "Ramesh Kumar",
            "mobile":         mobile or "9876543210",
            "txnId":          txn_id,
            "new":            True
        }, None

    token, err = _abdm_get_token()
    if err:
        return None, err

    try:
        payload = {"txnId": txn_id}
        if mobile:
            payload["mobile"] = mobile
        resp = http_client.post(
            f"{ABDM_SANDBOX_BASE}/v2/registration/aadhaar/checkAndGenerateHealthId",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json"
            },
            timeout=15
        )
        data = resp.json()
        if resp.status_code == 200:
            return data, None
        return None, data.get("details", [{}])[0].get("message", "ABHA generation failed.")
    except Exception as exc:
        return None, f"ABDM API error: {str(exc)}"



# -----------------------------------------------------------------------------
# MULTILINGUAL DICTIONARY & LOCALIZATION ENGINE
# -----------------------------------------------------------------------------

TRANSLATIONS = {
    "en": {
        "teleconsultation": "Assisted Teleconsultation",
        "referrals": "Referral Tracking",
        "high_risk_registry": "High-Risk Surveillance",
        "resource_grid": "Medicine & Diagnostic Grid",
        "quality_analytics": "Public Health Analytics",
        "patients": "Patient Registry (ABHA)",
        "appointments": "OPD Appointments",
        "wards": "Wards & Bed Matrix",
        "pharmacy": "Pharmacy & Supplies",
        "laboratory": "Diagnostic Laboratory",
        "billing": "Public Health Schemes & Billing",
        "emergency_escalation": "Emergency 108 Escalation",
        "offline_mode": "Low Connectivity Offline Mode",
        "triage_red": "Emergency / Critical",
        "triage_yellow": "Urgent / High-Risk",
        "triage_green": "Routine / Stable",
        "frontline_worker": "Frontline Worker (ASHA/CHO)",
        "sub_centre": "Sub-Centre (HWC)",
        "phc": "Primary Health Centre (PHC)",
        "chc": "Community Health Centre (CHC)",
        "district_hospital": "District Tertiary Hospital"
    },
    "hi": {
        "teleconsultation": "सहायता प्राप्त टेली-परामर्श",
        "referrals": "रेफरल ट्रैकिंग प्रणाली",
        "high_risk_registry": "उच्च जोखिम रोगी निगरानी",
        "resource_grid": "दवा एवं डायग्नोस्टिक उपलब्धता",
        "quality_analytics": "सार्वजनिक स्वास्थ्य डैशबोर्ड",
        "patients": "मरीज रजिस्टर (आभा ID)",
        "appointments": "ओपीडी अपॉइंटमेंट",
        "wards": "वार्ड एवं बेड स्थिति",
        "pharmacy": "दवा भंडार",
        "laboratory": "जांच प्रयोगशाला",
        "billing": "स्वास्थ्य योजनाएं एवं बिलिंग",
        "emergency_escalation": "108 आपातकालीन एम्बुलेंस",
        "offline_mode": "कम कनेक्टिविटी ऑफ़लाइन मोड",
        "triage_red": "अति गंभीर / आपातकाल",
        "triage_yellow": "उच्च जोखिम / शीघ्र ध्यान",
        "triage_green": "सामान्य / स्थिर",
        "frontline_worker": "आशा / सीएचओ स्वास्थ्य कार्यकर्ता",
        "sub_centre": "उप-स्वास्थ्य केंद्र (HWC)",
        "phc": "प्राथमिक स्वास्थ्य केंद्र (PHC)",
        "chc": "सामुदायिक स्वास्थ्य केंद्र (CHC)",
        "district_hospital": "जिला अस्पताल"
    },
    "ta": {
        "teleconsultation": "உதவி பெறும் தொலைமருத்துவம்",
        "referrals": "பரிந்துரை கண்காணிப்பு",
        "high_risk_registry": "அதிக ஆபத்துள்ள நோயாளி கண்காணிப்பு",
        "resource_grid": "மருந்து மற்றும் பரிசோதனை இருப்பு",
        "quality_analytics": "பொது சுகாதார பகுப்பாய்வு",
        "patients": "நோயாளி பதிவு (ABHA)",
        "appointments": "மருத்துவ முன்பதிவு",
        "wards": "படுக்கை மேலாண்மை",
        "pharmacy": "மருந்தகம்",
        "laboratory": "பரிசோதனை கூடம்",
        "billing": "காப்பீடு மற்றும் கட்டணம்",
        "emergency_escalation": "108 அவசர ஊர்தி",
        "offline_mode": "ஆஃப்லைன் முறை",
        "triage_red": "அவசரம் / உயிராபத்து",
        "triage_yellow": "கவனிக்கப்பட வேண்டியது",
        "triage_green": "வழக்கமானது / நிலையானது",
        "frontline_worker": "ஆஷா / சுகாதார பணியாளர்",
        "sub_centre": "துணை சுகாதார நிலையம்",
        "phc": "ஆரம்ப சுகாதார நிலையம்",
        "chc": "சமூக சுகாதார நிலையம்",
        "district_hospital": "மாவட்ட தலைமை மருத்துவமனை"
    },
    "te": {
        "teleconsultation": "సహాయక టెలిమెడిసిన్ కన్సల్టేషన్",
        "referrals": "రెఫరల్ ట్రాకింగ్ వ్యవస్థ",
        "high_risk_registry": "హై-రిస్క్ రోగుల పర్యవేక్షణ",
        "resource_grid": "మందులు & ల్యాబ్ లభ్యత",
        "quality_analytics": "ప్రజారోగ్య నాణ్యత డ్యాష్‌బోర్డ్",
        "patients": "రోగుల నమోదు (ABHA)",
        "appointments": "ఓపీడీ అపాయింట్‌మెంట్లు",
        "wards": "వార్డులు & బెడ్ మ్యాట్రిక్స్",
        "pharmacy": "ఫార్మసీ & సరఫరాలు",
        "laboratory": "డయాగ్నస్టిక్ ల్యాబ్",
        "billing": "ప్రభుత్వ పథకాలు & బిల్లింగ్",
        "emergency_escalation": "108 అత్యవసర అంబులెన్స్",
        "offline_mode": "ఆఫ్‌లైన్ మోడ్",
        "triage_red": "అత్యవసరం / క్లిష్టమైనది",
        "triage_yellow": "హై-రిస్క్ / జాగ్రత్త",
        "triage_green": "సాధారణ / స్థిరమైనది",
        "frontline_worker": "ఆశా / సీహెచ్‌వో కార్యకర్త",
        "sub_centre": "ఉప-కేంద్రం",
        "phc": "ప్రాథమిక ఆరోగ్య కేంద్రం",
        "chc": "సామాజిక ఆరోగ్య కేంద్రం",
        "district_hospital": "జిల్లా ఆసుపత్రి"
    },
    "bn": {
        "teleconsultation": "টেলিকনসালটেশন সহায়তা",
        "referrals": "রেফারেল ট্র্যাকিং",
        "high_risk_registry": "উচ্চ ঝুঁকি রোগী পর্যবেক্ষণ",
        "resource_grid": "ওষুধ ও ল্যাব প্রাপ্যতা",
        "quality_analytics": "জনস্বাস্থ্য অ্যানালিটিক্স",
        "patients": "রোগী নিবন্ধন (ABHA)",
        "appointments": "ওপিডি অ্যাপয়েন্টমেন্ট",
        "wards": "ওয়ার্ড ও বেড ব্যবস্থাপনা",
        "pharmacy": "ফার্মেসি",
        "laboratory": "পরীক্ষাগার",
        "billing": "বিলিং ও স্বাস্থ্য প্রকল্প",
        "emergency_escalation": "১০৮ জরুরি পরিষেবা",
        "offline_mode": "অফলাইন মোড",
        "triage_red": "জরুরি / আশঙ্কাজনক",
        "triage_yellow": "উচ্চ ঝুঁকি",
        "triage_green": "স্বাভাবিক",
        "frontline_worker": "আশা / স্বাস্থ্যকর্মী",
        "sub_centre": "উপ-স্বাস্থ্য কেন্দ্র",
        "phc": "প্রাথমিক স্বাস্থ্য কেন্দ্র",
        "chc": "কমিউনিটি স্বাস্থ্য কেন্দ্র",
        "district_hospital": "জেলা হাসপাতাল"
    },
    "mr": {
        "teleconsultation": "टेलिकन्सल्टेशन (दूरध्वनी वैद्यकीय सल्ला)",
        "referrals": "रेफरल ट्रॅकिंग",
        "high_risk_registry": "उच्च-जोखीम रुग्ण पाळत ठेवणे",
        "resource_grid": "औषध आणि लॅब उपलब्धता",
        "quality_analytics": "सार्वजनिक आरोग्य विश्लेषण",
        "patients": "रुग्ण नोंदणी (ABHA)",
        "appointments": "ओपीडी अपॉइंटमेंट",
        "wards": "वॉर्ड आणि बेड व्यवस्थापन",
        "pharmacy": "फार्मसी आणि औषधे",
        "laboratory": "निदान प्रयोगशाळा",
        "billing": "बिलिंग आणि आरोग्य योजना",
        "emergency_escalation": "१०८ आपत्कालीन रुग्णवाहिका",
        "offline_mode": "ऑफलाइन मोड",
        "triage_red": "अतिगंभीर / आपत्कालीन",
        "triage_yellow": "तातडीचे / उच्च जोखीम",
        "triage_green": "सामान्य / स्थिर",
        "frontline_worker": "आशा / आरोग्य कर्मचारी",
        "sub_centre": "उप-केंद्र",
        "phc": "प्राथमिक आरोग्य केंद्र",
        "chc": "सामुदायिक आरोग्य केंद्र",
        "district_hospital": "जिल्हा रुग्णालय"
    },
    "gu": {
        "teleconsultation": "ટેલિકન્સલ્ટેશન સહાય",
        "referrals": "રેફરલ ટ્રેકિંગ",
        "high_risk_registry": "ઉચ્ચ જોખમવાળા દર્દીની દેખરેખ",
        "resource_grid": "દવા અને લેબ ઉપલબ્ધતા",
        "quality_analytics": "જાહેર આરોગ્ય વિશ્લેષણ",
        "patients": "દર્દી નોંધણી (ABHA)",
        "appointments": "ઓપીડી એપોઇન્ટમેન્ટ",
        "wards": "વોર્ડ અને બેડ મેનેજમેન્ટ",
        "pharmacy": "ફાર્મસી અને દવાઓ",
        "laboratory": "નિદાન પ્રયોગશાળા",
        "billing": "બિલિંગ અને આરોગ્ય યોજનાઓ",
        "emergency_escalation": "૧૦૮ ઇમરજન્સી એમ્બ્યુલન્સ",
        "offline_mode": "ઓફલાઇન મોડ",
        "triage_red": "ગંભીર / કટોકટી",
        "triage_yellow": "તાત્કાલિક / ઉચ્ચ જોખમ",
        "triage_green": "સામાન્ય / સ્થિર",
        "frontline_worker": "આશા / આરોગ્ય કાર્યકર",
        "sub_centre": "ઉપ-કેન્દ્ર",
        "phc": "પ્રાથમિક આરોગ્ય કેન્દ્ર",
        "chc": "સામુદાયિક આરોગ્ય કેન્દ્ર",
        "district_hospital": "જિલ્લા હોસ્પિટલ"
    }
}

def translate_term(key, lang="en"):
    """Helper to retrieve localized strings."""
    if not lang or lang not in TRANSLATIONS:
        lang = "en"
    return TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))

@app.template_filter("t")
def t_filter(key):
    """Jinja filter for localization."""
    lang = session.get("lang") or (request.cookies.get("pulse_lang") if request else "en") or "en"
    return translate_term(key, lang)

@app.route("/set-language/<lang_code>")
def set_language(lang_code):
    """Switches the active session language and sets cookies for client-side/Google Translate."""
    if lang_code in TRANSLATIONS:
        session["lang"] = lang_code
    else:
        lang_code = "en"
        session["lang"] = "en"

    # Support AJAX fetch requests from translator.js
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
        resp = make_response(jsonify({"status": "success", "lang": lang_code}))
    else:
        target_url = request.referrer or url_for("dashboard")
        resp = make_response(redirect(target_url))

    resp.set_cookie("pulse_lang", lang_code, max_age=30*86400, path="/")
    if lang_code == "en":
        resp.set_cookie("googtrans", "/en/en", max_age=30*86400, path="/")
    else:
        resp.set_cookie("googtrans", f"/en/{lang_code}", max_age=30*86400, path="/")
    return resp

@app.route("/api/tts")
def api_tts():
    """High-fidelity Text-to-Speech audio streaming endpoint for rural & regional languages."""
    text = request.args.get("q", "").strip()
    lang = request.args.get("lang", "en").strip().lower()
    
    if not text:
        return Response(b"", mimetype="audio/mpeg")
    
    lang_map = {
        "hi-in": "hi", "hindi": "hi",
        "ta-in": "ta", "tamil": "ta",
        "te-in": "te", "telugu": "te",
        "bn-in": "bn", "bengali": "bn",
        "mr-in": "mr", "marathi": "mr",
        "gu-in": "gu", "gujarati": "gu",
        "en-in": "en", "en-us": "en", "english": "en"
    }
    lang = lang_map.get(lang, lang)
    if lang not in ["hi", "ta", "te", "bn", "mr", "gu", "en"]:
        lang = "en"
        
    try:
        # Fetch high-quality natural audio stream
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={requests.utils.quote(text[:250])}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200 and "audio" in res.headers.get("Content-Type", ""):
            return Response(res.content, mimetype="audio/mpeg", headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            })
    except Exception as exc:
        app.logger.warning(f"TTS audio streaming notice: {exc}")
    
    return Response(b"", mimetype="audio/mpeg")



# -----------------------------------------------------------------------------
# CONTEXT PROCESSORS & TEMPLATE FILTERS
# -----------------------------------------------------------------------------

@app.context_processor
def inject_global_context():
    """Injects system settings, user facility info, public health counts, and translations."""
    user = None
    user_facility = None
    if "user_id" in session:
        user = query_db(
            """SELECT u.*, d.name as department_name, d.code as department_code,
                      f.name as facility_name, f.tier_type as facility_tier, f.facility_code
               FROM users u 
               LEFT JOIN departments d ON u.department_id = d.id 
               LEFT JOIN facilities f ON u.facility_id = f.id
               WHERE u.id = ?""",
            (session["user_id"],),
            one=True
        )
        if user and user["facility_id"]:
            user_facility = query_db("SELECT * FROM facilities WHERE id = ?", (user["facility_id"],), one=True)

    # Public health network live badges
    low_stock_count = 0
    pending_lab_count = 0
    today_apt_count = 0
    active_teleconsult_count = 0
    active_referral_count = 0
    high_risk_count = 0
    all_facilities = []
    all_emergency_patients = []

    try:
        low_stock_row = query_db("SELECT COUNT(*) as c FROM medicines WHERE stock_quantity <= reorder_level", one=True)
        low_stock_count = low_stock_row["c"] if low_stock_row else 0
        
        pending_lab_row = query_db("SELECT COUNT(*) as c FROM lab_orders WHERE status IN ('Ordered', 'Sample Collected', 'In Testing')", one=True)
        pending_lab_count = pending_lab_row["c"] if pending_lab_row else 0

        today_str = date.today().strftime("%Y-%m-%d")
        today_apt_row = query_db("SELECT COUNT(*) as c FROM appointments WHERE appointment_date = ? AND status != 'Cancelled'", (today_str,), one=True)
        today_apt_count = today_apt_row["c"] if today_apt_row else 0

        tele_row = query_db("SELECT COUNT(*) as c FROM teleconsultations WHERE status IN ('Requested', 'In-Call')", one=True)
        active_teleconsult_count = tele_row["c"] if tele_row else 0

        ref_row = query_db("SELECT COUNT(*) as c FROM referrals WHERE status IN ('Initiated', 'Accepted', 'In-Transit')", one=True)
        active_referral_count = ref_row["c"] if ref_row else 0

        hr_row = query_db("SELECT COUNT(*) as c FROM high_risk_registry WHERE status IN ('Active Surveillance', 'Critical Escalation')", one=True)
        high_risk_count = hr_row["c"] if hr_row else 0

        all_facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")
        all_emergency_patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients ORDER BY is_high_risk DESC, first_name ASC")
    except Exception:
        all_emergency_patients = []

    return {
        "current_user": user,
        "current_facility": user_facility,
        "all_facilities": all_facilities,
        "all_emergency_patients": all_emergency_patients,
        "query_db": query_db,
        "hospital_name": get_setting("hospital_name", "PulseCare National Public Health Network"),
        "tagline": get_setting("tagline", "Equitable & Specialist-Enabled Care for All"),
        "currency": get_setting("currency", "$"),
        "today_date": date.today().strftime("%Y-%m-%d"),
        "now_datetime": datetime.now(),
        "low_stock_count": low_stock_count,
        "pending_lab_count": pending_lab_count,
        "today_apt_count": today_apt_count,
        "active_teleconsult_count": active_teleconsult_count,
        "active_referral_count": active_referral_count,
        "high_risk_count": high_risk_count,
        "selected_lang": session.get("lang") or (request.cookies.get("pulse_lang") if request else "en") or "en",
        "available_languages": [
            ("en", "English"),
            ("hi", "हिंदी (Hindi)"),
            ("ta", "தமிழ் (Tamil)"),
            ("te", "తెలుగు (Telugu)"),
            ("bn", "বাংলা (Bengali)"),
            ("mr", "मराठी (Marathi)"),
            ("gu", "ગુજરાતી (Gujarati)")
        ]
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
        clean_val = str(value).split(".")[0]
        if " " in clean_val:
            dt = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(clean_val, "%Y-%m-%d")
        return dt.strftime(fmt)
    except Exception:
        return str(value)


# -----------------------------------------------------------------------------
# AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
# -----------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access PulseCare Public Health Network.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_accepted(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            user_role = session.get("user_role")
            if user_role not in allowed_roles and user_role != "admin":
                flash(f"Access restricted. Role '{user_role}' is not authorized for this resource.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = query_db("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_role"] = user["role"]
            session["full_name"] = user["full_name"]
            session["facility_id"] = user["facility_id"]
            session.permanent = True

            log_audit(user["id"], "User Login", "Auth", f"Successful login for {username} ({user['role']})", request.remote_addr, user["facility_id"])
            flash(f"Welcome back, {user['full_name']}! Signed in as {user['role'].upper()}.", "success")
            
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))
        else:
            flash("Invalid username or password. Please check your credentials.", "danger")

    # Fetch verified staff directory
    staff_directory = query_db(
        """SELECT u.id, u.username, u.full_name, u.role, u.specialization, u.avatar_url,
                  f.name as facility_name, f.tier_type as facility_tier
           FROM users u
           LEFT JOIN facilities f ON u.facility_id = f.id
           ORDER BY u.id ASC"""
    )
    return render_template("auth/login.html", staff_directory=staff_directory)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def user_profile():
    """User profile management and security settings."""
    user_id = session.get("user_id")
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        flash("User profile not found.", "danger")
        return redirect(url_for("login"))

    facility = query_db("SELECT * FROM facilities WHERE id = ?", (user["facility_id"],), one=True) if user["facility_id"] else None
    department = query_db("SELECT * FROM departments WHERE id = ?", (user["department_id"],), one=True) if user["department_id"] else None
    patient = query_db("SELECT * FROM patients WHERE user_id = ? OR phone = ? OR email = ?", (user_id, user["phone"], user["email"]), one=True) if user["role"] == "patient" else None

    if request.method == "POST":
        action = request.form.get("action", "update_profile")
        
        if action == "update_profile":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            avatar_url = request.form.get("avatar_url", "").strip()
            specialization = request.form.get("specialization", "").strip()
            qualification = request.form.get("qualification", "").strip()
            license_number = request.form.get("license_number", "").strip()
            try:
                consultation_fee = float(request.form.get("consultation_fee") or 0.0)
            except ValueError:
                consultation_fee = 0.0

            if not full_name:
                flash("Full name cannot be empty.", "danger")
                return redirect(url_for("user_profile"))

            execute_db(
                """UPDATE users SET full_name = ?, email = ?, phone = ?, avatar_url = ?,
                                  specialization = ?, qualification = ?, license_number = ?, consultation_fee = ?
                   WHERE id = ?""",
                (full_name, email, phone, avatar_url, specialization, qualification, license_number, consultation_fee, user_id)
            )

            # Update patient table if patient
            if user["role"] == "patient" and patient:
                dob = request.form.get("dob") or patient["dob"]
                gender = request.form.get("gender") or patient["gender"]
                blood_group = request.form.get("blood_group") or patient["blood_group"]
                village = request.form.get("village", "").strip()
                panchayat = request.form.get("panchayat", "").strip()
                address = request.form.get("address", "").strip()
                emergency_name = request.form.get("emergency_contact_name", "").strip()
                emergency_phone = request.form.get("emergency_contact_phone", "").strip()
                emergency_rel = request.form.get("emergency_contact_relation", "").strip()
                abha_id = request.form.get("abha_id", "").strip()
                allergies = request.form.get("allergies", "").strip()
                chronic_conditions = request.form.get("chronic_conditions", "").strip()

                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                execute_db(
                    """UPDATE patients SET first_name = ?, last_name = ?, email = ?, phone = ?,
                                          dob = ?, gender = ?, blood_group = ?, village = ?, panchayat = ?, address = ?,
                                          emergency_contact_name = ?, emergency_contact_phone = ?, emergency_contact_relation = ?,
                                          abha_id = ?, allergies = ?, chronic_conditions = ?
                       WHERE id = ?""",
                    (first_name, last_name, email, phone, dob, gender, blood_group, village, panchayat, address,
                     emergency_name, emergency_phone, emergency_rel, abha_id, allergies, chronic_conditions, patient["id"])
                )

            session["full_name"] = full_name
            log_audit(user_id, "Update Profile", "User", f"Profile details updated by {full_name}", request.remote_addr, user["facility_id"])
            flash("Your profile information has been successfully updated!", "success")
            return redirect(url_for("user_profile"))

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(user["password_hash"], current_password):
                flash("Current password verification failed. Please enter your correct current password.", "danger")
                return redirect(url_for("user_profile") + "#security")

            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "warning")
                return redirect(url_for("user_profile") + "#security")

            if new_password != confirm_password:
                flash("New password and confirmation password do not match.", "danger")
                return redirect(url_for("user_profile") + "#security")

            new_hash = generate_password_hash(new_password)
            execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            log_audit(user_id, "Change Password", "Auth", "Account password updated successfully", request.remote_addr, user["facility_id"])
            flash("Your password has been changed securely! Please use your new password next time you sign in.", "success")
            return redirect(url_for("user_profile") + "#security")

    return render_template(
        "profile/index.html",
        user=user,
        facility=facility,
        department=department,
        patient=patient
    )



@app.route("/logout")
def logout():
    uid = session.get("user_id")
    if uid:
        log_audit(uid, "User Logout", "Auth", "User logged out", request.remote_addr, session.get("facility_id"))
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET"])
def register():
    """ABHA Registration portal — multi-step Aadhaar OTP flow."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth/register.html", sandbox_mode=ABDM_SANDBOX_MODE,
                           mock_aadhaar=ABDM_MOCK_AADHAAR_NUMBERS[0])


# ── ABDM Step 1: Generate OTP ─────────────────────────────────────────────────
@app.route("/register/abha/generate-otp", methods=["POST"])
def abha_generate_otp():
    """
    AJAX endpoint — calls ABDM /v2/registration/aadhaar/generateOtp.
    Body: { aadhaar: "999941057058" }
    Returns JSON: { success, txnId, maskedMobile, error }
    """
    data    = request.get_json() or {}
    aadhaar = data.get("aadhaar", "").strip().replace(" ", "").replace("-", "")

    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return jsonify({"success": False, "error": "Please enter a valid 12-digit Aadhaar number."}), 400

    txn_id, err = abdm_generate_otp(aadhaar)
    if err:
        return jsonify({"success": False, "error": err}), 400

    # Store txnId + aadhaar in server session (not exposed to client)
    session["abdm_txn_id"] = txn_id
    session["abdm_aadhaar"] = aadhaar

    # Mask mobile for display (ABDM returns this; we simulate it)
    masked_mobile = "XXXXXX" + aadhaar[-4:] if txn_id.startswith("ABDM-SANDBOX-") else "XXXXXX0000"
    is_sandbox    = txn_id.startswith("ABDM-SANDBOX-")

    return jsonify({
        "success":      True,
        "txnId":        txn_id,
        "maskedMobile": masked_mobile,
        "sandbox":      is_sandbox,
        "hint":         f"Sandbox mode: use OTP {ABDM_MOCK_OTP}" if is_sandbox else ""
    })


# ── ABDM Step 2: Verify OTP ───────────────────────────────────────────────────
@app.route("/register/abha/verify-otp", methods=["POST"])
def abha_verify_otp():
    """
    AJAX endpoint — calls ABDM /v2/registration/aadhaar/verifyOTP.
    Body: { otp: "123456" }
    Returns JSON: { success, profile: { name, dob, gender, mobile, address }, error }
    """
    data   = request.get_json() or {}
    otp    = data.get("otp", "").strip()
    txn_id = session.get("abdm_txn_id")

    if not txn_id:
        return jsonify({"success": False, "error": "Session expired. Please restart registration."}), 400
    if not otp or len(otp) != 6 or not otp.isdigit():
        return jsonify({"success": False, "error": "Enter the 6-digit OTP sent to your Aadhaar-linked mobile."}), 400

    profile, err = abdm_verify_otp(txn_id, otp, session.get("abdm_aadhaar", ""))
    if err:
        return jsonify({"success": False, "error": err}), 400

    # Update txnId if ABDM returns a new one after OTP verification
    new_txn = profile.get("txnId", txn_id)
    session["abdm_txn_id"] = new_txn

    # Store profile fields in session for final step
    session["abdm_profile"] = {
        "name":    profile.get("name", ""),
        "dob":     profile.get("dob", ""),
        "gender":  profile.get("gender", ""),
        "mobile":  profile.get("mobile", ""),
        "address": profile.get("address", ""),
        "district":profile.get("districtName", ""),
        "state":   profile.get("stateName", ""),
    }

    return jsonify({
        "success": True,
        "profile": session["abdm_profile"]
    })


# ── ABDM Step 3: Create ABHA + PulseCare Account ─────────────────────────────
@app.route("/register/abha/complete", methods=["POST"])
def abha_complete():
    """
    AJAX endpoint — calls ABDM /v2/registration/aadhaar/checkAndGenerateHealthId,
    then creates the PulseCare user + patient record.
    Body: { password, confirm_password, email, village, preferred_language,
            first_name, last_name, dob, gender, mobile }
    Returns JSON: { success, patient_uid, abha_id, redirect_url, error }
    """
    data          = request.get_json() or {}
    txn_id        = session.get("abdm_txn_id")
    abdm_profile  = session.get("abdm_profile", {})

    if not txn_id:
        return jsonify({"success": False, "error": "Session expired. Please restart registration."}), 400

    # Collect form fields (user can edit pre-filled ABDM data)
    first_name  = data.get("first_name",  abdm_profile.get("name", "").split()[0]).strip()
    last_name   = data.get("last_name",   " ".join(abdm_profile.get("name", "").split()[1:])).strip()
    mobile      = data.get("mobile",      abdm_profile.get("mobile", "")).strip()
    email       = data.get("email",       "").strip().lower()
    dob         = data.get("dob",         abdm_profile.get("dob", "")).strip()
    gender      = data.get("gender",      abdm_profile.get("gender", "M"))
    village     = data.get("village",     abdm_profile.get("address", "")).strip()
    pref_lang   = data.get("preferred_language", "en")
    password    = data.get("password", "")
    confirm     = data.get("confirm_password", "")

    # Validate
    errors = []
    if not first_name:
        errors.append("First name is required.")
    if not mobile or not mobile.isdigit() or len(mobile) < 10:
        errors.append("A valid 10-digit mobile number is required.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    if errors:
        return jsonify({"success": False, "error": " | ".join(errors)}), 400

    # Check duplicate mobile
    existing = query_db("SELECT id FROM users WHERE username = ?", (mobile,), one=True)
    if existing:
        return jsonify({"success": False, "error": "An account with this mobile number already exists. Please sign in."}), 409

    # ── Call ABDM Step 3: Generate real 14-digit ABHA number ──────────────────
    abha_data, err = abdm_create_abha(txn_id, mobile)
    if err:
        return jsonify({"success": False, "error": f"ABHA generation failed: {err}"}), 400

    abha_number  = abha_data.get("healthIdNumber", "")   # 14-digit: 91-XXXX-XXXX-XXXX
    abha_address = abha_data.get("healthId", "")          # username@abdm

    # ── Create PulseCare user account ─────────────────────────────────────────
    gender_map = {'M': 'Male', 'Male': 'Male', 'F': 'Female', 'Female': 'Female', 'O': 'Other', 'Other': 'Other'}
    normalized_gender = gender_map.get(gender, 'Male')

    full_name     = f"{first_name} {last_name}".strip()
    password_hash = generate_password_hash(password)
    user_id = execute_db(
        """INSERT INTO users (username, password_hash, full_name, role, email, phone,
                              is_active, created_at)
           VALUES (?, ?, ?, 'patient', ?, ?, 1, datetime('now'))""",
        (mobile, password_hash, full_name, email or None, mobile)
    )

    patient_uid = f"PC-{str(user_id).zfill(5)}"

    # Link to primary sub-centre facility if available
    facility = query_db("SELECT id FROM facilities WHERE tier_type = 'Sub-Centre' LIMIT 1", one=True)
    facility_id = facility["id"] if facility else None

    execute_db(
        """INSERT INTO patients (user_id, patient_uid, first_name, last_name, phone, email,
                                 dob, gender, village, address, abha_id, socioeconomic_category,
                                 facility_id, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'General', ?, 'Outpatient', datetime('now'))""",
        (user_id, patient_uid, first_name, last_name or first_name, mobile,
         email or None, dob or '1990-01-01', normalized_gender, village or None, village or None,
         abha_number, facility_id)
    )

    # Set preferred language in session
    session["selected_lang"] = pref_lang

    log_audit(user_id, "ABHA Patient Registration", "Auth",
              f"Patient registered via ABDM ABHA flow: {full_name} | ABHA: {abha_number} | Address: {abha_address}",
              request.remote_addr, facility_id)

    # ── Auto-login ─────────────────────────────────────────────────────────────
    session.pop("abdm_txn_id",   None)
    session.pop("abdm_aadhaar",  None)
    session.pop("abdm_profile",  None)
    session["user_id"]     = user_id
    session["username"]    = mobile
    session["user_role"]   = "patient"
    session["full_name"]   = full_name
    session["facility_id"] = facility_id
    session.permanent      = True

    return jsonify({
        "success":      True,
        "patient_uid":  patient_uid,
        "abha_id":      abha_number,
        "abha_address": abha_address,
        "redirect_url": url_for("dashboard")
    })


# -----------------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------------

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("user_role")
    user_id = session.get("user_id")
    facility_id = session.get("facility_id")

    # Overview KPIs
    kpis = {
        "total_patients": query_db("SELECT COUNT(*) as c FROM patients", one=True)["c"],
        "active_teleconsults": query_db("SELECT COUNT(*) as c FROM teleconsultations WHERE status IN ('Requested', 'In-Call')", one=True)["c"],
        "pending_referrals": query_db("SELECT COUNT(*) as c FROM referrals WHERE status IN ('Initiated', 'In-Transit')", one=True)["c"],
        "high_risk_patients": query_db("SELECT COUNT(*) as c FROM high_risk_registry WHERE status IN ('Active Surveillance', 'Critical Escalation')", one=True)["c"],
        "total_facilities": query_db("SELECT COUNT(*) as c FROM facilities", one=True)["c"],
        "occupied_beds": query_db("SELECT COUNT(*) as c FROM beds WHERE status = 'Occupied'", one=True)["c"],
        "total_beds": query_db("SELECT COUNT(*) as c FROM beds", one=True)["c"]
    }

    # Recent Teleconsultations
    recent_teleconsults = query_db(
        """SELECT t.*, p.first_name, p.last_name, p.patient_uid, p.village, p.abha_id,
                  u_init.full_name as initiator_name, u_spec.full_name as specialist_name,
                  f_from.name as from_facility_name, f_to.name as to_facility_name
           FROM teleconsultations t
           JOIN patients p ON t.patient_id = p.id
           JOIN users u_init ON t.initiator_user_id = u_init.id
           LEFT JOIN users u_spec ON t.specialist_id = u_spec.id
           JOIN facilities f_from ON t.from_facility_id = f_from.id
           JOIN facilities f_to ON t.target_facility_id = f_to.id
           ORDER BY t.scheduled_at DESC LIMIT 6"""
    )

    # Active Referrals
    recent_referrals = query_db(
        """SELECT r.*, p.first_name, p.last_name, p.patient_uid, p.village, p.abha_id,
                  f_from.name as from_facility_name, f_to.name as to_facility_name,
                  u_doc.full_name as doctor_name
           FROM referrals r
           JOIN patients p ON r.patient_id = p.id
           JOIN facilities f_from ON r.from_facility_id = f_from.id
           JOIN facilities f_to ON r.to_facility_id = f_to.id
           JOIN users u_doc ON r.referring_doctor_id = u_doc.id
           ORDER BY r.initiated_at DESC LIMIT 6"""
    )

    # High-Risk Surveillance Watchlist
    high_risk_list = query_db(
        """SELECT hr.*, p.first_name, p.last_name, p.patient_uid, p.village, p.phone, p.abha_id,
                  u.full_name as assigned_worker_name, f.name as facility_name
           FROM high_risk_registry hr
           JOIN patients p ON hr.patient_id = p.id
           LEFT JOIN users u ON hr.assigned_worker_id = u.id
           LEFT JOIN facilities f ON hr.facility_id = f.id
           ORDER BY hr.severity_score DESC, hr.next_followup_date ASC LIMIT 5"""
    )

    # Network Bed Occupancy by Facility
    facility_occupancy = query_db(
        """SELECT f.name, f.tier_type, f.total_beds,
                  (SELECT COUNT(*) FROM beds b JOIN wards w ON b.ward_id = w.id WHERE w.facility_id = f.id AND b.status = 'Occupied') as occupied_beds
           FROM facilities f ORDER BY f.id ASC"""
    )

    # Patient Portal Specific Data
    patient_data = None
    patient_teleconsults = []
    patient_prescriptions = []
    patient_referrals = []

    if role == "patient":
        patient_record = query_db("SELECT * FROM patients WHERE user_id = ?", (user_id,), one=True)
        if patient_record:
            pid = patient_record["id"]
            patient_data = patient_record
            patient_teleconsults = query_db(
                """SELECT t.*, u_spec.full_name as specialist_name, f_to.name as to_facility_name
                   FROM teleconsultations t
                   LEFT JOIN users u_spec ON t.specialist_id = u_spec.id
                   JOIN facilities f_to ON t.target_facility_id = f_to.id
                   WHERE t.patient_id = ? ORDER BY t.scheduled_at DESC""",
                (pid,)
            )
            patient_prescriptions = query_db(
                """SELECT pr.*, u.full_name as doctor_name
                   FROM prescriptions pr
                   JOIN users u ON pr.doctor_id = u.id
                   WHERE pr.patient_id = ? ORDER BY pr.created_at DESC""",
                (pid,)
            )
            patient_referrals = query_db(
                """SELECT r.*, f_to.name as to_facility_name, u_spec.full_name as specialist_name
                   FROM referrals r
                   JOIN facilities f_to ON r.to_facility_id = f_to.id
                   LEFT JOIN users u_spec ON r.receiving_specialist_id = u_spec.id
                   WHERE r.patient_id = ? ORDER BY r.initiated_at DESC""",
                (pid,)
            )

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        recent_teleconsults=recent_teleconsults,
        recent_referrals=recent_referrals,
        high_risk_list=high_risk_list,
        facility_occupancy=facility_occupancy,
        patient_data=patient_data,
        patient_teleconsults=patient_teleconsults,
        patient_prescriptions=patient_prescriptions,
        patient_referrals=patient_referrals
    )


# -----------------------------------------------------------------------------
# 1. ASSISTED TELECONSULTATION SUITE
# -----------------------------------------------------------------------------

@app.route("/teleconsult")
@login_required
def teleconsult_index():
    status_filter = request.args.get("status", "").strip()
    triage_filter = request.args.get("triage", "").strip()

    sql = """
        SELECT t.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.village, p.abha_id,
               p.is_high_risk, p.high_risk_category,
               u_init.full_name as initiator_name, u_init.role as initiator_role,
               u_spec.full_name as specialist_name, u_spec.specialization,
               f_from.name as from_facility_name, f_from.tier_type as from_facility_tier,
               f_to.name as to_facility_name
        FROM teleconsultations t
        JOIN patients p ON t.patient_id = p.id
        JOIN users u_init ON t.initiator_user_id = u_init.id
        LEFT JOIN users u_spec ON t.specialist_id = u_spec.id
        JOIN facilities f_from ON t.from_facility_id = f_from.id
        JOIN facilities f_to ON t.target_facility_id = f_to.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        sql += " AND t.status = ?"
        params.append(status_filter)
    if triage_filter:
        sql += " AND t.triage_level = ?"
        params.append(triage_filter)

    sql += " ORDER BY CASE t.triage_level WHEN 'Emergency' THEN 1 WHEN 'High-Risk' THEN 2 ELSE 3 END, t.scheduled_at DESC"
    teleconsults = query_db(sql, params)

    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id, is_high_risk FROM patients ORDER BY first_name")
    specialists = query_db("SELECT id, full_name, specialization, qualification FROM users WHERE role = 'doctor' ORDER BY full_name")
    facilities = query_db("SELECT id, name, tier_type FROM facilities ORDER BY id")

    return render_template(
        "teleconsult/index.html",
        teleconsults=teleconsults,
        patients=patients,
        specialists=specialists,
        facilities=facilities,
        status_filter=status_filter,
        triage_filter=triage_filter
    )

@app.route("/teleconsult/new", methods=["POST"])
@login_required
def teleconsult_create():
    patient_id = request.form.get("patient_id")
    specialist_id = request.form.get("specialist_id") or None
    from_facility_id = request.form.get("from_facility_id") or session.get("facility_id") or 4 # Default Rampur Sub-Centre
    target_facility_id = request.form.get("target_facility_id") or 1 # Default District Hospital
    triage_level = request.form.get("triage_level", "Routine")
    chief_complaint = request.form.get("chief_complaint", "").strip()
    clinical_findings = request.form.get("clinical_findings", "").strip()

    # Vitals snapshot
    vitals_snap = {
        "bp": request.form.get("vitals_bp", "120/80"),
        "pulse": request.form.get("vitals_pulse", "76"),
        "spo2": request.form.get("vitals_spo2", "98"),
        "temp": request.form.get("vitals_temp", "37.0"),
        "fbs": request.form.get("vitals_fbs", ""),
        "fhr": request.form.get("vitals_fhr", ""),
        "triage": triage_level
    }

    count_tele = query_db("SELECT COUNT(*) as c FROM teleconsultations", one=True)["c"]
    session_uid = f"TELE-{date.today().year}-{(count_tele + 1):04d}"

    tele_id = execute_db(
        """INSERT INTO teleconsultations (session_uid, patient_id, initiator_user_id, specialist_id, from_facility_id, target_facility_id, triage_level, chief_complaint, clinical_findings, status, vitals_snapshot_json, scheduled_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Requested', ?, datetime('now'))""",
        (session_uid, patient_id, session.get("user_id"), specialist_id, from_facility_id, target_facility_id, triage_level, chief_complaint, clinical_findings, json.dumps(vitals_snap))
    )

    log_audit(session.get("user_id"), "Create Teleconsult", "Teleconsultation", f"Initiated {session_uid} for Patient #{patient_id} (Triage: {triage_level})", request.remote_addr, from_facility_id)
    flash(f"Assisted Teleconsultation request {session_uid} dispatched to District Specialists!", "success")
    return redirect(url_for("teleconsult_session", session_id=tele_id))

@app.route("/teleconsult/session/<int:session_id>")
@login_required
def teleconsult_session(session_id):
    tele = query_db(
        """SELECT t.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.blood_group,
                  p.allergies, p.chronic_conditions, p.village, p.abha_id, p.phone, p.emergency_contact_phone,
                  u_init.full_name as initiator_name, u_init.role as initiator_role, u_init.phone as initiator_phone,
                  u_spec.full_name as specialist_name, u_spec.specialization, u_spec.qualification,
                  f_from.name as from_facility_name, f_from.tier_type as from_facility_tier,
                  f_to.name as to_facility_name
           FROM teleconsultations t
           JOIN patients p ON t.patient_id = p.id
           JOIN users u_init ON t.initiator_user_id = u_init.id
           LEFT JOIN users u_spec ON t.specialist_id = u_spec.id
           JOIN facilities f_from ON t.from_facility_id = f_from.id
           JOIN facilities f_to ON t.target_facility_id = f_to.id
           WHERE t.id = ?""",
        (session_id,),
        one=True
    )
    if not tele:
        flash("Teleconsultation session not found.", "danger")
        return redirect(url_for("teleconsult_index"))

    # Update status to In-Call if specialist opens it
    if session.get("user_role") == "doctor" and tele["status"] == "Requested":
        execute_db("UPDATE teleconsultations SET status = 'In-Call', started_at = datetime('now'), specialist_id = ? WHERE id = ?", (session.get("user_id"), session_id))
        tele["status"] = "In-Call"

    # Patient's latest vitals & past teleconsultations
    vitals_history = query_db("SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT 5", (tele["patient_id"],))
    medicines = query_db("SELECT * FROM medicines ORDER BY brand_name ASC")
    specialists = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")

    return render_template(
        "teleconsult/room.html",
        tele=tele,
        vitals_history=vitals_history,
        medicines=medicines,
        specialists=specialists
    )

@app.route("/teleconsult/session/<int:session_id>/update", methods=["POST"])
@login_required
def teleconsult_update(session_id):
    specialist_advice = request.form.get("specialist_advice", "").strip()
    status = request.form.get("status", "Completed")

    execute_db(
        """UPDATE teleconsultations 
           SET specialist_advice = ?, status = ?, completed_at = datetime('now')
           WHERE id = ?""",
        (specialist_advice, status, session_id)
    )

    # Check if prescription items were submitted during teleconsult
    med_ids = request.form.getlist("med_id[]")
    if med_ids and any(med_ids):
        tele = query_db("SELECT * FROM teleconsultations WHERE id = ?", (session_id,), one=True)
        count_rx = query_db("SELECT COUNT(*) as c FROM prescriptions", one=True)["c"]
        rx_num = f"RX-TELE-{date.today().year}-{(count_rx + 1):04d}"
        
        rx_id = execute_db(
            """INSERT INTO prescriptions (prescription_number, teleconsult_id, patient_id, doctor_id, facility_id, status, special_instructions)
               VALUES (?, ?, ?, ?, ?, 'Pending', ?)""",
            (rx_num, session_id, tele["patient_id"], session.get("user_id"), tele["from_facility_id"], specialist_advice)
        )
        execute_db("UPDATE teleconsultations SET prescription_id = ? WHERE id = ?", (rx_id, session_id))

        dosages = request.form.getlist("dosage[]")
        frequencies = request.form.getlist("frequency[]")
        durations = request.form.getlist("duration_days[]")
        instructions = request.form.getlist("instructions[]")
        quantities = request.form.getlist("quantity_prescribed[]")

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

    log_audit(session.get("user_id"), "Complete Teleconsult", "Teleconsultation", f"Updated Teleconsult #{session_id} to {status}", request.remote_addr)
    flash(f"Teleconsultation updated successfully! Digital prescription & advice saved.", "success")
    return redirect(url_for("teleconsult_session", session_id=session_id))


# -----------------------------------------------------------------------------
# 2. CLOSED-LOOP REFERRAL MANAGEMENT
# -----------------------------------------------------------------------------

@app.route("/referrals")
@login_required
def referrals_index():
    status_filter = request.args.get("status", "").strip()
    priority_filter = request.args.get("priority", "").strip()

    sql = """
        SELECT r.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.village, p.abha_id, p.phone,
               f_from.name as from_facility_name, f_from.tier_type as from_facility_tier,
               f_to.name as to_facility_name, f_to.tier_type as to_facility_tier,
               u_doc.full_name as doctor_name, u_spec.full_name as specialist_name,
               u_asha.full_name as followup_asha_name
        FROM referrals r
        JOIN patients p ON r.patient_id = p.id
        JOIN facilities f_from ON r.from_facility_id = f_from.id
        JOIN facilities f_to ON r.to_facility_id = f_to.id
        JOIN users u_doc ON r.referring_doctor_id = u_doc.id
        LEFT JOIN users u_spec ON r.receiving_specialist_id = u_spec.id
        LEFT JOIN users u_asha ON r.assigned_followup_asha_id = u_asha.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        sql += " AND r.status = ?"
        params.append(status_filter)
    if priority_filter:
        sql += " AND r.triage_priority = ?"
        params.append(priority_filter)

    sql += " ORDER BY CASE r.triage_priority WHEN 'Emergency - Red' THEN 1 WHEN 'Urgent - Yellow' THEN 2 ELSE 3 END, r.initiated_at DESC"
    referrals = query_db(sql, params)

    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients ORDER BY first_name")
    facilities = query_db("SELECT id, name, tier_type FROM facilities ORDER BY id")
    specialists = query_db("SELECT id, full_name, specialization FROM users WHERE role = 'doctor' ORDER BY full_name")
    asha_workers = query_db("SELECT id, full_name FROM users WHERE role = 'asha_cho' ORDER BY full_name")

    return render_template(
        "referrals/index.html",
        referrals=referrals,
        patients=patients,
        facilities=facilities,
        specialists=specialists,
        asha_workers=asha_workers,
        status_filter=status_filter,
        priority_filter=priority_filter
    )

@app.route("/referrals/new", methods=["POST"])
@login_required
def referral_create():
    patient_id = request.form.get("patient_id")
    from_facility_id = request.form.get("from_facility_id") or session.get("facility_id") or 3 # Default PHC
    to_facility_id = request.form.get("to_facility_id") or 1 # Default District Hospital
    specialty_needed = request.form.get("specialty_needed", "General Medicine").strip()
    reason = request.form.get("reason", "").strip()
    provisional_diagnosis = request.form.get("provisional_diagnosis", "").strip()
    triage_priority = request.form.get("triage_priority", "Urgent - Yellow")
    transport_mode = request.form.get("transport_mode", "108 Ambulance")
    assigned_followup_asha_id = request.form.get("assigned_followup_asha_id") or None

    count_ref = query_db("SELECT COUNT(*) as c FROM referrals", one=True)["c"]
    referral_uid = f"REF-{date.today().year}-{(count_ref + 1):04d}"

    execute_db(
        """INSERT INTO referrals (referral_uid, patient_id, from_facility_id, to_facility_id, referring_doctor_id, specialty_needed, reason, provisional_diagnosis, triage_priority, transport_mode, status, initiated_at, assigned_followup_asha_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Initiated', datetime('now'), ?)""",
        (referral_uid, patient_id, from_facility_id, to_facility_id, session.get("user_id"), specialty_needed, reason, provisional_diagnosis, triage_priority, transport_mode, assigned_followup_asha_id)
    )

    # Update patient status to 'Referred'
    execute_db("UPDATE patients SET status = 'Referred' WHERE id = ?", (patient_id,))

    log_audit(session.get("user_id"), "Initiate Referral", "Referrals", f"Created inter-facility referral {referral_uid} to Facility #{to_facility_id}", request.remote_addr, from_facility_id)
    flash(f"Referral {referral_uid} initiated successfully with {transport_mode} notification!", "success")
    return redirect(url_for("referrals_index"))

@app.route("/referrals/<int:ref_id>/status", methods=["POST"])
@login_required
def referral_status_update(ref_id):
    new_status = request.form.get("status")
    counter_notes = request.form.get("counter_referral_notes", "").strip()

    if new_status == "Accepted":
        execute_db("UPDATE referrals SET status = 'Accepted', accepted_at = datetime('now'), receiving_specialist_id = ? WHERE id = ?", (session.get("user_id"), ref_id))
    elif new_status == "In-Transit":
        execute_db("UPDATE referrals SET status = 'In-Transit' WHERE id = ?", (ref_id,))
    elif new_status == "Attended":
        execute_db("UPDATE referrals SET status = 'Attended', attended_at = datetime('now'), receiving_specialist_id = ? WHERE id = ?", (session.get("user_id"), ref_id))
    elif new_status == "Counter-Referred":
        execute_db(
            """UPDATE referrals 
               SET status = 'Counter-Referred', counter_referral_notes = ?, attended_at = COALESCE(attended_at, datetime('now'))
               WHERE id = ?""",
            (counter_notes, ref_id)
        )
    else:
        execute_db("UPDATE referrals SET status = ? WHERE id = ?", (new_status, ref_id))

    log_audit(session.get("user_id"), "Update Referral", "Referrals", f"Updated Referral #{ref_id} status to {new_status}", request.remote_addr)
    flash(f"Referral status updated to {new_status}!", "info")
    return redirect(request.referrer or url_for("referrals_index"))


# -----------------------------------------------------------------------------
# 3. HIGH-RISK PATIENT SURVEILLANCE REGISTRY
# -----------------------------------------------------------------------------

@app.route("/high-risk")
@login_required
def high_risk_index():
    category_filter = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    sql = """
        SELECT hr.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.village, p.phone, p.abha_id,
               p.emergency_contact_name, p.emergency_contact_phone,
               u.full_name as assigned_worker_name, u.role as assigned_worker_role,
               f.name as facility_name
        FROM high_risk_registry hr
        JOIN patients p ON hr.patient_id = p.id
        LEFT JOIN users u ON hr.assigned_worker_id = u.id
        LEFT JOIN facilities f ON hr.facility_id = f.id
        WHERE 1=1
    """
    params = []
    if category_filter:
        sql += " AND hr.category = ?"
        params.append(category_filter)
    if status_filter:
        sql += " AND hr.status = ?"
        params.append(status_filter)

    sql += " ORDER BY hr.severity_score DESC, hr.next_followup_date ASC"
    registry = query_db(sql, params)

    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients ORDER BY first_name")
    workers = query_db("SELECT id, full_name, role FROM users WHERE role IN ('asha_cho', 'nurse', 'doctor', 'medical_officer') ORDER BY full_name")
    facilities = query_db("SELECT id, name FROM facilities ORDER BY id")

    return render_template(
        "high_risk/index.html",
        registry=registry,
        patients=patients,
        workers=workers,
        facilities=facilities,
        category_filter=category_filter,
        status_filter=status_filter
    )

@app.route("/high-risk/new", methods=["POST"])
@login_required
def high_risk_create():
    patient_id = request.form.get("patient_id")
    category = request.form.get("category", "Maternal High-Risk (HRP)")
    risk_factors = request.form.get("risk_factors", "").strip()
    severity_score = int(request.form.get("severity_score", 3))
    assigned_worker_id = request.form.get("assigned_worker_id") or None
    facility_id = request.form.get("facility_id") or session.get("facility_id") or 4
    next_followup_date = request.form.get("next_followup_date", (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"))
    clinical_notes = request.form.get("clinical_notes", "").strip()

    execute_db(
        """INSERT INTO high_risk_registry (patient_id, category, risk_factors, severity_score, assigned_worker_id, facility_id, last_assessment_date, next_followup_date, status, clinical_notes)
           VALUES (?, ?, ?, ?, ?, ?, date('now'), ?, 'Active Surveillance', ?)""",
        (patient_id, category, risk_factors, severity_score, assigned_worker_id, facility_id, next_followup_date, clinical_notes)
    )

    # Flag patient as high risk
    execute_db("UPDATE patients SET is_high_risk = 1, high_risk_category = ? WHERE id = ?", (category, patient_id))

    log_audit(session.get("user_id"), "Enroll High Risk", "High-Risk Registry", f"Enrolled Patient #{patient_id} into {category} (Severity: {severity_score})", request.remote_addr)
    flash(f"Patient enrolled in {category} active surveillance registry!", "success")
    return redirect(url_for("high_risk_index"))

@app.route("/high-risk/followup/<int:entry_id>", methods=["POST"])
@login_required
def high_risk_followup(entry_id):
    status = request.form.get("status", "Active Surveillance")
    severity_score = int(request.form.get("severity_score", 3))
    next_followup_date = request.form.get("next_followup_date")
    notes = request.form.get("clinical_notes", "").strip()

    execute_db(
        """UPDATE high_risk_registry
           SET status = ?, severity_score = ?, next_followup_date = ?, last_assessment_date = date('now'), clinical_notes = ?
           WHERE id = ?""",
        (status, severity_score, next_followup_date, notes, entry_id)
    )

    log_audit(session.get("user_id"), "High Risk Follow-up", "High-Risk Registry", f"Logged follow-up for Entry #{entry_id} (Status: {status})", request.remote_addr)
    flash("High-risk surveillance follow-up logged successfully!", "success")
    return redirect(url_for("high_risk_index"))


# -----------------------------------------------------------------------------
# 4. CROSS-FACILITY MEDICINE & DIAGNOSTIC AVAILABILITY GRID
# -----------------------------------------------------------------------------

@app.route("/network/availability")
@login_required
def network_availability():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()
    facility_filter = request.args.get("facility_id", "").strip()

    # Query Medicines across facilities
    med_sql = """
        SELECT fi.id as inv_id, fi.stock_quantity, fi.reorder_threshold, fi.last_restocked,
               m.code as med_code, m.brand_name, m.generic_name, m.category as med_category, m.form, m.strength, m.is_essential_life_saving,
               f.id as facility_id, f.name as facility_name, f.tier_type as facility_tier, f.contact_phone
        FROM facility_inventory fi
        JOIN medicines m ON fi.medicine_id = m.id
        JOIN facilities f ON fi.facility_id = f.id
        WHERE 1=1
    """
    med_params = []
    if search_query:
        med_sql += " AND (m.brand_name LIKE ? OR m.generic_name LIKE ? OR m.code LIKE ?)"
        term = f"%{search_query}%"
        med_params.extend([term, term, term])
    if category_filter:
        med_sql += " AND m.category = ?"
        med_params.append(category_filter)
    if facility_filter:
        med_sql += " AND fi.facility_id = ?"
        med_params.append(facility_filter)

    med_sql += " ORDER BY m.is_essential_life_saving DESC, m.brand_name ASC, f.id ASC"
    inventory_items = query_db(med_sql, med_params)

    # Query Diagnostic Equipment across facilities
    diag_sql = """
        SELECT fd.id as diag_id, fd.is_operational, fd.equipment_status, fd.average_wait_hours,
               ltc.code as test_code, ltc.name as test_name, ltc.category as test_category, ltc.specimen_type,
               f.id as facility_id, f.name as facility_name, f.tier_type as facility_tier, f.contact_phone
        FROM facility_diagnostics fd
        JOIN lab_tests_catalog ltc ON fd.test_id = ltc.id
        JOIN facilities f ON fd.facility_id = f.id
        ORDER BY ltc.category ASC, f.id ASC
    """
    diagnostic_items = query_db(diag_sql)
    facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")
    categories = query_db("SELECT DISTINCT category FROM medicines ORDER BY category")

    return render_template(
        "network/availability.html",
        inventory_items=inventory_items,
        diagnostic_items=diagnostic_items,
        facilities=facilities,
        categories=categories,
        search_query=search_query,
        category_filter=category_filter,
        facility_filter=facility_filter
    )


# -----------------------------------------------------------------------------
# 5. PUBLIC HEALTH QUALITY & FACILITY ANALYTICS DASHBOARD
# -----------------------------------------------------------------------------

@app.route("/facility/analytics")
@login_required
def facility_analytics():
    # Public health quality indicators
    stats = {
        "teleconsult_total": query_db("SELECT COUNT(*) as c FROM teleconsultations", one=True)["c"],
        "teleconsult_completed": query_db("SELECT COUNT(*) as c FROM teleconsultations WHERE status = 'Completed'", one=True)["c"],
        "referral_total": query_db("SELECT COUNT(*) as c FROM referrals", one=True)["c"],
        "referral_completed": query_db("SELECT COUNT(*) as c FROM referrals WHERE status IN ('Attended', 'Counter-Referred')", one=True)["c"],
        "high_risk_maternal": query_db("SELECT COUNT(*) as c FROM high_risk_registry WHERE category = 'Maternal High-Risk (HRP)'", one=True)["c"],
        "high_risk_child": query_db("SELECT COUNT(*) as c FROM high_risk_registry WHERE category = 'Child Malnutrition & Immunization'", one=True)["c"],
        "high_risk_ncd": query_db("SELECT COUNT(*) as c FROM high_risk_registry WHERE category LIKE 'Chronic NCD%'", one=True)["c"],
        "stockout_alerts": query_db("SELECT COUNT(*) as c FROM facility_inventory WHERE stock_quantity <= reorder_threshold", one=True)["c"]
    }

    # Referral turnaround & counter-referral compliance %
    referral_completion_rate = 0.0
    if stats["referral_total"] > 0:
        referral_completion_rate = round((stats["referral_completed"] / stats["referral_total"]) * 100, 1)

    teleconsult_success_rate = 0.0
    if stats["teleconsult_total"] > 0:
        teleconsult_success_rate = round((stats["teleconsult_completed"] / stats["teleconsult_total"]) * 100, 1)

    facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")

    return render_template(
        "facility/analytics.html",
        stats=stats,
        referral_completion_rate=referral_completion_rate,
        teleconsult_success_rate=teleconsult_success_rate,
        facilities=facilities
    )


# -----------------------------------------------------------------------------
# 6. EMERGENCY 108 ESCALATION & TRIAGE PROTOCOL
# -----------------------------------------------------------------------------

@app.route("/emergency/escalate", methods=["POST"])
@login_required
def emergency_escalate():
    patient_id = request.form.get("patient_id")
    from_facility_id = request.form.get("from_facility_id") or session.get("facility_id") or 4
    emergency_reason = request.form.get("emergency_reason", "Acute Medical Emergency / Shock / Pre-eclampsia").strip()

    # 1. Update patient status to 'Critical'
    execute_db("UPDATE patients SET status = 'Critical', is_high_risk = 1 WHERE id = ?", (patient_id,))

    # 2. Fast-track 108 Ambulance & Emergency Referral to District Hospital (ID: 1)
    count_ref = query_db("SELECT COUNT(*) as c FROM referrals", one=True)["c"]
    referral_uid = f"REF-EMER-{(count_ref + 1):04d}"
    execute_db(
        """INSERT INTO referrals (referral_uid, patient_id, from_facility_id, to_facility_id, referring_doctor_id, specialty_needed, reason, provisional_diagnosis, triage_priority, transport_mode, status, initiated_at)
           VALUES (?, ?, ?, 1, ?, 'Emergency & Critical Care', ?, 'Impending Vital Failure / Red Flag Triage', 'Emergency - Red', '108 Ambulance', 'In-Transit', datetime('now'))""",
        (referral_uid, patient_id, from_facility_id, session.get("user_id"), emergency_reason)
    )

    log_audit(session.get("user_id"), "Emergency Escalation", "Emergency 108", f"TRIGGERED 108 EMERGENCY AMBULANCE for Patient #{patient_id}: {emergency_reason}", request.remote_addr, from_facility_id)
    flash(f"🚨 EMERGENCY 108 AMBULANCE DISPATCHED! Patient fast-tracked to District Hospital Emergency Bay ({referral_uid}).", "danger")
    return redirect(url_for("referrals_index"))


# -----------------------------------------------------------------------------
# 7. ABHA NATIONAL HEALTH ID & FHIR CLINICAL BUNDLE INTEROPERABILITY
# -----------------------------------------------------------------------------

@app.route("/patients/<int:patient_id>/generate-abha", methods=["POST"])
@login_required
def generate_abha(patient_id):
    """Generates a 14-digit ABDM-compliant Ayushman Bharat Health Account ID."""
    p = query_db("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if p and not p["abha_id"]:
        num1 = random.randint(1000, 9999)
        num2 = random.randint(1000, 9999)
        num3 = random.randint(1000, 9999)
        abha_id = f"91-{num1}-{num2}-{num3}"
        execute_db("UPDATE patients SET abha_id = ? WHERE id = ?", (abha_id, patient_id))
        flash(f"ABHA National Health ID {abha_id} successfully linked to patient record!", "success")
    return redirect(url_for("patient_view", patient_id=patient_id))

@app.route("/api/patients/<int:patient_id>/fhir")
@login_required
def export_fhir_bundle(patient_id):
    """Exports longitudinal clinical records formatted in HL7 FHIR standard JSON Bundle."""
    patient = query_db("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    vitals = query_db("SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC", (patient_id,))
    prescriptions = query_db("SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
    consultations = query_db("SELECT * FROM consultations WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "identifier": {
            "system": "https://abdm.gov.in/fhir/bundle",
            "value": f"PULSECARE-FHIR-{patient['patient_uid']}"
        },
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": patient["patient_uid"],
                    "identifier": [
                        {"system": "https://abdm.gov.in/abha", "value": patient["abha_id"] or "Pending"},
                        {"system": "https://pulsecare-publichealth.gov/uid", "value": patient["patient_uid"]}
                    ],
                    "name": [{"text": f"{patient['first_name']} {patient['last_name']}"}],
                    "gender": (patient["gender"] or "unknown").lower(),
                    "birthDate": patient["dob"],
                    "address": [{"line": [patient["address"] or ""], "city": patient["village"] or "", "state": "Metro State"}],
                    "telecom": [{"system": "phone", "value": patient["phone"]}]
                }
            }
        ]
    }

    # Add FHIR Condition entries
    if patient["chronic_conditions"]:
        for cond in patient["chronic_conditions"].split(","):
            fhir_bundle["entry"].append({
                "resource": {
                    "resourceType": "Condition",
                    "subject": {"reference": f"Patient/{patient['patient_uid']}"},
                    "code": {"text": cond.strip()},
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]}
                }
            })

    # Add FHIR Observation entries (Vitals)
    for v in vitals[:3]:
        fhir_bundle["entry"].append({
            "resource": {
                "resourceType": "Observation",
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                "subject": {"reference": f"Patient/{patient['patient_uid']}"},
                "effectiveDateTime": v["recorded_at"],
                "component": [
                    {"code": {"text": "Systolic BP"}, "valueQuantity": {"value": v["blood_pressure_sys"], "unit": "mmHg"}},
                    {"code": {"text": "Diastolic BP"}, "valueQuantity": {"value": v["blood_pressure_dia"], "unit": "mmHg"}},
                    {"code": {"text": "Heart Rate"}, "valueQuantity": {"value": v["heart_rate_bpm"], "unit": "beats/min"}},
                    {"code": {"text": "SpO2"}, "valueQuantity": {"value": v["spo2_percent"], "unit": "%"}}
                ]
            }
        })

    response = make_response(jsonify(fhir_bundle))
    response.headers["Content-Disposition"] = f"attachment; filename=fhir-bundle-{patient['patient_uid']}.json"
    return response


# -----------------------------------------------------------------------------
# 8. LOW-CONNECTIVITY OFFLINE SYNC SIMULATOR API
# -----------------------------------------------------------------------------

@app.route("/api/sync/offline-records", methods=["POST"])
def sync_offline_records():
    """Accepts offline-cached records from frontline mobile devices and commits to SQLite."""
    data = request.get_json(force=True, silent=True) or {}
    synced_count = 0

    # Sync offline vitals
    offline_vitals = data.get("vitals", [])
    for v in offline_vitals:
        try:
            execute_db(
                """INSERT INTO vitals (patient_id, recorded_by_id, facility_id, temperature_c, heart_rate_bpm, blood_pressure_sys, blood_pressure_dia, spo2_percent, blood_sugar_mgdl, triage_color, notes, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (v.get("patient_id"), v.get("recorded_by_id"), v.get("facility_id"), v.get("temp"), v.get("pulse"), v.get("sys"), v.get("dia"), v.get("spo2"), v.get("sugar"), v.get("triage", "Green"), v.get("notes", "Synced from offline cache"), v.get("recorded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            )
            synced_count += 1
        except Exception as e:
            print(f"Sync error: {e}")

    return jsonify({
        "status": "success",
        "synced_records": synced_count,
        "server_time": datetime.utcnow().isoformat() + "Z"
    })


# -----------------------------------------------------------------------------
# 9. PATIENT DIRECTORY & PATIENT 360 EHR
# -----------------------------------------------------------------------------

@app.route("/patients")
@login_required
def patients_index():
    query_param = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    facility_filter = request.args.get("facility_id", "").strip()
    high_risk_filter = request.args.get("high_risk", "").strip()

    sql = """
        SELECT p.*, f.name as facility_name, f.tier_type as facility_tier,
               u_asha.full_name as assigned_asha_name
        FROM patients p
        LEFT JOIN facilities f ON p.facility_id = f.id
        LEFT JOIN users u_asha ON p.assigned_asha_id = u_asha.id
        WHERE 1=1
    """
    params = []

    if query_param:
        sql += " AND (p.first_name LIKE ? OR p.last_name LIKE ? OR p.patient_uid LIKE ? OR p.abha_id LIKE ? OR p.phone LIKE ? OR p.village LIKE ?)"
        term = f"%{query_param}%"
        params.extend([term, term, term, term, term, term])

    if status_filter:
        sql += " AND p.status = ?"
        params.append(status_filter)

    if facility_filter:
        sql += " AND p.facility_id = ?"
        params.append(facility_filter)

    if high_risk_filter:
        sql += " AND p.is_high_risk = 1"

    sql += " ORDER BY p.is_high_risk DESC, p.created_at DESC"
    patients = query_db(sql, params)
    facilities = query_db("SELECT id, name, tier_type FROM facilities ORDER BY id ASC")

    return render_template(
        "patients/index.html",
        patients=patients,
        facilities=facilities,
        query=query_param,
        status_filter=status_filter,
        facility_filter=facility_filter,
        high_risk_filter=high_risk_filter
    )

@app.route("/patients/new", methods=["GET", "POST"])
@login_required
def patient_create():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        dob = request.form.get("dob")
        gender = request.form.get("gender")
        blood_group = request.form.get("blood_group")
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        village = request.form.get("village", "").strip()
        panchayat = request.form.get("panchayat", "").strip()
        address = request.form.get("address", "").strip()
        facility_id = request.form.get("facility_id") or session.get("facility_id") or 4
        assigned_asha_id = request.form.get("assigned_asha_id") or None
        socioeconomic_category = request.form.get("socioeconomic_category", "BPL")
        emergency_name = request.form.get("emergency_contact_name", "").strip()
        emergency_phone = request.form.get("emergency_contact_phone", "").strip()
        emergency_relation = request.form.get("emergency_contact_relation", "").strip()
        allergies = request.form.get("allergies", "").strip()
        chronic_conditions = request.form.get("chronic_conditions", "").strip()
        is_high_risk = 1 if request.form.get("is_high_risk") else 0
        high_risk_category = request.form.get("high_risk_category") if is_high_risk else None

        # Generate Unique UID & ABHA ID
        count = query_db("SELECT COUNT(*) as c FROM patients", one=True)["c"]
        patient_uid = f"PC-{date.today().year}-{(count + 1):04d}"
        num1 = random.randint(1000, 9999)
        num2 = random.randint(1000, 9999)
        num3 = random.randint(1000, 9999)
        abha_id = f"91-{num1}-{num2}-{num3}"

        patient_id = execute_db(
            """INSERT INTO patients (patient_uid, abha_id, facility_id, first_name, last_name, dob, gender, blood_group,
                                     phone, email, village, panchayat, address, emergency_contact_name, emergency_contact_phone,
                                     emergency_contact_relation, allergies, chronic_conditions, socioeconomic_category,
                                     is_high_risk, high_risk_category, assigned_asha_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Outpatient')""",
            (patient_uid, abha_id, facility_id, first_name, last_name, dob, gender, blood_group,
             phone, email, village, panchayat, address, emergency_name, emergency_phone,
             emergency_relation, allergies, chronic_conditions, socioeconomic_category,
             is_high_risk, high_risk_category, assigned_asha_id)
        )

        log_audit(session.get("user_id"), "Register Patient", "Patients", f"Registered {first_name} {last_name} ({patient_uid}) with ABHA: {abha_id}", request.remote_addr, facility_id)
        flash(f"Patient {first_name} {last_name} registered successfully with ABHA ID {abha_id}!", "success")
        return redirect(url_for("patient_view", patient_id=patient_id))

    facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")
    asha_workers = query_db("SELECT id, full_name FROM users WHERE role = 'asha_cho' ORDER BY full_name")
    return render_template("patients/form.html", patient=None, facilities=facilities, asha_workers=asha_workers)

@app.route("/patients/<int:patient_id>")
@login_required
def patient_view(patient_id):
    patient = query_db(
        """SELECT p.*, f.name as facility_name, f.tier_type as facility_tier,
                  u_asha.full_name as assigned_asha_name, u_asha.phone as assigned_asha_phone
           FROM patients p
           LEFT JOIN facilities f ON p.facility_id = f.id
           LEFT JOIN users u_asha ON p.assigned_asha_id = u_asha.id
           WHERE p.id = ?""",
        (patient_id,),
        one=True
    )
    if not patient:
        flash("Patient record not found.", "danger")
        return redirect(url_for("patients_index"))

    vitals = query_db("SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at DESC", (patient_id,))
    teleconsults = query_db(
        """SELECT t.*, u_spec.full_name as specialist_name, f_to.name as to_facility_name
           FROM teleconsultations t
           LEFT JOIN users u_spec ON t.specialist_id = u_spec.id
           JOIN facilities f_to ON t.target_facility_id = f_to.id
           WHERE t.patient_id = ? ORDER BY t.scheduled_at DESC""",
        (patient_id,)
    )
    referrals = query_db(
        """SELECT r.*, f_from.name as from_facility_name, f_to.name as to_facility_name, u_doc.full_name as doctor_name
           FROM referrals r
           JOIN facilities f_from ON r.from_facility_id = f_from.id
           JOIN facilities f_to ON r.to_facility_id = f_to.id
           JOIN users u_doc ON r.referring_doctor_id = u_doc.id
           WHERE r.patient_id = ? ORDER BY r.initiated_at DESC""",
        (patient_id,)
    )
    prescriptions = query_db(
        """SELECT pr.*, u.full_name as doctor_name, f.name as facility_name
           FROM prescriptions pr
           JOIN users u ON pr.doctor_id = u.id
           LEFT JOIN facilities f ON pr.facility_id = f.id
           WHERE pr.patient_id = ? ORDER BY pr.created_at DESC""",
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

    lab_orders = query_db(
        """SELECT lo.*, u.full_name as doctor_name
           FROM lab_orders lo
           JOIN users u ON lo.doctor_id = u.id
           WHERE lo.patient_id = ? ORDER BY lo.ordered_at DESC""",
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

    invoices = query_db("SELECT * FROM invoices WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
    high_risk_entries = query_db("SELECT * FROM high_risk_registry WHERE patient_id = ? ORDER BY next_followup_date ASC", (patient_id,))

    return render_template(
        "patients/view.html",
        patient=patient,
        vitals=vitals,
        teleconsults=teleconsults,
        referrals=referrals,
        prescriptions=prescriptions,
        lab_orders=lab_orders,
        invoices=invoices,
        high_risk_entries=high_risk_entries
    )

@app.route("/patients/<int:patient_id>/vitals", methods=["POST"])
@login_required
def vitals_create(patient_id):
    temp = float(request.form.get("temperature_c") or 37.0)
    pulse = int(request.form.get("heart_rate_bpm") or 75)
    sys_bp = int(request.form.get("blood_pressure_sys") or 120)
    dia_bp = int(request.form.get("blood_pressure_dia") or 80)
    resp = int(request.form.get("respiratory_rate") or 16)
    spo2 = int(request.form.get("spo2_percent") or 98)
    weight = float(request.form.get("weight_kg") or 0.0)
    height = float(request.form.get("height_cm") or 0.0)
    sugar = float(request.form.get("blood_sugar_mgdl") or 0.0) if request.form.get("blood_sugar_mgdl") else None
    hb = float(request.form.get("hemoglobin_gdl") or 0.0) if request.form.get("hemoglobin_gdl") else None
    fhr = int(request.form.get("fetal_heart_rate") or 0) if request.form.get("fetal_heart_rate") else None
    notes = request.form.get("notes", "").strip()

    # Calculate BMI
    bmi = None
    if weight > 0 and height > 0:
        height_m = height / 100.0
        bmi = round(weight / (height_m * height_m), 1)

    # Automated Digital Triage Scoring
    triage = "Green"
    if sys_bp >= 160 or dia_bp >= 105 or spo2 < 92 or (fhr and (fhr < 110 or fhr > 160)) or (hb and hb < 7.0):
        triage = "Red"
    elif sys_bp >= 140 or dia_bp >= 90 or spo2 < 95 or (sugar and sugar > 200) or (hb and hb < 10.0):
        triage = "Yellow"

    facility_id = session.get("facility_id") or 4
    execute_db(
        """INSERT INTO vitals (patient_id, recorded_by_id, facility_id, temperature_c, heart_rate_bpm, blood_pressure_sys, blood_pressure_dia, respiratory_rate, spo2_percent, weight_kg, height_cm, bmi, blood_sugar_mgdl, hemoglobin_gdl, fetal_heart_rate, triage_color, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, session.get("user_id"), facility_id, temp, pulse, sys_bp, dia_bp, resp, spo2, weight, height, bmi, sugar, hb, fhr, triage, notes)
    )

    flash(f"Point-of-Care Vitals logged successfully! Digital Triage Color: {triage.upper()}.", "success" if triage == "Green" else "warning")
    return redirect(url_for("patient_view", patient_id=patient_id))


# -----------------------------------------------------------------------------
# 10. APPOINTMENTS & OUTPATIENT (OPD) QUEUE
# -----------------------------------------------------------------------------

@app.route("/appointments")
@login_required
def appointments_index():
    date_filter = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    sql = """
        SELECT a.*, p.first_name, p.last_name, p.patient_uid, p.phone, p.village, p.abha_id,
               u.full_name as doctor_name, d.name as department_name, f.name as facility_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON a.doctor_id = u.id
        LEFT JOIN departments d ON a.department_id = d.id
        LEFT JOIN facilities f ON a.facility_id = f.id
        WHERE a.appointment_date = ?
        ORDER BY a.token_number ASC
    """
    appointments = query_db(sql, (date_filter,))
    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role IN ('doctor', 'medical_officer') ORDER BY full_name")
    departments = query_db("SELECT id, name FROM departments ORDER BY name")
    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients ORDER BY first_name")

    return render_template(
        "appointments/index.html",
        appointments=appointments,
        doctors=doctors,
        departments=departments,
        patients=patients,
        date_filter=date_filter
    )

@app.route("/appointments/new", methods=["POST"])
@login_required
def appointment_create():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    dept_id = request.form.get("department_id") or None
    facility_id = request.form.get("facility_id") or session.get("facility_id") or 1
    apt_date = request.form.get("appointment_date")
    apt_time = request.form.get("appointment_time")
    apt_type = request.form.get("type", "Consultation")
    reason = request.form.get("reason", "").strip()

    count_today = query_db("SELECT COUNT(*) as c FROM appointments WHERE appointment_date = ?", (apt_date,), one=True)["c"]
    token_num = count_today + 1
    apt_num = f"APT-{apt_date.replace('-', '')}-{token_num:03d}"

    execute_db(
        """INSERT INTO appointments (appointment_number, patient_id, doctor_id, facility_id, department_id, appointment_date, appointment_time, type, status, token_number, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Booked', ?, ?)""",
        (apt_num, patient_id, doctor_id, facility_id, dept_id, apt_date, apt_time, apt_type, token_num, reason)
    )

    flash(f"Appointment booked successfully! Token #{token_num} ({apt_num}).", "success")
    return redirect(url_for("appointments_index", date=apt_date))

@app.route("/appointments/<int:apt_id>/status", methods=["POST"])
@login_required
def appointment_update_status(apt_id):
    new_status = request.form.get("status")
    if new_status:
        execute_db("UPDATE appointments SET status = ? WHERE id = ?", (new_status, apt_id))
        flash(f"Appointment status updated to {new_status}.", "info")
    return redirect(url_for("appointments_index"))

@app.route("/appointments/queue")
@login_required
def appointments_queue():
    """Live auto-refreshing OPD waiting room token display."""
    today_str = date.today().strftime("%Y-%m-%d")
    queue = query_db(
        """SELECT a.*, p.first_name, p.last_name, p.patient_uid, u.full_name as doctor_name, d.name as department_name, f.name as facility_name
           FROM appointments a
           JOIN patients p ON a.patient_id = p.id
           JOIN users u ON a.doctor_id = u.id
           LEFT JOIN departments d ON a.department_id = d.id
           LEFT JOIN facilities f ON a.facility_id = f.id
           WHERE a.appointment_date = ? AND a.status != 'Cancelled'
           ORDER BY a.token_number ASC""",
        (today_str,)
    )
    current_serving = next((q for q in queue if q["status"] == "In Consultation"), None)
    next_up = [q for q in queue if q["status"] in ("Booked", "Checked-in")]

    return render_template(
        "appointments/queue.html",
        queue=queue,
        current_serving=current_serving,
        next_up=next_up,
        today_date=today_str
    )


# -----------------------------------------------------------------------------
# 11. WARDS & BED MATRIX
# -----------------------------------------------------------------------------

@app.route("/wards")
@login_required
def wards_index():
    facility_filter = request.args.get("facility_id", "").strip()

    sql = "SELECT w.*, f.name as facility_name, f.tier_type FROM wards w JOIN facilities f ON w.facility_id = f.id WHERE 1=1"
    params = []
    if facility_filter:
        sql += " AND w.facility_id = ?"
        params.append(facility_filter)
    sql += " ORDER BY f.id, w.name"
    wards = query_db(sql, params)

    for w in wards:
        beds = query_db(
            """SELECT b.*, adm.admission_number, adm.admitted_at, p.first_name, p.last_name, p.patient_uid, p.village, p.abha_id, u.full_name as doctor_name
               FROM beds b
               LEFT JOIN admissions adm ON b.current_admission_id = adm.id
               LEFT JOIN patients p ON adm.patient_id = p.id
               LEFT JOIN users u ON adm.doctor_id = u.id
               WHERE b.ward_id = ?
               ORDER BY b.bed_number""",
            (w["id"],)
        )
        w["beds"] = beds
        w["available_count"] = sum(1 for b in beds if b["status"] == "Available")
        w["occupied_count"] = sum(1 for b in beds if b["status"] == "Occupied")
        w["maintenance_count"] = sum(1 for b in beds if b["status"] == "Maintenance")

    facilities = query_db("SELECT id, name, tier_type FROM facilities ORDER BY id ASC")
    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients WHERE status != 'Inpatient' ORDER BY first_name")
    doctors = query_db("SELECT id, full_name FROM users WHERE role IN ('doctor', 'medical_officer') ORDER BY full_name")

    return render_template(
        "wards/index.html",
        wards=wards,
        facilities=facilities,
        patients=patients,
        doctors=doctors,
        facility_filter=facility_filter
    )

@app.route("/wards/admit", methods=["POST"], endpoint="ward_admit")
@app.route("/wards/admit/patient", methods=["POST"], endpoint="ward_admit_patient")
@login_required
def ward_admit():
    patient_id = request.form.get("patient_id")
    bed_id = request.form.get("bed_id")
    doctor_id = request.form.get("doctor_id")
    reason = request.form.get("admission_reason", "").strip()

    bed = query_db("SELECT b.*, w.facility_id FROM beds b JOIN wards w ON b.ward_id = w.id WHERE b.id = ?", (bed_id,), one=True)
    if not bed or bed["status"] != "Available":
        flash("Bed is no longer available.", "danger")
        return redirect(url_for("wards_index"))

    count_adm = query_db("SELECT COUNT(*) as c FROM admissions", one=True)["c"]
    adm_num = f"ADM-{date.today().year}-{(count_adm + 1):04d}"

    adm_id = execute_db(
        """INSERT INTO admissions (admission_number, patient_id, bed_id, facility_id, doctor_id, admitted_at, admission_reason, status)
           VALUES (?, ?, ?, ?, ?, datetime('now'), ?, 'Admitted')""",
        (adm_num, patient_id, bed_id, bed["facility_id"], doctor_id, reason)
    )

    execute_db("UPDATE beds SET status = 'Occupied', current_admission_id = ? WHERE id = ?", (adm_id, bed_id))
    execute_db("UPDATE patients SET status = 'Inpatient' WHERE id = ?", (patient_id,))

    flash(f"Patient admitted successfully! Admission #{adm_num}.", "success")
    return redirect(url_for("wards_index"))

@app.route("/wards/discharge/<int:adm_id>", methods=["POST"])
@login_required
def ward_discharge(adm_id):
    discharge_summary = request.form.get("discharge_summary", "").strip()
    discharge_condition = request.form.get("discharge_condition", "Recovered / Stable").strip()

    adm = query_db("SELECT * FROM admissions WHERE id = ?", (adm_id,), one=True)
    if not adm:
        flash("Admission record not found.", "danger")
        return redirect(url_for("wards_index"))

    execute_db(
        """UPDATE admissions
           SET status = 'Discharged', discharged_at = datetime('now'), discharge_summary = ?, discharge_condition = ?
           WHERE id = ?""",
        (discharge_summary, discharge_condition, adm_id)
    )

    execute_db("UPDATE beds SET status = 'Available', current_admission_id = NULL WHERE id = ?", (adm["bed_id"],))
    execute_db("UPDATE patients SET status = 'Discharged' WHERE id = ?", (adm["patient_id"],))

    flash(f"Patient discharged from Admission #{adm['admission_number']}.", "success")
    return redirect(url_for("wards_index"))

@app.route("/wards/bed/<int:bed_id>/toggle-maintenance", methods=["POST"])
@login_required
def toggle_bed_maintenance(bed_id):
    bed = query_db("SELECT * FROM beds WHERE id = ?", (bed_id,), one=True)
    if bed:
        new_status = "Available" if bed["status"] == "Maintenance" else "Maintenance"
        execute_db("UPDATE beds SET status = ? WHERE id = ?", (new_status, bed_id))
        flash(f"Bed #{bed['bed_number']} status changed to {new_status}.", "info")
    return redirect(url_for("wards_index"))


# -----------------------------------------------------------------------------
# 12. PHARMACY & DISPENSING
# -----------------------------------------------------------------------------

@app.route("/pharmacy")
@login_required
def pharmacy_catalog():
    query_param = request.args.get("q", "").strip()
    category_param = request.args.get("category", "").strip()
    stock_status = request.args.get("stock", "").strip()

    sql = "SELECT * FROM medicines WHERE 1=1"
    params = []
    if query_param:
        sql += " AND (brand_name LIKE ? OR generic_name LIKE ? OR code LIKE ?)"
        term = f"%{query_param}%"
        params.extend([term, term, term])
    if category_param:
        sql += " AND category = ?"
        params.append(category_param)
    if stock_status == "low":
        sql += " AND stock_quantity <= reorder_level AND stock_quantity > 0"
    elif stock_status == "out":
        sql += " AND stock_quantity = 0"

    sql += " ORDER BY is_essential_life_saving DESC, brand_name ASC"
    medicines = query_db(sql, params)
    categories = query_db("SELECT DISTINCT category FROM medicines ORDER BY category")

    # Pending prescriptions for dispensing
    pending_prescriptions = query_db(
        """SELECT pr.*, p.first_name, p.last_name, p.patient_uid, p.village, p.abha_id, u.full_name as doctor_name
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

    return render_template(
        "pharmacy/index.html",
        medicines=medicines,
        categories=categories,
        pending_prescriptions=pending_prescriptions,
        query=query_param,
        category_filter=category_param,
        stock_status=stock_status
    )

@app.route("/pharmacy/dispense/<int:rx_id>", methods=["POST"])
@login_required
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

    execute_db("UPDATE prescriptions SET status = 'Dispensed' WHERE id = ?", (rx_id,))
    flash(f"Prescription {rx['prescription_number']} dispensed successfully!", "success")
    return redirect(url_for("pharmacy_catalog"))

@app.route("/pharmacy/medicine/new", methods=["POST"])
@login_required
def medicine_create():
    brand_name = request.form.get("brand_name", "").strip()
    generic_name = request.form.get("generic_name", "").strip()
    category = request.form.get("category", "").strip()
    form_type = request.form.get("form", "Tablet")
    strength = request.form.get("strength", "").strip()
    unit_price = float(request.form.get("unit_price", 0.0) or 0.0)
    stock_quantity = int(request.form.get("stock_quantity", 0) or 0)
    reorder_level = int(request.form.get("reorder_level", 20) or 20)
    batch_number = request.form.get("batch_number", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()
    location_rack = request.form.get("location_rack", "").strip()
    manufacturer = request.form.get("manufacturer", "").strip()

    if not brand_name or not generic_name:
        flash("Brand name and generic name are required.", "danger")
        return redirect(url_for("pharmacy_catalog"))

    import uuid
    code = f"MED-{uuid.uuid4().hex[:6].upper()}"

    execute_db(
        """INSERT INTO medicines (code, brand_name, generic_name, category, form, strength, unit_price, stock_quantity, reorder_level, batch_number, expiry_date, location_rack, manufacturer, is_essential_life_saving, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))""",
        (code, brand_name, generic_name, category, form_type, strength, unit_price, stock_quantity, reorder_level, batch_number, expiry_date, location_rack, manufacturer)
    )
    flash(f"Medicine '{brand_name}' added to inventory.", "success")
    return redirect(url_for("pharmacy_catalog"))


# -----------------------------------------------------------------------------
# 13. LABORATORY & DIAGNOSTICS
# -----------------------------------------------------------------------------

@app.route("/laboratory")
@login_required
def laboratory_index():
    status_filter = request.args.get("status", "").strip()
    sql = """
        SELECT lo.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.village, p.abha_id,
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

    test_catalog = query_db("SELECT * FROM lab_tests_catalog ORDER BY category, name")
    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id FROM patients ORDER BY first_name")
    doctors = query_db("SELECT id, full_name, specialization FROM users WHERE role IN ('doctor', 'medical_officer') ORDER BY full_name")

    return render_template(
        "laboratory/index.html",
        orders=orders,
        status_filter=status_filter,
        test_catalog=test_catalog,
        patients=patients,
        doctors=doctors
    )

@app.route("/laboratory/new", methods=["POST"])
@login_required
def lab_order_create():
    """Create a new diagnostic lab order from the modal form."""
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    clinical_notes = request.form.get("clinical_notes", "")
    test_ids = request.form.getlist("test_ids[]")

    if not patient_id or not doctor_id or not test_ids:
        flash("Patient, doctor, and at least one test are required.", "danger")
        return redirect(url_for("laboratory_index"))

    import uuid
    order_number = f"LAB-{uuid.uuid4().hex[:6].upper()}"
    facility_id = g.user.get("facility_id") if g.user else None

    execute_db(
        """INSERT INTO lab_orders (order_number, patient_id, doctor_id, facility_id, status, clinical_notes, ordered_at)
           VALUES (?, ?, ?, ?, 'Ordered', ?, datetime('now'))""",
        (order_number, patient_id, doctor_id, facility_id, clinical_notes)
    )
    order_id = query_db("SELECT last_insert_rowid() as id", one=True)["id"]

    for test_id in test_ids:
        execute_db(
            "INSERT INTO lab_order_items (lab_order_id, test_id, status) VALUES (?, ?, 'Pending')",
            (order_id, test_id)
        )

    flash(f"Lab order {order_number} created successfully.", "success")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/order/<int:order_id>/collect", methods=["POST"])
@login_required
def lab_sample_collect(order_id):
    execute_db("UPDATE lab_orders SET status = 'Sample Collected', sample_collected_at = datetime('now') WHERE id = ?", (order_id,))
    flash("Specimen collected and sent to diagnostic bench.", "info")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/item/<int:item_id>/results", methods=["POST"])
@login_required
def lab_result_entry(item_id):
    param_names = request.form.getlist("param_name[]")
    param_values = request.form.getlist("param_value[]")
    param_units = request.form.getlist("param_unit[]")
    param_ranges = request.form.getlist("param_range[]")
    param_flags = request.form.getlist("param_flag[]")
    interpretation = request.form.get("interpretation", "").strip()

    results = []
    for i in range(len(param_names)):
        if param_names[i]:
            results.append({
                "parameter": param_names[i],
                "value": param_values[i],
                "unit": param_units[i],
                "reference_range": param_ranges[i],
                "flag": param_flags[i] if i < len(param_flags) else "Normal"
            })

    execute_db(
        """UPDATE lab_order_items
           SET status = 'Completed', results_json = ?, interpretation = ?, technician_id = ?, verified_by_id = ?, performed_at = datetime('now')
           WHERE id = ?""",
        (json.dumps(results), interpretation, session.get("user_id"), session.get("user_id"), item_id)
    )

    item = query_db("SELECT * FROM lab_order_items WHERE id = ?", (item_id,), one=True)
    if item:
        pending = query_db("SELECT COUNT(*) as c FROM lab_order_items WHERE lab_order_id = ? AND status != 'Completed'", (item["lab_order_id"],), one=True)["c"]
        if pending == 0:
            execute_db("UPDATE lab_orders SET status = 'Completed', completed_at = datetime('now') WHERE id = ?", (item["lab_order_id"],))

    flash("Diagnostic test results verified successfully!", "success")
    return redirect(url_for("laboratory_index"))

@app.route("/laboratory/report/<int:order_id>")
@login_required
def lab_report_view(order_id):
    order = query_db(
        """SELECT lo.*, p.first_name, p.last_name, p.patient_uid, p.gender, p.dob, p.phone, p.village, p.abha_id,
                  u.full_name as doctor_name, u.specialization as doctor_spec
           FROM lab_orders lo
           JOIN patients p ON lo.patient_id = p.id
           JOIN users u ON lo.doctor_id = u.id
           WHERE lo.id = ?""",
        (order_id,),
        one=True
    )
    if not order:
        flash("Lab order not found.", "danger")
        return redirect(url_for("laboratory_index"))

    items = query_db(
        """SELECT loi.*, ltc.code as test_code, ltc.name as test_name, ltc.category as test_category, ltc.specimen_type,
                  u_tech.full_name as technician_name, u_ver.full_name as verified_by_name
           FROM lab_order_items loi
           JOIN lab_tests_catalog ltc ON loi.test_id = ltc.id
           LEFT JOIN users u_tech ON loi.technician_id = u_tech.id
           LEFT JOIN users u_ver ON loi.verified_by_id = u_ver.id
           WHERE loi.lab_order_id = ?""",
        (order_id,)
    )
    return render_template("laboratory/report.html", order=order, items=items)


# -----------------------------------------------------------------------------
# 14. BILLING & PUBLIC HEALTH SCHEMES (PM-JAY CASHLESS)
# -----------------------------------------------------------------------------

@app.route("/billing", methods=["GET"])
@login_required
def billing_index():
    invoices = query_db(
        """SELECT inv.*, p.first_name, p.last_name, p.patient_uid, p.phone, p.village, p.abha_id, p.socioeconomic_category, f.name as facility_name
           FROM invoices inv
           JOIN patients p ON inv.patient_id = p.id
           LEFT JOIN facilities f ON inv.facility_id = f.id
           ORDER BY inv.created_at DESC"""
    )
    patients = query_db("SELECT id, patient_uid, first_name, last_name, village, abha_id, socioeconomic_category FROM patients ORDER BY first_name")

    # Compute billing KPI aggregates
    totals = query_db(
        "SELECT COALESCE(SUM(total_amount),0) as billed, COALESCE(SUM(amount_paid),0) as collected FROM invoices",
        one=True
    )
    total_billed = totals["billed"] if totals else 0.0
    total_collected = totals["collected"] if totals else 0.0
    total_outstanding = total_billed - total_collected

    return render_template(
        "billing/index.html",
        invoices=invoices,
        patients=patients,
        total_billed=total_billed,
        total_collected=total_collected,
        total_outstanding=total_outstanding
    )

@app.route("/billing/new", methods=["POST"])
@login_required
def billing_create_invoice():
    """Create a new itemized invoice from the modal form."""
    patient_id = request.form.get("patient_id")
    payment_method = request.form.get("payment_method", "Cash")
    tax_percent = float(request.form.get("tax_percent", 5.0))
    discount_amount = float(request.form.get("discount_amount", 0.0))
    amount_paid = float(request.form.get("amount_paid", 0.0))
    notes = request.form.get("notes", "")

    item_types = request.form.getlist("item_type[]")
    descriptions = request.form.getlist("description[]")
    quantities = request.form.getlist("quantity[]")
    unit_prices = request.form.getlist("unit_price[]")

    if not patient_id or not item_types:
        flash("Patient and at least one billing line item are required.", "danger")
        return redirect(url_for("billing_index"))

    # Compute totals
    subtotal = sum(float(q) * float(p) for q, p in zip(quantities, unit_prices) if q and p)
    tax_amount = round(subtotal * tax_percent / 100, 2)
    total_amount = round(subtotal + tax_amount - discount_amount, 2)
    status = "Paid" if amount_paid >= total_amount else ("Partially Paid" if amount_paid > 0 else "Pending")

    import uuid
    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
    facility_id = g.user.get("facility_id") if g.user else None

    execute_db(
        """INSERT INTO invoices (invoice_number, patient_id, facility_id, subtotal, tax_percent, tax_amount,
           discount_amount, total_amount, amount_paid, status, payment_method, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (invoice_number, patient_id, facility_id, subtotal, tax_percent, tax_amount,
         discount_amount, total_amount, amount_paid, status, payment_method, notes)
    )
    invoice_id = query_db("SELECT last_insert_rowid() as id", one=True)["id"]

    for i_type, desc, qty, price in zip(item_types, descriptions, quantities, unit_prices):
        if desc and qty and price:
            line_total = float(qty) * float(price)
            execute_db(
                "INSERT INTO invoice_items (invoice_id, item_type, description, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?, ?)",
                (invoice_id, i_type, desc, float(qty), float(price), line_total)
            )

    flash(f"Invoice {invoice_number} generated successfully.", "success")
    return redirect(url_for("invoice_view", invoice_id=invoice_id))

@app.route("/billing/invoice/<int:invoice_id>")
@login_required
def invoice_view(invoice_id):
    invoice = query_db(
        """SELECT inv.*, p.first_name, p.last_name, p.patient_uid, p.phone, p.email, p.address, p.village, p.abha_id,
                  p.socioeconomic_category, p.insurance_provider, p.insurance_policy_number,
                  f.name as facility_name, f.district
           FROM invoices inv
           JOIN patients p ON inv.patient_id = p.id
           LEFT JOIN facilities f ON inv.facility_id = f.id
           WHERE inv.id = ?""",
        (invoice_id,),
        one=True
    )
    if not invoice:
        flash("Invoice record not found.", "danger")
        return redirect(url_for("billing_index"))

    items = query_db("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    return render_template("billing/invoice.html", invoice=invoice, items=items)

@app.route("/billing/invoice/<int:invoice_id>/pay", methods=["POST"])
@login_required
def billing_record_payment(invoice_id):
    pay_amount = float(request.form.get("pay_amount", 0.0) or 0.0)
    payment_method = request.form.get("payment_method", "Cash")

    inv = query_db("SELECT * FROM invoices WHERE id = ?", (invoice_id,), one=True)
    if not inv:
        flash("Invoice not found.", "danger")
        return redirect(url_for("billing_index"))

    new_paid = inv["amount_paid"] + pay_amount
    new_status = "Paid" if new_paid >= inv["total_amount"] else "Partially Paid"

    execute_db(
        """UPDATE invoices
           SET amount_paid = ?, status = ?, payment_method = ?, paid_at = datetime('now')
           WHERE id = ?""",
        (new_paid, new_status, payment_method, invoice_id)
    )
    flash(f"Payment of ${pay_amount:.2f} recorded successfully for Invoice {inv['invoice_number']}.", "success")
    return redirect(url_for("invoice_view", invoice_id=invoice_id))


# -----------------------------------------------------------------------------
# 15. AUDIT TRAIL & SYSTEM SETTINGS
# -----------------------------------------------------------------------------

@app.route("/audit-logs")
@login_required
@roles_accepted("admin")
def audit_logs_view():
    logs = query_db(
        """SELECT a.*, u.full_name as user_name, u.role as user_role, f.name as facility_name
           FROM audit_logs a
           LEFT JOIN users u ON a.user_id = u.id
           LEFT JOIN facilities f ON a.facility_id = f.id
           ORDER BY a.timestamp DESC LIMIT 200"""
    )
    return render_template("settings/audit_logs.html", logs=logs)

@app.route("/settings", methods=["GET", "POST"])
@login_required
@roles_accepted("admin")
def settings_view():
    if request.method == "POST":
        for k, v in request.form.items():
            set_setting(k, v.strip())
        flash("Hospital settings updated successfully.", "success")
        return redirect(url_for("settings_view"))

    settings_rows = query_db("SELECT key, value FROM hospital_settings")
    settings = {r["key"]: r["value"] for r in settings_rows} if settings_rows else {}
    facilities = query_db("SELECT * FROM facilities ORDER BY id ASC")
    return render_template("settings/index.html", facilities=facilities, settings=settings)

@app.route("/staff")
@login_required
@roles_accepted("admin")
def staff_index():
    staff = query_db(
        """SELECT u.*, d.name as department_name, f.name as facility_name, f.tier_type as facility_tier
           FROM users u
           LEFT JOIN departments d ON u.department_id = d.id
           LEFT JOIN facilities f ON u.facility_id = f.id
           ORDER BY u.id ASC"""
    )
    departments = query_db("SELECT id, name FROM departments ORDER BY name")
    facilities = query_db("SELECT id, name, tier_type FROM facilities ORDER BY id")
    return render_template("staff/index.html", staff=staff, departments=departments, facilities=facilities)

@app.route("/staff/new", methods=["POST"])
@login_required
@roles_accepted("admin")
def staff_create():
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "password123").strip()
    role = request.form.get("role", "doctor")
    department_id = request.form.get("department_id") or None
    facility_id = request.form.get("facility_id") or session.get("facility_id") or 1
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    specialization = request.form.get("specialization", "").strip()
    license_number = request.form.get("license_number", "").strip()
    consultation_fee = float(request.form.get("consultation_fee", 0.0) or 0.0)

    if not full_name or not username:
        flash("Full name and username are required.", "danger")
        return redirect(url_for("staff_index"))

    existing = query_db("SELECT id FROM users WHERE username = ?", (username,), one=True)
    if existing:
        flash(f"Username '{username}' already exists.", "danger")
        return redirect(url_for("staff_index"))

    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash(password)

    execute_db(
        """INSERT INTO users (username, password_hash, full_name, email, phone, role, facility_id, department_id, specialization, license_number, consultation_fee, is_active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))""",
        (username, pwd_hash, full_name, email, phone, role, facility_id, department_id, specialization, license_number, consultation_fee)
    )
    flash(f"Staff member '{full_name}' ({role}) registered successfully.", "success")
    return redirect(url_for("staff_index"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

