"""
Study-Abroad Student Strength Dashboard  -  Flask app
Run:  py -m venv .venv  ->  .venv\\Scripts\\activate  ->  pip install -r requirements.txt  ->  python app.py
Open: http://127.0.0.1:5050
"""
import csv
import io
import os
from datetime import date

from flask import (Flask, jsonify, render_template, request,
                   redirect, url_for, Response, flash)

import scoring

app = Flask(__name__)
app.secret_key = "change-me-in-production"

# In-memory store. For 1000+/day this is fine; swap for a DB when you add logins.
STUDENTS = []          # list of scored dicts
SOURCE_NOTE = "No data loaded yet"

HERE = os.path.dirname(os.path.abspath(__file__))

# How HubSpot / common export headers map onto the fields the scorer expects.
# Lower-cased, stripped. Add your real HubSpot internal names here.
COLUMN_ALIASES = {
    "name": ["name", "full name", "contact name"],
    "first_name": ["first name", "firstname"],
    "last_name": ["last name", "lastname"],
    "email": ["email", "email address"],
    "phone": ["phone", "phone number", "mobile", "mobile phone number"],
    "gpa": ["gpa", "cgpa", "grade point average"],
    "percentage": ["percentage", "marks", "aggregate"],
    "grade_class": ["grade class", "degree class", "classification"],
    "ielts": ["ielts", "ielts score"],
    "toefl": ["toefl", "toefl score"],
    "pte": ["pte", "pte score"],
    "duolingo": ["duolingo", "duolingo score"],
    "funding_type": ["funding type", "funding", "funding source", "how will you fund"],
    "budget": ["budget", "budget (gbp)", "available funds", "budget amount"],
    "intake_year": ["intake year", "intake", "intake/session", "session",
                    "intake session", "preferred intake"],
    "intake_months": ["intake months", "months to intake", "months_to_intake"],
    "target_country": ["target country", "country", "preferred country", "destination"],
    "target_course": ["target course", "course", "program", "programme", "subject"],
    "stage": ["stage", "lead status", "lifecycle stage", "deal stage", "status"],
    "source": ["source", "lead source", "original source", "campaign"],
}


def _build_alias_lookup():
    lookup = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            lookup[a] = canonical
    return lookup


ALIAS_LOOKUP = _build_alias_lookup()


def year_to_months(intake_year):
    """'2026/2027' -> whole months from today to the September intake of that session."""
    try:
        start = int(str(intake_year).split("/")[0].strip())
    except (ValueError, AttributeError):
        return None
    today = date.today()
    return (start - today.year) * 12 + (9 - today.month)   # intakes start ~September


def normalise_row(raw):
    """Map an arbitrary CSV row onto canonical field names the scorer understands."""
    out = {}
    for key, value in raw.items():
        if key is None:
            continue
        canonical = ALIAS_LOOKUP.get(key.strip().lower())
        if canonical:
            out[canonical] = value
        else:
            out[key.strip().lower()] = value      # keep unknowns too, harmless
    # Derive months-to-intake from the academic-year session for the scorer.
    if out.get("intake_year") and not out.get("intake_months"):
        m = year_to_months(out["intake_year"])
        if m is not None:
            out["intake_months"] = m
    return out


def load_csv_text(text):
    reader = csv.DictReader(io.StringIO(text))
    rows = [normalise_row(r) for r in reader]
    return scoring.score_all(rows)


# --- Customer-service playbook per tier (the "effective for CS" part) ---------
PLAYBOOK = {
    "Strong": {
        "headline": "Concierge - win these, fast.",
        "sla": "Call within 15 minutes. Senior counsellor owns it end-to-end.",
        "owner": "Senior counsellor",
        "actions": [
            "Phone first, not email - book a video consult the same day.",
            "Move straight to shortlisting universities and application prep.",
            "Offer premium/fast-track service; protect against competitors.",
            "Confirm documents checklist and target deadlines immediately.",
        ],
        "talk_track": "You're a strong candidate - let's get your applications in early to maximise offers and scholarships.",
        "avoid": "Don't leave them in a queue or send generic drip emails.",
    },
    "Very Good": {
        "headline": "Full-service, quick follow-up.",
        "sla": "Call within 1 hour. Assigned counsellor.",
        "owner": "Counsellor",
        "actions": [
            "Call to confirm intake, country and course.",
            "Send a tailored university shortlist within 24h.",
            "Close the one or two gaps flagged (e.g. English test booking).",
            "Set the next concrete step with a date.",
        ],
        "talk_track": "You've got a great profile - here's a shortlist; let's lock your intake and timeline.",
        "avoid": "Don't over-qualify - they're ready; reduce friction.",
    },
    "Good": {
        "headline": "Nurture and remove blockers.",
        "sla": "Contact within 4 working hours.",
        "owner": "Counsellor / junior counsellor",
        "actions": [
            "Identify the single biggest blocker from the flags and tackle it.",
            "Share funding options or English-prep resources as relevant.",
            "Put on a structured nurture sequence with check-in calls.",
            "Re-score after the blocker is resolved - many move up a tier.",
        ],
        "talk_track": "You have real potential - let's sort out [blocker] and you'll be in great shape.",
        "avoid": "Don't drop them - one fixed gap often turns Good into Very Good.",
    },
    "Fair": {
        "headline": "One specific gap to close.",
        "sla": "Contact within 1 working day.",
        "owner": "Junior counsellor / support team",
        "actions": [
            "Be honest about the main gap (funds, grades, or English).",
            "Give a clear, realistic path: what to improve and by when.",
            "Offer lower-barrier options (pathway/foundation, cheaper destinations).",
            "Set a follow-up trigger for when their situation changes.",
        ],
        "talk_track": "Here's exactly what to improve to make this work - let's build a realistic plan.",
        "avoid": "Don't overpromise admission they can't realistically reach.",
    },
    "Weak": {
        "headline": "Guided / self-serve track - still cared for.",
        "sla": "Bulk nurture; respond to inbound within 1-2 days.",
        "owner": "Support team / automation + counsellor on request",
        "actions": [
            "Route to self-serve guides, webinars and FAQs.",
            "Set expectations kindly and honestly about current options.",
            "Capture what would change their eligibility, then re-score.",
            "Keep the door open - circumstances and intakes change.",
        ],
        "talk_track": "Right now these are your options - here are resources, and we're here when things change.",
        "avoid": "Don't ignore or dismiss them - protect the brand and future referrals.",
    },
}


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/students")
def api_students():
    return jsonify(STUDENTS)


