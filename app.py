"""CyberShield SMB Flask application entry point."""

import json
import hashlib
import hmac
import os
import re
import secrets
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from functools import wraps
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from ai.assistant import DISCLAIMER, answer_question
from ai.business_classifier import interpret_description, matched_keywords
from ai.openai_assistant import get_openai_response
from data.questions import ASSESSMENT_CATEGORIES, all_questions
from data.sectors import FRAMEWORKS, INTAKE_QUESTIONS, SECTORS, get_sector
from database import AssessmentHistory, AssessmentSession, AuthRateLimitEvent, PrivacyConsent, User, db, init_database
from engine.classifier import classify_business
from engine.risk_engine import calculate_assessment
from engine.sector_engine import calculate_sector, describe_sources, sector_history_row
from utils.recommendations import generate_recommendations

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CYBERSHIELD_SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("CYBERSHIELD_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
if os.environ.get("CYBERSHIELD_TRUST_PROXY", "false").lower() in {"1", "true", "yes"}:
    # Behind Render's load balancer the real visitor IP arrives in X-Forwarded-For.
    # Without this every visitor looks like the proxy and shares one rate-limit bucket.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
init_database(app)


PRIVACY_NOTICE_VERSION = "1.1"
PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 1024
AUTH_WINDOW = timedelta(minutes=15)
LOCAL_TZ = ZoneInfo("Australia/Melbourne")
CHAT_WINDOW = timedelta(minutes=15)
CHAT_MAX_MESSAGE_LENGTH = 1000
CHAT_PER_VISITOR_LIMIT = int(os.environ.get("CYBERSHIELD_CHAT_LIMIT", "20"))
CHAT_DAILY_CAP = int(os.environ.get("CYBERSHIELD_AI_DAILY_CAP", "300"))


def _to_local(moment):
    """Convert a stored UTC timestamp (SQLite returns it naive) to Melbourne time for display."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LOCAL_TZ)


def _pack_result(core_form, assessment_date, sector_id=None, sector_form=None, confidence=None):
    """Keep only the answers in the session cookie; everything else is recalculated on demand.

    The scoring is rule-based and deterministic, so recalculating always gives the same result.
    This keeps the cookie far below the browser's size limit even with sector questions added.
    """
    packed = {
        "v": 2,
        "core": "".join(
            "1" if str(core_form.get(question["id"], "no")).lower() == "yes" else "0"
            for question in all_questions()
        ),
        "date": assessment_date,
    }
    sector = get_sector(sector_id) if sector_id else None
    if sector is not None:
        packed["sector"] = sector["id"]
        packed["sbits"] = "".join(
            "1" if str((sector_form or {}).get(question["id"], "no")).lower() == "yes" else "0"
            for question in sector["questions"]
        )
        if confidence is not None:
            packed["conf"] = confidence
    return packed


def _load_result():
    """Rebuild the full result (scores, summary, recommendations) from the session."""
    stored = session.get("assessment_result")
    if not stored:
        return None
    if "score" in stored:
        # A result saved by an earlier version of the app, already in full form.
        stored.setdefault("sector", None)
        return stored
    questions = all_questions()
    bits = stored.get("core", "")
    if len(bits) != len(questions):
        return None
    result = calculate_assessment({
        question["id"]: "yes" if bit == "1" else "no" for question, bit in zip(questions, bits)
    })
    result["recommendations"] = generate_recommendations(result["answers"])
    result["assessment_date"] = stored.get("date", "")
    result["sector"] = None
    sector = get_sector(stored.get("sector"))
    sector_bits = stored.get("sbits", "")
    if sector is not None and len(sector_bits) == len(sector["questions"]):
        result["sector"] = calculate_sector(sector["id"], {
            question["id"]: "yes" if bit == "1" else "no"
            for question, bit in zip(sector["questions"], sector_bits)
        })
        result["sector"]["confidence"] = stored.get("conf")
    return result


def _csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_auth_context():
    return {"csrf_token": _csrf_token(), "authenticated_email": session.get("user_email")}


def _valid_csrf():
    sent = request.form.get("csrf_token", "")
    expected = session.get("_csrf_token", "")
    return bool(sent and expected and hmac.compare_digest(sent, expected))


def _validate_credentials(email, password):
    if not isinstance(email, str) or not isinstance(password, str):
        return "Email and password are required."
    email = email.strip().lower()
    if len(email) > 320 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return "Enter a valid email address."
    if not password or len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be between {PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters."
    return {"email": email, "password": password}


def _auth_payload(require_consent=False):
    if not request.is_json:
        return None, (jsonify({"error": "Send credentials as JSON."}), 415)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "Request body must be a JSON object."}), 400)
    credentials = _validate_credentials(payload.get("email"), payload.get("password"))
    if isinstance(credentials, str):
        return None, (jsonify({"error": credentials}), 400)
    if len(credentials["password"]) < PASSWORD_MIN_LENGTH:
        return None, (jsonify({"error": f"Password must be at least {PASSWORD_MIN_LENGTH} characters."}), 400)
    if require_consent and payload.get("privacy_consent") is not True:
        return None, (jsonify({"error": "Privacy notice consent is required to create an account."}), 400)
    return credentials, None


def _rate_key(scope, value):
    secret = str(app.config["SECRET_KEY"]).encode("utf-8")
    return hmac.new(secret, f"{scope}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _rate_limit_hit(action, email):
    """Throttle repeated auth attempts while storing no raw IP or email in the limiter table."""
    now = datetime.now(timezone.utc)
    cutoff = now - AUTH_WINDOW
    db.session.query(AuthRateLimitEvent).filter(AuthRateLimitEvent.created_at < now - timedelta(days=1)).delete(
        synchronize_session=False
    )
    remote = request.remote_addr or "unknown"
    keys = [(_rate_key("auth-ip", f"{action}:{remote}"), 30)]
    if email:
        keys.append((_rate_key("auth-subject", f"{action}:{remote}:{email}"), 5 if action == "login" else 8))
    for key, limit in keys:
        attempts = db.session.query(AuthRateLimitEvent.id).filter(
            AuthRateLimitEvent.key_hash == key,
            AuthRateLimitEvent.created_at >= cutoff,
        ).count()
        if attempts >= limit:
            db.session.commit()
            return True
    db.session.add_all([AuthRateLimitEvent(key_hash=key, created_at=now) for key, _ in keys])
    db.session.commit()
    return False


def _password_is_breached(password):
    """Check HIBP Pwned Passwords by k-anonymity; the password is never sent."""
    import certifi

    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    req = urllib.request.Request(
        f"https://api.pwnedpasswords.com/range/{digest[:5]}",
        headers={"User-Agent": "CyberShield-SMB/2.0", "Add-Padding": "true"},
    )
    try:
        tls_context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=12, context=tls_context) as response:
            suffixes = response.read(2_000_000).decode("ascii")
    except (urllib.error.URLError, TimeoutError, UnicodeError, OSError):
        return None
    target = digest[5:]
    for line in suffixes.splitlines():
        suffix, separator, count = line.partition(":")
        if separator and suffix.upper() == target:
            try:
                return int(count) > 0
            except ValueError:
                return None
    return False


def _create_account(email, password):
    if _rate_limit_hit("register", email):
        return None, "Too many account attempts. Please try again in 15 minutes.", 429
    breached = _password_is_breached(password)
    if breached is None:
        return None, "Password safety checking is temporarily unavailable. Please try again shortly.", 503
    if breached:
        return None, "Choose a password that has not appeared in known data breaches.", 400
    user = User(email=email, password_hash=generate_password_hash(password, method="scrypt"))
    db.session.add(user)
    try:
        db.session.flush()
        db.session.add(PrivacyConsent(user_id=user.id, notice_version=PRIVACY_NOTICE_VERSION))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "An account with that email already exists.", 409
    return user, None, None


def _authenticate(email, password):
    if _rate_limit_hit("login", email):
        return None, "Too many sign-in attempts. Please try again in 15 minutes.", 429
    user = db.session.scalar(db.select(User).where(User.email == email))
    if user is None or not check_password_hash(user.password_hash, password):
        return None, "Email or password is incorrect.", 401
    return user, None, None


def _persist_current_assessment(user_id):
    """Save aggregate scores only; raw question answers are never written to the database."""
    result = _load_result()
    if not result or session.get("assessment_owner_user_id") is not None:
        return False
    sector = result.get("sector")
    category_scores = list(result["category_scores"])
    recommendations = list(result["recommendations"])
    if sector:
        # Stored beside the core rows (flagged "sector") so the existing tables need no migration.
        category_scores.append(sector_history_row(sector))
        recommendations.extend(sector["recommendations"])
    came_from_guest = session.get("assessment_origin_guest", True)
    created_at = session.get("assessment_result_created_at")
    if created_at:
        try:
            created_at = datetime.fromisoformat(created_at)
        except (TypeError, ValueError):
            created_at = None
    record = AssessmentSession(
        user_id=user_id,
        business_type=sector["id"] if sector else None,
        overall_score=result["score"],
        risk_tier=result["risk"],
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(record)
    db.session.flush()
    db.session.add(AssessmentHistory(
        session_id=record.id,
        category_scores=category_scores,
        recommendations=recommendations,
        created_at=record.created_at,
    ))
    db.session.commit()
    session["assessment_owner_user_id"] = user_id
    session["assessment_origin_guest"] = came_from_guest
    if "score" in session["assessment_result"]:
        # Older full-form session results: drop the raw answers once saved.
        session["assessment_result"] = {key: value for key, value in result.items() if key != "answers"}
    return True


def _establish_login(user):
    """Start a fresh authenticated session while retaining an unclaimed guest result."""
    old_owner = session.get("assessment_owner_user_id")
    keep_guest_result = old_owner is None
    guest_result = session.get("assessment_result") if keep_guest_result else None
    result_created_at = session.get("assessment_result_created_at") if keep_guest_result else None
    session.clear()
    session["_csrf_token"] = secrets.token_urlsafe(32)
    session["user_id"] = user.id
    session["user_email"] = user.email
    if guest_result is not None:
        session["assessment_result"] = guest_result
        session["assessment_origin_guest"] = True
        if result_created_at:
            session["assessment_result_created_at"] = result_created_at
    else:
        session["assessment_origin_guest"] = False
    imported = _persist_current_assessment(user.id)
    return imported


def _end_login_session():
    """End account access while returning a carried guest result to guest mode."""
    keep_guest_result = session.get("assessment_origin_guest") is True
    guest_result = session.get("assessment_result") if keep_guest_result else None
    created_at = session.get("assessment_result_created_at") if keep_guest_result else None
    owner_id = session.get("assessment_owner_user_id") if keep_guest_result else None
    session.clear()
    session["_csrf_token"] = secrets.token_urlsafe(32)
    if guest_result is not None:
        session["assessment_result"] = guest_result
        session["assessment_origin_guest"] = True
        if owner_id is not None:
            session["assessment_owner_user_id"] = owner_id
        if created_at:
            session["assessment_result_created_at"] = created_at


def _current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None:
        session.pop("user_id", None)
        session.pop("user_email", None)
    return user


def _login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if _current_user() is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for("login_form"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register_form():
    if request.method == "GET":
        return render_template("auth.html", mode="register")
    if not _valid_csrf():
        abort(400)
    credentials = _validate_credentials(request.form.get("email"), request.form.get("password"))
    if isinstance(credentials, str):
        return render_template("auth.html", mode="register", error=credentials), 400
    if len(credentials["password"]) < PASSWORD_MIN_LENGTH:
        return render_template("auth.html", mode="register", error=f"Password must be at least {PASSWORD_MIN_LENGTH} characters."), 400
    if request.form.get("privacy_consent") != "yes":
        return render_template("auth.html", mode="register", error="Please review and accept the privacy notice to create an account."), 400
    user, error, status = _create_account(credentials["email"], credentials["password"])
    if error:
        return render_template("auth.html", mode="register", error=error, email=credentials["email"]), status
    _establish_login(user)
    return redirect(url_for("result" if session.get("assessment_result") else "assessment"))


@app.route("/login", methods=["GET", "POST"])
def login_form():
    if request.method == "GET":
        return render_template("auth.html", mode="login")
    if not _valid_csrf():
        abort(400)
    credentials = _validate_credentials(request.form.get("email"), request.form.get("password"))
    if isinstance(credentials, str):
        return render_template("auth.html", mode="login", error=credentials), 400
    user, error, status = _authenticate(credentials["email"], credentials["password"])
    if error:
        return render_template("auth.html", mode="login", error=error, email=credentials["email"]), status
    _establish_login(user)
    return redirect(url_for("result" if session.get("assessment_result") else "assessment"))


@app.post("/logout")
def logout_form():
    if not _valid_csrf():
        abort(400)
    _end_login_session()
    return redirect(url_for("home"))


@app.route("/api/auth/register", methods=["POST"])
def register():
    """Create an account and carry an optional guest result into its history."""
    payload, error = _auth_payload(require_consent=True)
    if error:
        return error
    user, error_message, status = _create_account(payload["email"], payload["password"])
    if error_message:
        return jsonify({"error": error_message}), status
    imported = _establish_login(user)
    return jsonify({"id": user.id, "email": user.email, "assessment_imported": imported}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticate and add the user identity to the existing Flask session."""
    payload, error = _auth_payload()
    if error:
        return error
    user, error_message, status = _authenticate(payload["email"], payload["password"])
    if error_message:
        return jsonify({"error": error_message}), status
    imported = _establish_login(user)
    return jsonify({"id": user.id, "email": user.email, "assessment_imported": imported})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Sign out of the JSON API session."""
    if not request.is_json:
        return jsonify({"error": "Send a JSON request."}), 415
    _end_login_session()
    return jsonify({"status": "logged_out"})


@app.route("/api/auth/me", methods=["GET"])
def current_user():
    """Return the authenticated account associated with this browser session."""
    user = _current_user()
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    return jsonify({"id": user.id, "email": user.email})


ERROR_PAGES = {
    400: ("bi-arrow-repeat", "This form has expired",
          "For your security, forms stop working after a while or when opened in another tab. Go back, refresh the page and try again."),
    404: ("bi-signpost-split", "Page not found",
          "The page you were looking for does not exist or has moved."),
    500: ("bi-tools", "Something went wrong on our side",
          "The error has been logged. Your saved results are safe. Please try again in a moment."),
}


def _error_page(code):
    icon, heading, message = ERROR_PAGES[code]
    return render_template("error.html", code=code, icon=icon, heading=heading, message=message), code


@app.errorhandler(400)
def bad_request(error):
    return _error_page(400)


@app.errorhandler(404)
def not_found(error):
    return _error_page(404)


@app.errorhandler(500)
def server_error(error):
    # Undo any half-finished database work so the next request starts clean.
    try:
        db.session.rollback()
    except Exception:
        pass
    return _error_page(500)


CORE_SOURCES = {question["id"]: describe_sources(question) for question in all_questions()}


def _result_context():
    """Retrieve the latest result while preserving template variables expected by the UI."""
    result = _load_result()
    if result is None:
        return None
    return {
        "sector": result.get("sector"),
        "score": result["score"],
        "risk": result["risk"],
        "assessment_date": result["assessment_date"],
        "category_scores": result["category_scores"],
        "recommendations": result["recommendations"],
        "summary": result["summary"],
        "total_questions": result["total_questions"],
        # Looked up by question id so stored results and cookies do not need to carry sources.
        "core_sources": CORE_SOURCES,
    }


def _history_entries(user_id):
    rows = (
        db.session.query(AssessmentSession, AssessmentHistory)
        .join(AssessmentHistory, AssessmentHistory.session_id == AssessmentSession.id)
        .filter(AssessmentSession.user_id == user_id)
        .order_by(AssessmentSession.created_at.asc(), AssessmentSession.id.asc())
        .all()
    )
    entries = []
    for index, (record, history) in enumerate(rows, start=1):
        local = _to_local(record.created_at)
        # The column is a Float, but the engine only produces whole numbers; show 60, not 60.0.
        score = round(record.overall_score or 0)
        previous_score = entries[-1]["score"] if entries else None
        stored_scores = history.category_scores or []
        sector_row = next((row for row in stored_scores if row.get("sector")), None)
        business = get_sector(record.business_type)
        entries.append({
            "id": record.id,
            "attempt": index,
            "created_at": record.created_at,
            "date_label": local.strftime("%d %b %Y"),
            "time_label": f"{local.strftime('%d %b %Y')}, {local.strftime('%I:%M %p').lstrip('0').lower()}",
            "chart_label": f"#{index} \u00b7 {local.strftime('%d %b')}",
            "score": score,
            "risk_tier": record.risk_tier,
            "delta": None if previous_score is None else score - previous_score,
            "category_scores": [row for row in stored_scores if not row.get("sector")],
            "business_type": business["name"] if business else None,
            "sector_score": sector_row["score"] if sector_row else None,
            "sector_row": sector_row,
            "recommendations": history.recommendations,
        })
    return entries


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", notice_version=PRIVACY_NOTICE_VERSION)


@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    if request.method == "POST":
        _store_new_result(_pack_result(request.form, datetime.now(LOCAL_TZ).strftime("%d %B %Y")))
        return redirect(url_for("result"))

    return render_template("assessment.html", categories=ASSESSMENT_CATEGORIES)


def _store_new_result(packed):
    """Put a freshly submitted result in the session and save it if the visitor is signed in."""
    session["assessment_result"] = packed
    session["assessment_result_created_at"] = datetime.now(timezone.utc).isoformat()
    session.pop("assessment_owner_user_id", None)
    user = _current_user()
    session["assessment_origin_guest"] = user is None
    if user is not None:
        _persist_current_assessment(user.id)


# ---------------------------------------------------------------------------
# Adaptive assessment (Sprint 2): intake -> business type -> core + sector questions.
# The standard /assessment route above is untouched and remains the default guest path.
# ---------------------------------------------------------------------------

def _business_profile():
    profile = session.get("business_profile")
    return profile if isinstance(profile, dict) else None


def _intake_answers_from(profile):
    return {
        question["id"]: option_id
        for question, option_id in zip(INTAKE_QUESTIONS, profile.get("intake", []))
    }


@app.route("/tailored", methods=["GET", "POST"])
def tailored_intake():
    """Step 1: a few questions about the business."""
    if request.method == "GET":
        return render_template("tailored_intake.html", questions=INTAKE_QUESTIONS)
    if not _valid_csrf():
        abort(400)
    chosen = []
    for question in INTAKE_QUESTIONS:
        option_id = request.form.get(question["id"], "")
        if option_id not in {option["id"] for option in question["options"]}:
            return render_template(
                "tailored_intake.html", questions=INTAKE_QUESTIONS, selected=request.form,
                error="Please answer all four questions so we can suggest a business type.",
            ), 400
        chosen.append(option_id)
    description = request.form.get("description", "")
    described_as, source = (None, "none")
    if description.strip():
        # The model only labels the free text. It shares the assistant's spend limits.
        described_as, source = interpret_description(description, allow_ai=_chat_budget_available())
    session["business_profile"] = {
        "intake": chosen,
        "described_as": described_as,
        "source": source,
        "described": bool(description.strip()),
        # Words from our own keyword list that back up the label; the description itself is not kept.
        "evidence": matched_keywords(description, described_as) if described_as else [],
    }
    return redirect(url_for("tailored_confirm"))


@app.route("/tailored/sources")
def tailored_sources():
    """Traceability: every core and sector question with the published frameworks it is based on."""
    core = [
        {
            "name": category["name"],
            "icon": category["icon"],
            "questions": [
                {
                    "question": question["question"],
                    "reason": question["reason"],
                    "functions": question["csf_functions"],
                    "sources": describe_sources(question),
                }
                for question in category["questions"]
            ],
        }
        for category in ASSESSMENT_CATEGORIES
    ]
    sectors = [
        {
            "name": sector["name"],
            "icon": sector["icon"],
            "questions": [
                {"question": question["question"], "reason": question["reason"], "sources": describe_sources(question)}
                for question in sector["questions"]
            ],
        }
        for sector in SECTORS
    ]
    return render_template("tailored_sources.html", core=core, sectors=sectors, frameworks=FRAMEWORKS.values())


def _points_breakdown(outcome):
    """Each business type that received points, with its share, for display on the confirm page."""
    total = sum(outcome["points"].values())
    rows = [
        {
            "id": sector_id,
            "name": get_sector(sector_id)["name"],
            "points": points,
            "share": round(points / total * 100),
        }
        for sector_id, points in outcome["points"].items()
        if points
    ]
    return sorted(rows, key=lambda row: -row["points"])


def _confirm_context(outcome, profile):
    """Everything the confirm page needs. The card is always shown; its content depends on the state."""
    return {
        "outcome": outcome,
        "sectors": SECTORS,
        "profile": profile,
        "suggested": get_sector(outcome["sector"]),
        "described_as": get_sector(outcome["description_sector"]),
        "description_given": bool(profile.get("described")),
        "description_source": profile.get("source"),
        "description_evidence": [str(word) for word in (profile.get("evidence") or [])][:4],
        "breakdown": _points_breakdown(outcome),
    }


@app.route("/tailored/confirm", methods=["GET", "POST"])
def tailored_confirm():
    """Step 2: show the suggested business type and why; the user confirms, changes or skips it."""
    profile = _business_profile()
    if profile is None:
        return redirect(url_for("tailored_intake"))
    outcome = classify_business(_intake_answers_from(profile), profile.get("described_as"))
    if request.method == "POST":
        if not _valid_csrf():
            abort(400)
        choice = request.form.get("sector", "")
        if choice == "core":
            # Core-only fallback: continue with the standard 20 questions.
            session.pop("business_profile", None)
            return redirect(url_for("assessment"))
        if get_sector(choice) is None:
            return render_template(
                "tailored_confirm.html", **_confirm_context(outcome, profile),
                error="Please choose a business type, or continue with the standard questions.",
            ), 400
        profile["sector"] = choice
        # Confidence is recorded only when the answers pointed clearly to the type the owner accepted.
        accepted = outcome["state"] == "clear" and choice == outcome["sector"]
        profile["confidence"] = outcome["confidence"] if accepted else None
        session["business_profile"] = profile
        return redirect(url_for("tailored_assessment"))
    return render_template("tailored_confirm.html", **_confirm_context(outcome, profile))


@app.route("/tailored/assessment", methods=["GET", "POST"])
def tailored_assessment():
    """Step 3: the unchanged 20 core questions plus the questions for the chosen business type."""
    profile = _business_profile()
    sector = get_sector(profile.get("sector")) if profile else None
    if sector is None:
        return redirect(url_for("tailored_intake"))
    if request.method == "POST":
        _store_new_result(_pack_result(
            request.form,
            datetime.now(LOCAL_TZ).strftime("%d %B %Y"),
            sector_id=sector["id"],
            sector_form=request.form,
            confidence=profile.get("confidence"),
        ))
        session.pop("business_profile", None)
        return redirect(url_for("result"))
    return render_template(
        "tailored_assessment.html",
        categories=ASSESSMENT_CATEGORIES,
        sector=sector,
        total_questions=len(all_questions()) + len(sector["questions"]),
    )


@app.route("/result")
def result():
    context = _result_context()
    if context is None:
        return redirect(url_for("assessment"))
    user = _current_user()
    account = {"signed_in": user is not None, "saved": False, "delta": None, "attempts": 0}
    if user is not None and session.get("assessment_owner_user_id") == user.id:
        entries = _history_entries(user.id)
        account["saved"] = bool(entries)
        account["attempts"] = len(entries)
        if len(entries) >= 2:
            account["delta"] = entries[-1]["delta"]
            account["previous_score"] = entries[-2]["score"]
    return render_template("result.html", account=account, **context)


@app.route("/history")
@_login_required
def assessment_history():
    user = _current_user()
    entries = _history_entries(user.id)
    return render_template("history.html", entries=entries, email=user.email)


@app.route("/api/assessment-history")
@_login_required
def assessment_history_api():
    user = _current_user()
    entries = _history_entries(user.id)
    return jsonify({
        "assessments": [
            {
                "id": item["id"],
                "created_at": item["created_at"].isoformat(),
                "score": item["score"],
                "risk_tier": item["risk_tier"],
                "category_scores": item["category_scores"],
                "business_type": item["business_type"],
                "sector_score": item["sector_score"],
            }
            for item in entries
        ]
    })


@app.post("/account/delete")
@_login_required
def delete_account():
    if not _valid_csrf():
        abort(400)
    user = _current_user()
    password = request.form.get("password", "")
    if not check_password_hash(user.password_hash, password):
        entries = _history_entries(user.id)
        return render_template("history.html", entries=entries, email=user.email, delete_error="Password did not match."), 400
    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect(url_for("home"))


@app.route("/assistant", methods=["GET", "POST"])
def chatbot():
    question = ""
    answer = ""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = answer_question(question)
    return render_template("chatbot.html", question=question, answer=answer, disclaimer=DISCLAIMER)


@app.route("/download-report")
def download_report():
    """Create a concise, downloadable PDF report from the latest browser-session result."""
    context = _result_context()
    if context is None:
        return redirect(url_for("assessment"))

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return "PDF reporting requires the ReportLab package. Run: pip install -r requirements.txt", 500

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ShieldTitle", parent=styles["Title"], textColor=colors.HexColor("#0F4C81"), alignment=TA_CENTER, fontSize=23, leading=28))
    styles.add(ParagraphStyle(name="ShieldHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0F4C81"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="ShieldBody", parent=styles["BodyText"], leading=16, textColor=colors.HexColor("#243447")))
    styles.add(ParagraphStyle(name="ShieldSmall", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#526477")))

    story = [
        Paragraph("CyberShield SMB", styles["ShieldTitle"]),
        Paragraph("Cybersecurity Self-Assessment Report", styles["ShieldBody"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Assessment date: {escape(context['assessment_date'])}", styles["ShieldBody"]),
        Spacer(1, 4 * mm),
    ]
    score_table = Table(
        [["Overall security score", "Risk level", "Recommended actions"], [f"{context['score']} / 100", context["risk"], str(len(context["recommendations"]))]],
        colWidths=[58 * mm, 48 * mm, 58 * mm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F7FB")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0F4C81")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 15),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EF")),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([score_table, Paragraph("Executive summary", styles["ShieldHeading"]), Paragraph(escape(context["summary"]["headline"]), styles["ShieldBody"]), Paragraph(escape(context["summary"]["detail"]), styles["ShieldBody"])])

    story.append(Paragraph("Category performance", styles["ShieldHeading"]))
    category_rows = [["Category", "Score", "Safeguards in place"]]
    for category in context["category_scores"]:
        category_rows.append([category["name"], f"{category['score']}%", f"{category['protected']} of {category['total']}"])
    category_table = Table(category_rows, colWidths=[78 * mm, 35 * mm, 51 * mm])
    category_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7F0FA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(category_table)

    sector = context.get("sector")
    if sector:
        story.append(Paragraph(f"Questions for your business type: {escape(sector['name'])}", styles["ShieldHeading"]))
        story.append(Paragraph(
            f"Sector score: {sector['score']}% ({sector['protected']} of {sector['total']} safeguards in place). "
            "This score is reported separately and is not part of the overall score above.",
            styles["ShieldBody"],
        ))
        story.append(Spacer(1, 2.5 * mm))
        for item in sector["recommendations"]:
            story.append(Paragraph(
                f"<b>{escape(item['priority'])} priority</b><br/>{escape(item['description'])}"
                f"<br/><i>Why this is asked: {escape(item['reason'])}</i>",
                styles["ShieldBody"],
            ))
            story.append(Spacer(1, 2.5 * mm))

    story.append(Paragraph("Prioritised action plan", styles["ShieldHeading"]))
    if context["recommendations"]:
        for item in context["recommendations"]:
            story.append(Paragraph(f"<b>{escape(item['priority'])} priority — {escape(item['category'])}</b><br/>{escape(item['description'])}", styles["ShieldBody"]))
            story.append(Spacer(1, 2.5 * mm))
    else:
        story.append(Paragraph("Excellent work — all assessment safeguards were marked as in place. Review your controls regularly to keep them effective.", styles["ShieldBody"]))

    story.extend([Spacer(1, 5 * mm), Paragraph(escape(DISCLAIMER), styles["ShieldSmall"])])
    document.build(story)
    buffer.seek(0)
    safe_date = context["assessment_date"].replace(" ", "-").lower()
    return send_file(buffer, as_attachment=True, download_name=f"cybershield-smb-report-{safe_date}.pdf", mimetype="application/pdf")

def _chat_budget_available():
    """Apply a per-visitor limit and a daily cap so the OpenAI spend stays within the project budget."""
    now = datetime.now(timezone.utc)
    visitor_key = _rate_key("chat-visitor", request.remote_addr or "unknown")
    global_key = _rate_key("chat-global", "all")
    visitor_count = db.session.query(AuthRateLimitEvent.id).filter(
        AuthRateLimitEvent.key_hash == visitor_key,
        AuthRateLimitEvent.created_at >= now - CHAT_WINDOW,
    ).count()
    global_count = db.session.query(AuthRateLimitEvent.id).filter(
        AuthRateLimitEvent.key_hash == global_key,
        AuthRateLimitEvent.created_at >= now - timedelta(days=1),
    ).count()
    if visitor_count >= CHAT_PER_VISITOR_LIMIT or global_count >= CHAT_DAILY_CAP:
        return False
    db.session.add_all([
        AuthRateLimitEvent(key_hash=visitor_key, created_at=now),
        AuthRateLimitEvent(key_hash=global_key, created_at=now),
    ])
    db.session.commit()
    return True


def _is_trusted_ask_ai(message):
    """Only the results-page button may skip moderation: it must quote one of this session's own recommendations."""
    if not message.startswith("[ASK_AI]"):
        return False
    result = _load_result() or {}
    items = list(result.get("recommendations", []))
    if result.get("sector"):
        items.extend(result["sector"]["recommendations"])
    titles = {item.get("title") for item in items}
    return any(title and f'"{title}"' in message for title in titles)


def _chat_risk_context():
    """Build the risk context on the server so a visitor cannot inject text into the system prompt."""
    result = _load_result()
    if not result:
        return ""
    context = f"{result['risk']} risk (overall score {result['score']}/100)"
    sector = result.get("sector")
    if sector:
        # Only the fixed business-type label and its score are shared, never free text.
        context += f". Business type: {sector['name']} (sector questions score {sector['score']}%)"
    return context


@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for AI-powered chat responses."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Send a JSON request.'}), 400
    user_message = str(data.get('message', '')).strip()
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    if len(user_message) > CHAT_MAX_MESSAGE_LENGTH:
        return jsonify({'error': 'Message is too long.'}), 400

    if user_message.startswith('[ASK_AI]') and not _is_trusted_ask_ai(user_message):
        # An untrusted prefix is removed so the normal moderation and topic checks still apply.
        user_message = user_message[len('[ASK_AI]'):].strip()
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

    if not _chat_budget_available():
        # Budget or rate limit reached: use the offline rule-based assistant instead of OpenAI.
        return jsonify({'response': answer_question(user_message.replace('[ASK_AI]', '').strip()), 'fallback': True})

    try:
        response = get_openai_response(user_message, _chat_risk_context())
        return jsonify({'response': response})
    except Exception:
        app.logger.exception("Chat request failed")
        return jsonify({'error': 'The assistant is temporarily unavailable. Please try again.'}), 500

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"})
