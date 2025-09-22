import os
import re
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import pytz
import streamlit as st

# Google Sheets deps (optional)
try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

from config import (
    CSV_TO_INSTRUCTOR,
    TERM_LABEL,
    HEADER_TEMPLATE,
    LAB_PLACEHOLDER_BULLETS,
    LAB_TITLE_NORMALIZATION,
)

from functions import clean_and_parse_date

# ==============================
# 📅 Timezone & constants
# ==============================
ET_TZ = pytz.timezone("America/New_York")
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_ABBR = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}


def start_of_week(dt_et: datetime) -> datetime:
    dt_et = dt_et.astimezone(ET_TZ)
    monday = dt_et - timedelta(days=dt_et.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_week(monday_dt: datetime) -> datetime:
    return monday_dt + timedelta(days=7)


def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return str(title)
    key = title.strip()
    low = key.lower()
    for k, v in LAB_TITLE_NORMALIZATION.items():
        if low == k.lower():
            return v
    return key


def to_et_midnight(x) -> pd.Timestamp | None:
    """Vectorized-friendly: convert to tz-aware ET midnight Timestamp.
    Uses your clean_and_parse_date() for correctness, then normalizes.
    """
    try:
        parsed = clean_and_parse_date(x)
    except Exception:
        parsed = None
    if parsed is None or (isinstance(parsed, float) and pd.isna(parsed)):
        return None
    ts = pd.to_datetime(parsed, errors="coerce")  # pandas Timestamp (naive)
    if pd.isna(ts):
        return None
    ts = ts.normalize()  # set to 00:00
    try:
        return ts.tz_localize(ET_TZ)
    except TypeError:
        # already tz-aware
        return ts.tz_convert(ET_TZ)


def human_header_label(week_monday: datetime) -> str:
    if TERM_LABEL:
        return TERM_LABEL
    week_next = end_of_week(week_monday) - timedelta(days=1)
    return f"Week of {week_monday.strftime('%b %d')}"



# ==============================
# 🧠 Monday Message generator (returns ONE Slack-ready string)
# ==============================

def generate_monday_message(df: pd.DataFrame, *, week_monday: datetime) -> str:
    week_next_monday = end_of_week(week_monday)

    tmp = df.copy()
    ts = pd.to_datetime(tmp["date"], errors="coerce").dt.normalize()
    try:
        tmp["__date_dt"] = ts.dt.tz_localize(ET_TZ)
    except TypeError:
        tmp["__date_dt"] = ts.dt.tz_convert(ET_TZ)

    in_week = (tmp["__date_dt"] >= week_monday) & (tmp["__date_dt"] < week_next_monday)
    w = tmp.loc[in_week].copy()

    if w.empty:
        return f"No labs found for {human_header_label(week_monday)}."

    w["__weekday"] = w["__date_dt"].dt.strftime("%A")
    w["__weekday_abbr"] = w["__date_dt"].dt.strftime("%a")
    w["__weekday_rank"] = w["__weekday"].apply(lambda d: WEEKDAY_ORDER.index(d) if d in WEEKDAY_ORDER else 99)
    w["__title"] = w["livelab_title"].astype(str).map(normalize_title)
    w["__instructor"] = (
        w.get("section").map(lambda s: CSV_TO_INSTRUCTOR.get(f"{s}.csv", "TBD"))
        if "section" in w.columns else "TBD"
    )
    w.sort_values(["__weekday_rank", "__date_dt", "__title"], inplace=True)

    # Build a single Slack-ready message
    lines = []
    temp1 = HEADER_TEMPLATE.format(header_label=human_header_label(week_monday))
    lines.append(f"### {temp1}")
    lines.append("")  # spacer
    lines.append("#### :loudspeaker: **ANNOUNCEMENTS** :loudspeaker:")
    lines.append("- Placeholder note")
    lines.append("\n")
    lines.append("")  # spacer
    lines.append("#### :test_tube: **LABS THIS WEEK** :test_tube:")

    # Group by lab title, then aggregate day → unique instructors
    for title, g in w.groupby("__title", sort=False):
        day_to_instructors = {}
        for _, row in g.iterrows():
            day = row["__weekday_abbr"]
            instr = row["__instructor"]
            if day not in day_to_instructors:
                day_to_instructors[day] = []
            if instr not in day_to_instructors[day]:
                day_to_instructors[day].append(instr)

        # Compose segments in weekday order
        day_rank = {d: i for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])}
        segments = []
        for day in sorted(day_to_instructors.keys(), key=lambda d: day_rank.get(d, 99)):
            instrs = " / ".join(day_to_instructors[day])
            segments.append(f"*{day} - {instrs}*")
        schedule = ", ".join(segments)

        lines.append(f":nerd_face: **{title}** ({schedule})")
        for _ in range(LAB_PLACEHOLDER_BULLETS):
            lines.append("- Placeholder note")
            lines.append("\n")

    return "\n".join(lines)


