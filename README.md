# 📣 Monday Message Builder
*Katie Sylvia*

A Streamlit app for generating weekly Monday Messages by **track** (DA, DC, RT, …).  
It loads schedules from local CSVs or Google Sheets and outputs a **Slack‑ready** message with grouped instructors and placeholder bullets.

---

## 🚀 Features

- **Track‑first** selection (e.g., DA, DC, RT) — merges all sections in that track.
- Pull data from **local CSVs** (`csv_data/*.csv`) or optionally from **Google Sheets**.
- Fixed columns: `date`, `livelab_title` (no column mapping needed).
- Robust date parsing (reuses your `clean_and_parse_date`) and **ET‑midnight** localization.
- Groups instructors **per lab** by weekday (no repeated lines).
- Produces a **single Slack‑ready message** you can copy or download as `.txt`.
- Optional debug expander when no rows match the selected week.

---

## 📂 Project Structure

```
.
├── app.py                # Streamlit app (track-first, Slack output)
├── config.py             # Instructor map, templates, knobs
├── functions.py          # Utilities (incl. clean_and_parse_date)
├── csv_data/             # Local CSV files per section
└── README.md             # This file
```

---

## ⚙️ Configuration (`config.py`)

Map section CSV filenames → **full Slack display names** exactly as you want them printed:

```python
CSV_TO_INSTRUCTOR = {
    "DA Section 1A.csv": "@Steven Johnson",
    "DA Section 1B.csv": "@Sarah Cole",
    "DA Section 2A.csv": "@Katie",
    "DA Section 2B.csv": "@Mark Vigeant",
    "DA Section 2C.csv": "@Pete (he/him)",
    # Add DC/RT/etc as needed
}
```

Optional knobs:

- `TERM_LABEL`: override the header (e.g., `"Week 4 of Fall '25"`). Set to `None` to show date range.
- `HEADER_TEMPLATE`: string with `{header_label}` placeholder.
- `LAB_PLACEHOLDER_BULLETS`: number of bullets to add under each lab.
- `LAB_TITLE_NORMALIZATION`: normalize variants of the same lab title.

---

## 📥 Data Sources

### Local CSVs (recommended for speed)
Place files in `csv_data/` and name them with a **track prefix**, e.g.:
```
DA Section 1A.csv
DA Section 1B.csv
DC Section 2A.csv
RT Section 1A.csv
```
**Required columns** in each CSV:
- `date` — lab date (any format your `clean_and_parse_date` can parse)
- `livelab_title` — the lab name/title

Example CSV:
```csv
date,livelab_title
2025-09-22,What is a Data Analyst?!
2025-09-24,A/B Testing w/ BuzzFeed
```

### Google Sheets (optional)
If toggled on, the app will read every worksheet whose title **starts with your track** (e.g., `"DA Section 1A"`).  
Provide `st.secrets["google_credentials"]` (a Service Account JSON) in `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml
google_credentials = { 
  type = "service_account",
  project_id = "…",
  private_key_id = "…",
  private_key = "-----BEGIN PRIVATE KEY-----
…
-----END PRIVATE KEY-----
",
  client_email = "…@…gserviceaccount.com",
  client_id = "…",
  auth_uri = "https://accounts.google.com/o/oauth2/auth",
  token_uri = "https://oauth2.googleapis.com/token",
  auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs",
  client_x509_cert_url = "…"
}
```

---

## ▶️ Run

### 1) Install dependencies
```bash
pip install -r requirements.txt
# or
pip install streamlit pandas gspread google-auth pytz
```

### 2) Start the app
```bash
streamlit run app.py
```

### 3) Use it
- Pick a **track** in the sidebar.
- (Optional) Toggle **Google Sheets** for live data.
- Pick the **week of Monday**.
- Copy the **Slack‑ready** message (shown in a code block) or download as `.txt`.

---

## 🧠 How the Slack Message Is Built

- Dates are parsed via your **`clean_and_parse_date`**, then normalized and localized to **America/New_York** midnight.
- The app filters rows within the selected Monday → next Monday window.
- Labs are grouped by **title**. Inside each lab, instructors are grouped **by weekday** and de‑duplicated, e.g.:
  - `:nerd_face: *What is a Data Analyst?!* (Mon - @Steven Johnson / @Katie, Wed - @Pete (he/him))`
- Each lab includes **placeholder bullets** you can customize.

**Tip:** The app shows a formatted preview *and* a raw “Slack‑ready” block (via `st.code`) so bold/italics survive copy‑paste.

---

## ✅ Example Output (Slack‑ready)

```
HI TEAM happy Week of Sep 22–Sep 28, 2025! :fallen_leaf:

:loudspeaker: *ANNOUNCEMENTS* :loudspeaker:
- Placeholder note
- Placeholder note

:test_tube: *LABS THIS WEEK* :test_tube:
:nerd_face: *What is a Data Analyst?!* (Mon - @Steven Johnson / @Katie, Wed - @Pete (he/him))
• Placeholder note
• Placeholder note

:nerd_face: *A/B Testing w/ BuzzFeed* (Thu - @Mark Vigeant, Fri - @Pete (he/him))
• Placeholder note
• Placeholder note
```

---

