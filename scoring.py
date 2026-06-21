"""
scoring.py  -  Student Strength Scoring Engine
==============================================

This is the BRAIN of the dashboard. It turns a raw HubSpot contact into a
0-100 "Strength Score" and a tier (Strong / Very Good / Good / Fair / Weak).

The score answers ONE practical question for customer service:
    "How likely is this student to ENROLL and SUCCEED in getting placed abroad?"

It is built from three pillars (no engagement data needed):

    1. ACADEMIC   (40%) - grades + English test. Can they get an offer?
    2. FINANCIAL  (35%) - funding + budget.      Can they pay / get a visa?
    3. INTENT     (25%) - timeline + clarity.    Are they ready to move now?

Everything you might want to change (weights, thresholds, tier cut-offs) lives
in the CONFIG block at the top. Tune it to match your conversion data over time.
"""

# ---------------------------------------------------------------------------
# CONFIG  - tune these to match your real conversion data
# ---------------------------------------------------------------------------

PILLAR_WEIGHTS = {
    "academic":  0.40,
    "financial": 0.35,
    "intent":    0.25,
}

# Composite score cut-offs (inclusive lower bound) -> tier
TIERS = [
    ("Strong",    80, "#10b981", "Top priority. High chance to enrol & succeed."),
    ("Very Good", 65, "#3b82f6", "Strong prospect. Fast, full-service follow-up."),
    ("Good",      50, "#8b5cf6", "Solid. Nurture and remove blockers."),
    ("Fair",      35, "#f59e0b", "Needs work. One specific gap to close."),
    ("Weak",       0, "#ef4444", "Long shot. Route to guided/self-serve track."),
]

# Money: rough tuition + 1yr living the student must show (your destination avg).
# Used to judge whether a stated budget is "adequate". Change to your numbers.
BUDGET_TARGET = 25000          # in the same currency as the budget column
BUDGET_GOOD_RATIO = 1.0        # budget >= 100% of target  -> full marks
BUDGET_FLOOR_RATIO = 0.4       # budget <= 40% of target    -> zero marks