# ==============================
# 📥 Google loader (track → concat all sheets)
# ==============================
@st.cache_data(ttl=3600)
def fetch_track_from_google(track: str) -> pd.DataFrame:
    if gspread is None or Credentials is None:
        return pd.DataFrame()
    creds_dict = dict(st.secrets.get("google_credentials", {}))
    if not creds_dict:
        return pd.DataFrame()

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    spreadsheet = client.open("Curriculum Schedules All Tracks")
    sheets = spreadsheet.worksheets()

    frames: List[pd.DataFrame] = []
    for ws in sheets:
        title = ws.title
        if re.match(rf"^{re.escape(track)}(\b|[\s_-])", title):
            values = ws.get_all_values("A1:Z200")
            if not values:
                continue
            df = pd.DataFrame(values[1:], columns=values[0])
            df["section"] = title
            # Use your cleaner for dates here too
            if "date" in df.columns:
                df["date"] = df["date"].apply(lambda x: clean_and_parse_date(x))
            frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ==============================
# 🔧 App Config
# ==============================
st.set_page_config(page_icon='books', page_title="Monday Message Builder", layout="wide")

# ------------------------------
# 📂 Discover local CSVs + infer tracks
# -------------------------------
local_basenames: List[str] = []
if os.path.isdir("csv_data"):
    local_basenames = [f[:-4] for f in os.listdir("csv_data") if f.lower().endswith(".csv")]

# A track is the leading token before first space/underscore/hyphen (e.g., 'DA', 'DC', 'RT')
def infer_track(name: str) -> str:
    m = re.match(r"^([A-Za-z]+)(?:[\s_-].*)?$", name.strip())
    return m.group(1) if m else name.strip().split()[0]

local_tracks = sorted({infer_track(name) for name in local_basenames if name.strip()})


# -------------------------------
# 🖱️ Sidebar Controls — Track-first
# -------------------------------
with st.sidebar:
    st.header("📂 Choose a Track")
    selected_track = st.selectbox("Track", [""] + local_tracks)
    st.write("")
    # Keep Google toggle behavior consistent
    if "prev_selected_track" not in st.session_state:
        st.session_state.prev_selected_track = ""
    if selected_track != st.session_state.prev_selected_track:
        st.session_state.use_google = False
        st.session_state.prev_selected_track = selected_track
    if selected_track:
        st.toggle(
            "Is something missing? Toggle to connect to the Google Sheet for the most up-to-date version.",
            value=st.session_state.get("use_google", False),
            key="use_google",
        )
if not selected_track:
    st.info("Use the sidebar to select a track.")
    st.stop()


# -------------------------------
# 🗂️ Load data (all sections under the selected track)
# -------------------------------
if st.session_state.get("use_google", False):
    with st.spinner(f"Loading all {selected_track} worksheets from Google Sheets..."):
        df_track = fetch_track_from_google(selected_track)
else:
    track_pat = re.compile(rf"^{re.escape(selected_track)}(\b|[\s_-])", re.IGNORECASE)
    basenames_for_track = [bn for bn in local_basenames if track_pat.search(bn)]
    frames: List[pd.DataFrame] = []
    for bn in basenames_for_track:
        csv_path = os.path.join("csv_data", f"{bn}.csv")
        if os.path.exists(csv_path):
            df_tmp = pd.read_csv(csv_path)
            df_tmp["section"] = bn
            # Use cleaner immediately on the raw date col
            if "date" in df_tmp.columns:
                df_tmp["date"] = df_tmp["date"].apply(lambda x: clean_and_parse_date(x))
            frames.append(df_tmp)
    df_track = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if df_track.empty:
    with st.expander("🔎 Debug: What I looked for", expanded=False):
        st.write({
            "selected_track": selected_track,
            "local_basenames": local_basenames,
            "matched_basenames": basenames_for_track if 'basenames_for_track' in locals() else [],
            "using_google": st.session_state.get("use_google", False),
        })
    st.error("No data found for this track. Make sure filenames (or worksheet titles) start with the track code, e.g., 'RT Section 1A.csv'.")
    st.stop()

if selected_track:
    st.title(f"📣 Monday Message — :blue[**{selected_track} Track**]")
else:
    st.title("📣 Monday Message")



# -------------------------------
# 📆 Pick the target week (Monday)
# -------------------------------
col1, col2 = st.columns([1,3], vertical_alignment="top", border = True, gap = "medium")

with col1:
    now_et = datetime.now(ET_TZ)
    week_monday_dt = start_of_week(now_et)
    week_date = st.date_input("Select a Monday", value=week_monday_dt.date(), format="MM/DD/YYYY")
    week_monday_dt = ET_TZ.localize(datetime.combine(week_date, datetime.min.time()))

# -------------------------------
# 🧾 Generate & display Monday message
# -------------------------------
with col2:
    msg = generate_monday_message(df=df_track, week_monday=week_monday_dt)
    st.markdown(msg)
