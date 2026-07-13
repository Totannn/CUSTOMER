"""
jotform_sync.py  -  Pull form submissions straight from Jotform into the dashboard.

WHAT IT DOES
------------
Every Jotform submission becomes one "contact" row. Each answer is keyed by its
QUESTION LABEL (e.g. "Email", "GPA", "Funding type"), and the dashboard's existing
column-alias mapping (COLUMN_ALIASES in app.py) turns those labels into the fields
the scorer understands — so as long as your Jotform question labels resemble the
aliases already listed there, this works with no extra mapping.

SETUP (one time)
----------------
1. Get an API key:  Jotform -> Account -> API -> Create New Key (Full/Read access).
2. Get your Form ID: open the form; the number in the URL (…/build/240xxxxxxxxxx)
   or in My Forms is the Form ID.
3. Tell this app, either via environment (PowerShell):
       setx JOTFORM_API_KEY "your-key"
       setx JOTFORM_FORM_ID "240xxxxxxxxxx"
   then open a NEW terminal. OR drop them in files next to this one:
       jotform_key.txt      (the API key)
       jotform_form.txt     (the form id)
4. Click "Sync from Jotform" in the admin sidebar.

EU data-region accounts: set JOTFORM_API_BASE="https://eu-api.jotform.com".
"""
import os

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("JOTFORM_API_BASE", "https://api.jotform.com").rstrip("/")


def _read(env_name, file_name):
    val = os.environ.get(env_name, "").strip()
    if not val:
        path = os.path.join(HERE, file_name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                val = f.read().strip()
    return val


def get_api_key():
    return _read("JOTFORM_API_KEY", "jotform_key.txt")


def get_form_id():
    return _read("JOTFORM_FORM_ID", "jotform_form.txt")


def _flatten_answer(ans):
    """Jotform answers can be strings, name/address dicts, or lists. Make them flat text."""
    val = ans.get("answer")
    if val in (None, "", [], {}):
        val = ans.get("prettyFormat", "")
    if isinstance(val, dict):
        if "first" in val or "last" in val:                  # full-name field
            return f"{val.get('first', '')} {val.get('last', '')}".strip()
        return " ".join(str(v) for v in val.values() if v)   # address / composite
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v)
    return str(val).strip()


def _combine_english_test(row):
    """Forms that ask 'Which English test?' + one 'Test score' field get folded into
    the right canonical field (IELTS/TOEFL/PTE/Duolingo) the scorer understands."""
    test = score = ""
    for k in list(row):
        kl = k.strip().lower()
        if kl in ("english test", "which english test", "english test taken"):
            test = row.pop(k)
        elif kl in ("test score", "english test score", "score"):
            score = row.pop(k)
    if test and score and "none" not in str(test).lower():
        t = str(test).lower()
        for name in ("ielts", "toefl", "pte", "duolingo"):
            if name in t:
                row[name] = score
                break
    return row


def _row_from_submission(sub):
    """One submission -> {question label: answer text}."""
    row = {}
    for ans in (sub.get("answers") or {}).values():
        label = (ans.get("text") or ans.get("name") or "").strip()
        if not label or ans.get("type") in ("control_head", "control_button",
                                            "control_pagebreak", "control_divider"):
            continue
        val = _flatten_answer(ans)
        if val:
            row[label] = val
    return _combine_english_test(row)


def fetch_contacts(form_id=None, max_records=1000):
    """Return a list of label-keyed dicts ready for normalise_row + scoring."""
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "No Jotform API key found. Set JOTFORM_API_KEY or create jotform_key.txt "
            "(see jotform_sync.py for setup steps)."
        )
    form_id = form_id or get_form_id()
    if not form_id:
        raise RuntimeError(
            "No Jotform form id found. Set JOTFORM_FORM_ID or create jotform_form.txt."
        )

    rows, offset, limit = [], 0, 100
    while True:
        resp = requests.get(
            f"{BASE}/form/{form_id}/submissions",
            params={"apiKey": key, "limit": limit, "offset": offset},
            timeout=30,
        )
        if resp.status_code == 401:
            raise RuntimeError("Jotform rejected the API key (401). Check the key and its access.")
        if resp.status_code == 404:
            raise RuntimeError(f"Jotform form '{form_id}' not found (404). Check the form id.")
        resp.raise_for_status()

        content = resp.json().get("content") or []
        for sub in content:
            row = _row_from_submission(sub)
            if row:
                rows.append(row)

        if len(content) < limit or len(rows) >= max_records:
            break
        offset += limit

    return rows