# How far out an intake is still "hot". Nearer = more ready to act now.
INTAKE_HOT_MONTHS = 6          # within 6 months  -> full intent marks
INTAKE_COLD_MONTHS = 18        # 18+ months away  -> minimal intent marks


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def _num(value):
    """Best-effort parse a number out of messy text like '7.5 bands' or '£20,000'."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("", "n/a", "na", "none", "null", "-"):
        return None
    keep = "".join(c for c in s if (c.isdigit() or c == "."))
    if keep.count(".") > 1:                       # e.g. "3.2.1" -> take first part
        keep = keep.split(".")[0] + "." + keep.split(".")[1]
    try:
        return float(keep) if keep else None
    except ValueError:
        return None


def _norm(value, lo, hi):
    """Linear normalise value from [lo, hi] onto [0, 100]."""
    if value is None:
        return None
    if hi == lo:
        return 0.0
    return _clamp((value - lo) / (hi - lo) * 100.0)


# ---------------------------------------------------------------------------
# 1. ACADEMIC pillar  - grades + English test
# ---------------------------------------------------------------------------

def score_grades(row):
    """Return (0-100, note). Accepts GPA(/4 or /5), percentage, or UK class text."""
    gpa = _num(row.get("gpa"))
    if gpa is not None:
        if gpa <= 5.5:                            # looks like a GPA scale
            scale = 5.0 if gpa > 4.0 else 4.0
            return _norm(gpa, scale * 0.45, scale), f"GPA {gpa}/{int(scale)}"
        if gpa <= 100:                            # someone put a percentage here
            return _norm(gpa, 45, 85), f"{gpa}%"

    pct = _num(row.get("percentage")) or _num(row.get("grade"))
    if pct is not None and pct <= 100:
        return _norm(pct, 45, 85), f"{pct}%"

    cls = str(row.get("grade_class", "")).strip().lower()
    class_map = {
        "first": 95, "1st": 95, "distinction": 95,
        "2:1": 78, "upper second": 78, "merit": 75,
        "2:2": 60, "lower second": 60, "pass": 55,
        "third": 45, "3rd": 45,
    }
    for key, val in class_map.items():
        if key in cls:
            return float(val), cls.title()
    return None, "no grades"


def score_english(row):
    """Return (0-100, note). Accepts IELTS, TOEFL, PTE, or Duolingo."""
    ielts = _num(row.get("ielts"))
    if ielts is not None and ielts <= 9:
        return _norm(ielts, 5.0, 8.0), f"IELTS {ielts}"
    toefl = _num(row.get("toefl"))
    if toefl is not None and toefl <= 120:
        return _norm(toefl, 60, 110), f"TOEFL {toefl}"
    pte = _num(row.get("pte"))
    if pte is not None and pte <= 90:
        return _norm(pte, 50, 79), f"PTE {pte}"
    duo = _num(row.get("duolingo"))
    if duo is not None and duo <= 160:
        return _norm(duo, 90, 140), f"Duolingo {duo}"
    return None, "no English test"


def pillar_academic(row):
    g_score, g_note = score_grades(row)
    e_score, e_note = score_english(row)
    flags = []

    if g_score is None and e_score is None:
        return 30.0, ["No grades or English test on file"], "grades & English missing"
    if e_score is None:
        flags.append("No English test yet - book IELTS/Duolingo")
        value = g_score * 0.85                     # penalise missing English a bit
    elif g_score is None:
        flags.append("Grades missing - request transcript")
        value = e_score * 0.85
    else:
        value = g_score * 0.6 + e_score * 0.4
        if e_score < 30:
            flags.append("English below typical entry - needs prep")
        if g_score < 35:
            flags.append("Grades below typical entry")

    return _clamp(value), flags, f"{g_note}, {e_note}"


# ---------------------------------------------------------------------------
# 2. FINANCIAL pillar  - funding type + budget adequacy
# ---------------------------------------------------------------------------

FUNDING_SCORES = {
    "self": 95, "self-funded": 95, "self funded": 95, "family": 90, "parent": 90,
    "sponsor": 88, "sponsored": 88, "scholarship": 92, "employer": 85,
    "loan": 70, "education loan": 70, "bank loan": 70,
    "partial": 45, "undecided": 25, "unknown": 25, "none": 10, "no funds": 10,
}


def pillar_financial(row):
    flags = []
    raw = str(row.get("funding_type", "")).strip().lower()
    fund_score = None
    for key, val in FUNDING_SCORES.items():
        if key in raw:
            fund_score = float(val)
            break
    if fund_score is None:
        fund_score = 30.0
        flags.append("Funding source unconfirmed")

    budget = _num(row.get("budget"))
    if budget is None:
        budget_score = 35.0
        flags.append("No budget stated - qualify ability to pay")
        budget_note = "budget unknown"
    else:
        ratio = budget / BUDGET_TARGET if BUDGET_TARGET else 0
        budget_score = _norm(ratio, BUDGET_FLOOR_RATIO, BUDGET_GOOD_RATIO)
        budget_note = f"budget {int(budget):,} ({int(ratio*100)}% of target)"
        if ratio < BUDGET_FLOOR_RATIO:
            flags.append("Budget well below requirement - visa/funds risk")
        elif ratio < 0.75:
            flags.append("Budget tight - discuss funding options")

    value = fund_score * 0.5 + budget_score * 0.5
    return _clamp(value), flags, f"{raw or 'funding ?'}, {budget_note}"


# ---------------------------------------------------------------------------
# 3. INTENT pillar  - timeline proximity + clarity of plan + stage
# ---------------------------------------------------------------------------

STAGE_SCORES = {
    "ready": 95, "ready to apply": 95, "application": 95, "applying": 95,
    "offer": 90, "shortlisting": 80, "evaluating": 70, "comparing": 70,
    "researching": 55, "considering": 55, "enquiry": 40, "new": 40,
    "just enquired": 35, "cold": 20, "not sure": 20, "unresponsive": 15,
}


def _months_to_intake(row):
    """Return months until intake from a numeric 'intake_months' column if present."""
    m = _num(row.get("intake_months"))
    if m is not None:
        return m
    # Fall back to coarse text like 'Sep 2026' is intentionally NOT parsed here to
    # keep the engine dependency-free; feed a numeric intake_months for best results.
    return None


def pillar_intent(row):
    flags = []

    # Timeline proximity
    months = _months_to_intake(row)
    if months is None:
        timeline_score = 45.0
        flags.append("No intake date - confirm when they want to start")
    else:
        # nearer intake = higher (more ready to act), but not negative if past.
        if months <= 0:
            timeline_score = 50.0
            flags.append("Intake date passed - re-confirm target intake")
        else:
            timeline_score = _clamp(
                _norm(INTAKE_COLD_MONTHS - months, 0, INTAKE_COLD_MONTHS - INTAKE_HOT_MONTHS)
            )

    # Clarity: do they know country + course?
    has_country = bool(str(row.get("target_country", "")).strip())
    has_course = bool(str(row.get("target_course", "")).strip())
    clarity = (has_country, has_course).count(True) / 2 * 100
    if not has_country:
        flags.append("No target country chosen")
    if not has_course:
        flags.append("No course chosen")

    # Decision stage
    raw = str(row.get("stage", "")).strip().lower()
    stage_score = None
    for key, val in STAGE_SCORES.items():
        if key in raw:
            stage_score = float(val)
            break
    if stage_score is None:
        stage_score = 40.0

    value = timeline_score * 0.4 + clarity * 0.25 + stage_score * 0.35
    return _clamp(value), flags, f"{raw or 'stage ?'}, clarity {int(clarity)}%"


# ---------------------------------------------------------------------------
# Composite + tier
# ---------------------------------------------------------------------------

def tier_for(score):
    for name, lo, color, blurb in TIERS:
        if score >= lo:
            return name, color, blurb
    return TIERS[-1][0], TIERS[-1][2], TIERS[-1][3]


def score_student(row):
    """Main entry: takes a dict (one HubSpot contact) -> scored result dict."""
    a_val, a_flags, a_note = pillar_academic(row)
    f_val, f_flags, f_note = pillar_financial(row)
    i_val, i_flags, i_note = pillar_intent(row)

    composite = (
        a_val * PILLAR_WEIGHTS["academic"]
        + f_val * PILLAR_WEIGHTS["financial"]
        + i_val * PILLAR_WEIGHTS["intent"]
    )
    composite = round(_clamp(composite), 1)
    tier, color, blurb = tier_for(composite)

    name = (row.get("name") or row.get("full_name")
            or f"{row.get('first_name','')} {row.get('last_name','')}").strip() or "Unknown"

    return {
        "name": name,
        "email": row.get("email", ""),
        "phone": row.get("phone", ""),
        "target_country": row.get("target_country", ""),
        "target_course": row.get("target_course", ""),
        "intake_year": row.get("intake_year", ""),
        "intake_months": _num(row.get("intake_months")),
        "funding_type": row.get("funding_type", ""),
        "source": row.get("source", ""),
        "score": composite,
        "tier": tier,
        "tier_color": color,
        "tier_blurb": blurb,
        "pillars": {
            "academic":  {"score": round(a_val, 1), "weight": PILLAR_WEIGHTS["academic"], "note": a_note},
            "financial": {"score": round(f_val, 1), "weight": PILLAR_WEIGHTS["financial"], "note": f_note},
            "intent":    {"score": round(i_val, 1), "weight": PILLAR_WEIGHTS["intent"], "note": i_note},
        },
        "flags": a_flags + f_flags + i_flags,
    }


def score_all(rows):
    scored = [score_student(r) for r in rows]
    scored.sort(key=lambda s: s["score"], reverse=True)
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return scored
