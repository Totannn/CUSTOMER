"""
hubspot_sync.py  -  Pull contacts straight from HubSpot into the dashboard.

SETUP (one time)
----------------
1. In HubSpot:  Settings -> Integrations -> Private Apps -> Create a private app.
   Give it the scope:  crm.objects.contacts.read   (add crm.schemas.contacts.read too).
   Copy the access token (starts with 'pat-').

2. Tell this app the token. Easiest on Windows PowerShell:
       setx HUBSPOT_TOKEN "pat-na1-xxxxxxxx"
   then open a NEW PowerShell window so it picks the value up.
   (Or drop the token into a file named  hubspot_token.txt  in this folder.)

3. Map YOUR HubSpot property names below in PROPERTY_MAP, then click
   "Sync from HubSpot" in the dashboard sidebar.

Find your internal property names in HubSpot:
   Settings -> Properties -> click a property -> the "Internal name" (e.g. 'gpa').
Defaults to the left of the ':' are what our scorer needs; values on the right
are HubSpot's internal names — change the right-hand side to match your portal.
"""
import os

import requests

BASE = "https://api.hubapi.com"
HERE = os.path.dirname(os.path.abspath(__file__))


def get_token():
    token = os.environ.get("HUBSPOT_TOKEN", "").strip()
    if not token:
        path = os.path.join(HERE, "hubspot_token.txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                token = f.read().strip()
    return token


# our_field  ->  HubSpot internal property name  (EDIT the right-hand side)
PROPERTY_MAP = {
    "first_name":     "firstname",
    "last_name":      "lastname",
    "email":          "email",
    "phone":          "phone",
    # --- academic ---
    "gpa":            "gpa",                 # <-- your custom property names
    "grade_class":    "degree_class",
    "ielts":          "ielts_score",
    "toefl":          "toefl_score",
    "pte":            "pte_score",
    "duolingo":       "duolingo_score",
    # --- financial ---
    "funding_type":   "funding_type",
    "budget":         "budget",
    # --- intent ---
    "intake_year":    "intake_session",
    "target_country": "preferred_country",
    "target_course":  "preferred_course",
    "stage":          "hs_lead_status",      # or "lifecyclestage"
    "source":         "hs_analytics_source",
}

# Optional: only pull contacts that match a filter (keeps daily syncs light).
# Leave as None to pull everyone. Example below pulls only lifecycle stage 'lead'.
SEARCH_FILTER = None
# SEARCH_FILTER = {"propertyName": "lifecyclestage", "operator": "EQ", "value": "lead"}


def _row_from_contact(contact):
    props = contact.get("properties", {}) or {}
    return {ours: (props.get(hs) or "") for ours, hs in PROPERTY_MAP.items()}


def fetch_contacts(max_records=None):
    """Return a list of canonical-field dicts ready for scoring. Raises on bad token."""
    token = get_token()
    if not token:
        raise RuntimeError(
            "No HubSpot token found. Set HUBSPOT_TOKEN or create hubspot_token.txt "
            "(see hubspot_sync.py for setup steps)."
        )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    wanted = list(dict.fromkeys(PROPERTY_MAP.values()))   # unique, ordered
    contacts, after = [], None

    while True:
        if SEARCH_FILTER:
            url = f"{BASE}/crm/v3/objects/contacts/search"
            body = {
                "filterGroups": [{"filters": [SEARCH_FILTER]}],
                "properties": wanted, "limit": 100,
            }
            if after:
                body["after"] = after
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            url = f"{BASE}/crm/v3/objects/contacts"
            params = {"limit": 100, "properties": ",".join(wanted)}
            if after:
                params["after"] = after
            resp = requests.get(url, headers=headers, params=params, timeout=30)

        if resp.status_code == 401:
            raise RuntimeError("HubSpot rejected the token (401). Check it and its scopes.")
        resp.raise_for_status()
        data = resp.json()

        for c in data.get("results", []):
            contacts.append(_row_from_contact(c))

        after = (data.get("paging", {}).get("next", {}) or {}).get("after")
        if not after or (max_records and len(contacts) >= max_records):
            break

    return contacts
