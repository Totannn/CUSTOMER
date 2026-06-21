# Student Strength Dashboard

Rank and segment study-abroad enquiries (1000+/day) so customer service knows
**who to call first, how to handle them, and which gap to close.**

## What it does
- Imports your HubSpot contacts (CSV export).
- Scores each student 0–100 on **likelihood to enrol & succeed** using three pillars:
  - **Academic 40%** – grades + English test
  - **Financial 35%** – funding type + budget adequacy
  - **Intent 25%** – intake timeline + clarity (country/course) + decision stage
- Buckets them into tiers: **Strong / Very Good / Good / Fair / Weak**.
- Gives CS a per-tier **playbook** (SLA, owner, actions, talk track, what to avoid) —
  weak students are still cared for, just on a guided/self-serve track.
- Filter & segment by tier, country, funding, intake window; search; export ranked CSV.

## Run it (Windows / PowerShell)
```powershell
cd C:\Users\olatu\Documents\student-rank-dashboard
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5050 and click **Load sample data**, or **Import HubSpot CSV**.

## Importing your real HubSpot data
Export contacts from HubSpot as CSV. Column names are matched flexibly
(see `COLUMN_ALIASES` in `app.py`). The fields used are:

`name/first_name/last_name, email, phone, gpa, percentage, grade_class,
ielts, toefl, pte, duolingo, funding_type, budget, intake_months,
target_country, target_course, stage, source`

Missing fields are handled gracefully and show up as **flags** for CS to chase.
For best intent scoring, provide `intake_months` (whole months until the intake).

## Connect HubSpot (pull leads automatically)
No more CSV exports — pull contacts straight from your portal.

**1. Create a Private App token in HubSpot**
Settings → Integrations → Private Apps → *Create a private app*.
Under **Scopes** add `crm.objects.contacts.read` (and `crm.schemas.contacts.read`).
Create it and copy the token (starts with `pat-`).

**2. Give the app the token** (PowerShell):
```powershell
setx HUBSPOT_TOKEN "pat-na1-xxxxxxxxxxxx"
```
Open a **new** PowerShell window afterwards. (Or paste the token into a file
named `hubspot_token.txt` in this folder — it's git-ignored.)

**3. Map your property names** in `hubspot_sync.py` → `PROPERTY_MAP`.
The left side is what the scorer needs; change the **right** side to your
HubSpot *internal* property names (Settings → Properties → open a property →
"Internal name"). To pull only a segment, set `SEARCH_FILTER` in the same file.

Then start the app and click **⟳ Sync from HubSpot** in the sidebar.
It pages through all contacts (handles 1000s), scores them, and shows them
ranked — ready to distribute to your CS agents.

**Automatic, hands-off refresh (optional)**
Set an interval and the app re-pulls in the background:
```powershell
setx AUTO_SYNC_MINUTES "30"
```
Restart the app (new window) and it syncs every 30 minutes automatically.
For a scheduled pull without keeping a window open, point **Windows Task
Scheduler** at `http://127.0.0.1:5050/sync-hubspot` instead.

## Tuning the ranking
All weights, thresholds and tier cut-offs live at the top of **`scoring.py`**:
- `PILLAR_WEIGHTS` – shift emphasis between academic/financial/intent.
- `TIERS` – change score cut-offs, colours, labels.
- `BUDGET_TARGET` – the funds a student should show for your destinations.
- `INTAKE_HOT_MONTHS` / `INTAKE_COLD_MONTHS` – what counts as "ready now".

Re-tune these against your own conversion data over time so the score predicts
real enrolments, not just a profile on paper.

## Next steps (when ready)
- Live HubSpot API sync instead of CSV upload.
- Logins + a database (reuse the Monitra pattern) to persist and assign students.
- Write the tier back to HubSpot as a property to drive workflows.
```