@app.route("/api/meta")
def api_meta():
    counts = {}
    for s in STUDENTS:
        counts[s["tier"]] = counts.get(s["tier"], 0) + 1
    tier_order = [t[0] for t in scoring.TIERS]
    avg = round(sum(s["score"] for s in STUDENTS) / len(STUDENTS), 1) if STUDENTS else 0
    priority = sum(counts.get(t, 0) for t in ("Strong", "Very Good"))
    return jsonify({
        "total": len(STUDENTS),
        "average": avg,
        "priority": priority,
        "counts": counts,
        "tier_order": tier_order,
        "tier_meta": [{"name": t[0], "color": t[2], "blurb": t[3]} for t in scoring.TIERS],
        "playbook": PLAYBOOK,
        "source_note": SOURCE_NOTE,
        "weights": scoring.PILLAR_WEIGHTS,
    })


@app.route("/upload", methods=["POST"])
def upload():
    global STUDENTS, SOURCE_NOTE
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please choose a CSV file.")
        return redirect(url_for("dashboard"))
    try:
        text = file.read().decode("utf-8-sig")
        STUDENTS = load_csv_text(text)
        SOURCE_NOTE = f"Loaded {len(STUDENTS)} contacts from {file.filename}"
    except Exception as exc:                       # noqa: BLE001
        flash(f"Could not read CSV: {exc}")
    return redirect(url_for("dashboard"))


@app.route("/sync-hubspot")
def sync_hubspot():
    try:
        _run_hubspot_sync()
        if not STUDENTS:
            flash("HubSpot returned 0 contacts. Check your filter / property names.")
    except Exception as exc:                       # noqa: BLE001
        flash(f"HubSpot sync failed: {exc}")
    return redirect(url_for("dashboard"))


@app.route("/load-sample")
def load_sample():
    global STUDENTS, SOURCE_NOTE
    path = os.path.join(HERE, "sample_data.csv")
    with open(path, encoding="utf-8-sig") as f:
        STUDENTS = load_csv_text(f.read())
    SOURCE_NOTE = f"Sample data ({len(STUDENTS)} contacts)"
    return redirect(url_for("dashboard"))


@app.route("/export")
def export():
    if not STUDENTS:
        return redirect(url_for("dashboard"))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Rank", "Name", "Email", "Phone", "Score", "Tier",
                "Academic", "Financial", "Intent", "Country", "Course",
                "Intake", "Funding", "Flags"])
    for s in STUDENTS:
        w.writerow([
            s["rank"], s["name"], s["email"], s["phone"], s["score"], s["tier"],
            s["pillars"]["academic"]["score"], s["pillars"]["financial"]["score"],
            s["pillars"]["intent"]["score"], s["target_country"], s["target_course"],
            s["intake_year"], s["funding_type"], " | ".join(s["flags"]),
        ])
    return Response(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ranked_students.csv"},
    )


def _run_hubspot_sync():
    """Used by both the route and the background auto-sync."""
    global STUDENTS, SOURCE_NOTE
    import hubspot_sync
    raw = hubspot_sync.fetch_contacts()
    rows = [normalise_row(r) for r in raw]
    STUDENTS = scoring.score_all(rows)
    SOURCE_NOTE = f"HubSpot sync: {len(STUDENTS)} contacts"


def start_auto_sync():
    """If AUTO_SYNC_MINUTES is set, re-pull HubSpot on that interval in the background."""
    minutes = os.environ.get("AUTO_SYNC_MINUTES")
    if not minutes:
        return
    try:
        interval = max(1, int(minutes)) * 60
    except ValueError:
        return
    import threading

    def loop():
        import time
        while True:
            try:
                _run_hubspot_sync()
                print(f"[auto-sync] refreshed {len(STUDENTS)} contacts from HubSpot")
            except Exception as exc:               # noqa: BLE001
                print(f"[auto-sync] failed: {exc}")
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()
    print(f"[auto-sync] enabled every {minutes} min")


if __name__ == "__main__":
    # Only start the background loop in the real process, not the debug reloader child.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        start_auto_sync()
    app.run(debug=True, port=5050)
