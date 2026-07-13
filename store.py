"""
store.py  -  Persistence for agents, lead assignments and the audit trail.
============================================================================

The scored STUDENTS list lives in memory (see app.py) and is rebuilt on every
upload / sync. This module persists the things that must SURVIVE a reload and a
restart, keyed by the student's email (the stable id):

    data/agents.json       -> the customer-service roster (editable)
    data/assignments.json  -> { "assignments": {email: agent},
                                "statuses":    {email: status} }
    data/activity.json     -> append-only audit log of everything each agent did

Two responsibilities worth calling out:

  * apply_assignments()  - distributes leads EQUALLY ACROSS EACH STRENGTH TIER,
    so every agent gets a near-identical mix of Strong/Very Good/.../Weak rather
    than one agent hoarding the strong leads. Existing assignments are kept
    stable; only brand-new leads are handed out.

  * log_activity()       - records one auditable action (call, email, note,
    status change, ...) with a timestamp, so you can always see what each
    person has done.
"""
import json
import os
import threading
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")
ASSIGN_FILE = os.path.join(DATA_DIR, "assignments.json")
ACTIVITY_FILE = os.path.join(DATA_DIR, "activity.json")

# Default customer-service roster. Edit on the Team page or here.
DEFAULT_AGENTS = ["Amara Obi", "Bola Adeyemi", "Chidi Okonkwo",
                  "Dami Lawal", "Efe Johnson"]

# The contact workflow each lead moves through.
STATUSES = ["New", "Attempted", "Contacted", "In Progress", "Converted", "Lost"]

# Action types an agent can log against a lead.
ACTIONS = ["Call", "Email", "WhatsApp", "Meeting booked",
           "No answer", "Note", "Status change"]

_lock = threading.RLock()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, data):
    """Atomic write so a crash mid-save can't corrupt the file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# --- Agents roster ----------------------------------------------------------

def get_agents():
    with _lock:
        agents = _load(AGENTS_FILE, None)
        if not agents:
            agents = list(DEFAULT_AGENTS)
            _save(AGENTS_FILE, agents)
        return agents


def set_agents(agents):
    with _lock:
        agents = [a.strip() for a in agents if a and a.strip()]
        if not agents:
            agents = list(DEFAULT_AGENTS)
        _save(AGENTS_FILE, agents)
        return agents


# --- Assignments + statuses -------------------------------------------------

def _assign_data():
    data = _load(ASSIGN_FILE, {})
    data.setdefault("assignments", {})
    data.setdefault("statuses", {})
    return data


def get_assignments():
    with _lock:
        return _assign_data()


def apply_assignments(students, tier_order):
    """Give every student a stable agent + status, in place.

    Already-assigned leads keep their owner. New leads are dealt out so each
    agent's count WITHIN EACH TIER stays as even as possible (ties broken by
    smallest overall workload). Also enriches each student with their current
    status and a summary of their audit history.
    """
    with _lock:
        data = _assign_data()
        assignments = data["assignments"]
        statuses = data["statuses"]
        agents = get_agents()
        valid = set(agents)

        present = {s["email"]: s for s in students if s.get("email")}

        # Current load per agent, per tier, counting only leads we still hold.
        load = {a: {} for a in agents}
        total = {a: 0 for a in agents}
        for email, s in present.items():
            a = assignments.get(email)
            if a in valid:
                load[a][s["tier"]] = load[a].get(s["tier"], 0) + 1
                total[a] += 1

        # Hand out the unassigned: best tiers first, strongest first within tier.
        rank = {t: i for i, t in enumerate(tier_order)}
        unassigned = [s for s in present.values()
                      if assignments.get(s["email"]) not in valid]
        unassigned.sort(key=lambda s: (rank.get(s["tier"], 99), -s["score"]))

        changed = False
        for s in unassigned:
            if not agents:
                break
            t = s["tier"]
            best = min(agents, key=lambda a: (load[a].get(t, 0), total[a]))
            assignments[s["email"]] = best
            load[best][t] = load[best].get(t, 0) + 1
            total[best] += 1
            changed = True

        if changed:
            data["assignments"] = assignments
            _save(ASSIGN_FILE, data)

        # Enrich each student with assignment + status + audit summary.
        activity = _load(ACTIVITY_FILE, [])
        last_by_email, count_by_email = {}, {}
        for ev in activity:
            e = ev.get("email")
            if not e:
                continue
            count_by_email[e] = count_by_email.get(e, 0) + 1
            last_by_email[e] = ev  # log is chronological; last wins

        for s in students:
            e = s.get("email")
            s["agent"] = assignments.get(e, "Unassigned")
            s["status"] = statuses.get(e, "New")
            s["activity_count"] = count_by_email.get(e, 0)
            last = last_by_email.get(e)
            s["last_activity"] = last["ts"] if last else None
            s["last_action"] = last["action"] if last else None
        return students


def redistribute(students, tier_order):
    """Wipe assignments and deal everything out fresh, balanced per tier."""
    with _lock:
        data = _assign_data()
        data["assignments"] = {}
        _save(ASSIGN_FILE, data)
    return apply_assignments(students, tier_order)


# --- Audit trail ------------------------------------------------------------

def log_activity(agent, email, student_name, action, status=None, note=None):
    with _lock:
        activity = _load(ACTIVITY_FILE, [])
        ev = {
            "id": (activity[-1]["id"] + 1) if activity else 1,
            "ts": _now(),
            "agent": agent,
            "email": email,
            "student": student_name,
            "action": action,
            "status": status or None,
            "note": (note or "").strip(),
        }
        activity.append(ev)
        _save(ACTIVITY_FILE, activity)

        if status:
            data = _assign_data()
            data["statuses"][email] = status
            _save(ASSIGN_FILE, data)
        return ev


def get_activity(agent=None, email=None):
    with _lock:
        log = _load(ACTIVITY_FILE, [])
    if agent:
        log = [e for e in log if e.get("agent") == agent]
    if email:
        log = [e for e in log if e.get("email") == email]
    return log
