# Jotform → Dashboard: form design guide

The dashboard maps every Jotform answer by its **question label** (case-insensitive,
spaces/trailing punctuation ignored) against the alias table in `app.py`
(`COLUMN_ALIASES`). If you label your questions as shown below, submissions score and
assign to agents automatically — no code changes.

- Labels are matched loosely, so `Email`, `Email Address` both work.
- Any question that doesn't match a known label is **kept but ignored** by the score —
  safe to add your own extra questions (consent, how-did-you-hear, etc.).
- One submission = one lead. **Email is the unique key** used for assignment + audit,
  so make it required.

---

## 1. Recommended questions

| # | Question label to use | Jotform field type | Required | Feeds | Example answer |
|---|----------------------|--------------------|:--------:|-------|----------------|
| 1 | **Name** (or Full Name) | Full Name | ✅ | identity | Idris Sani |
| 2 | **Email** | Email | ✅ | identity (key) | idris@email.com |
| 3 | **Phone** | Phone | ✅ | identity | +234 801 335 6886 |
| 4 | **GPA** *(or **Percentage**)* | Short Text / Number | ✅ | Academic 40% | 3.6 *(or 78)* |
| 5 | **Grade class** | Dropdown | optional | Academic 40% | 2:1 |
| 6 | **IELTS** | Number | optional* | Academic 40% | 7.5 |
| 7 | **TOEFL** | Number | optional* | Academic 40% | 100 |
| 8 | **PTE** | Number | optional* | Academic 40% | 65 |
| 9 | **Duolingo** | Number | optional* | Academic 40% | 120 |
| 10 | **Funding type** | Dropdown | ✅ | Financial 35% | Self-funded |
| 11 | **Budget (GBP)** | Number | ✅ | Financial 35% | 25000 |
| 12 | **Intake year** | Dropdown | ✅ | Intent 25% | 2026/2027 |
| 13 | **Target country** | Dropdown | ✅ | Intent 25% | UK |
| 14 | **Target course** | Short Text / Dropdown | ✅ | Intent 25% | MSc Data Science |
| 15 | **Stage** | Dropdown | optional | Intent 25% | Researching |
| 16 | **Source** | Hidden / Dropdown | optional | reporting | Google Ads |

\* English tests: ask all four as optional number fields and let the applicant fill the
one they have — OR use a "Which English test have you taken?" dropdown with Jotform
**conditional logic** to reveal just the relevant score field. The platform reads
whichever of IELTS / TOEFL / PTE / Duolingo is present.

---

## 2. Dropdown option lists (use these — the scorer recognises the keywords)

**Grade class** (degree classification)
```
First Class
2:1 (Upper Second)
2:2 (Lower Second)
Third
Distinction
Merit
Pass
```

**Funding type** — pick ONE concept per option
```
Self-funded
Family / Parent
Scholarship
Sponsor
Employer
Education loan
Bank loan
Partial
Undecided
None / No funds
```

**Intake year** (academic-year session — the dashboard derives months-to-intake from this)
```
2025/2026
2026/2027
2027/2028
2028/2029
2029/2030
```

**Target country**
```
UK
USA
Canada
Australia
Ireland
Germany
```

**Stage** (where they are in deciding — optional; new leads default to "enquiry")
```
Ready to apply
Shortlisting
Comparing
Evaluating
Researching
New enquiry
Just enquired
Not sure
Cold
Unresponsive
```

**Source** (best set as a HIDDEN field auto-filled from the ad/campaign URL)
```
Google Ads
Meta Campaign
TikTok Ads
Referral
Organic
Webinar
```

---

## 3. Field-specific rules that affect the score

**GPA scale is auto-detected:**
- A value ≤ 5.5 is read as a GPA. If it's > 4.0 the app assumes a **/5** scale,
  otherwise a **/4** scale.
- A value between 6 and 100 is read as a **percentage**.
- ⚠️ A `4.0` is treated as /4 (top marks). If your applicants use a /5 scale where 4.0
  is *not* the max, ask **Percentage** instead to avoid ambiguity.

**English tests** map by typical ranges: IELTS ≤ 9, TOEFL ≤ 120, PTE ≤ 90,
Duolingo ≤ 160. Leave blank if not taken (the score adapts and flags "no English test").

**Budget** is compared to a target of **£25,000** (tuition + ~1yr living; tune
`BUDGET_TARGET` in `scoring.py`). Ask for a number in the same currency.

**Intake year** accepts `2026/2027`, `2026`, or `Sep 2026` — it splits on `/` and uses
the first year. A dropdown of sessions is the cleanest.

---

## 4. Minimum viable form (if you want it short)

Name · Email · Phone · GPA · Funding type · Budget (GBP) · Intake year ·
Target country · Target course

That alone produces a full Strength Score + tier. Everything else sharpens it.

---

## 5. After you build it

1. Get your Jotform **API key** and **Form ID**.
2. Set `JOTFORM_API_KEY` + `JOTFORM_FORM_ID` (env vars) or drop `jotform_key.txt` /
   `jotform_form.txt` next to the app — see `jotform_sync.py`.
3. Click **Sync from Jotform** in the admin sidebar.

If your real question labels differ from the table above, send them over and they get
added to `COLUMN_ALIASES` in `app.py` (one line each).
