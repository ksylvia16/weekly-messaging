# =========================================================
# Imports
# =========================================================
from datetime import datetime, timedelta
import re
import pandas as pd

try:
    from utils.edits import PROJECT_DUE_DATES, get_milestone_due_days
except Exception:
    PROJECT_DUE_DATES = {}
    def get_milestone_due_days(_section):
        return []
    
# =========================================================
# 🧰 General Helpers
# =========================================================
def clean_and_parse_date(date_str, fallback_year=None):
    """
    Extracts MM/DD from strings like 'Monday, 09/01 SKIPPED FOR HOLIDAY!' 
    and returns a datetime object.
    """
    try:
        parts = str(date_str).split(", ")
        if len(parts) < 2:
            return None
        mmdd_part = parts[1].strip().split()[0]  # "09/01"
        if fallback_year is None:
            fallback_year = datetime.now().year
        return datetime.strptime(f"{mmdd_part}/{fallback_year}", "%m/%d/%Y")
    except Exception:
        return None


def add_ordinal_suffix(date):
    """Adds an ordinal suffix (st, nd, rd, th) to the day of a datetime object."""
    if date is None:
        return "Unknown Date"
    day = date.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return date.strftime(f"%A, %B {day}{suffix}")


def adjust_to_most_recent_friday(date):
    """Given any date, returns the most recent Friday (or the same day if it's already Friday)."""
    return date - timedelta(days=(date.weekday() - 4) % 7)


def get_fridays_between(start_date, end_date):
    """Return list of all Fridays between start_date and end_date (inclusive)."""
    fridays = []
    current = start_date
    # Go forward to the first Friday
    while current.weekday() != 4:
        current += timedelta(days=1)
    while current <= end_date:
        fridays.append(current)
        current += timedelta(weeks=1)
    return fridays


# =========================================================
# 🔎 Tiny helpers
# =========================================================
def _is_empty(val) -> bool:
    """Treat NaN/NaT/None/'nan'/'null' as empty."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return True
    s = str(val).strip()
    return s == "" or s.lower() in {"nan", "nat", "none", "null"}


def _get_dt(val):
    """Return pd.Timestamp if already datetime/TS, else try your custom parser, else None."""
    if isinstance(val, (datetime, pd.Timestamp)):
        return pd.Timestamp(val)
    return clean_and_parse_date(str(val))


def _fmt_date(d):
    return f"{d.strftime('%A')}, {d.strftime('%m/%d')}" if d is not None else None


# =========================================================
# 🗓️ Friday Announcement Generator
# =========================================================
def generate_friday_messages(df, track, friday_date, section=None):
    import streamlit as st

    def get_custom_project_due_date(milestone_title, section_code, track, override_dict):
        if not milestone_title or not section_code or not track:
            return None
        if not isinstance(milestone_title, str):
            return None

        milestone_key = milestone_title.strip().lower()
        section_full = f"{track} Section {section_code}".strip().lower()

        for (dict_section, dict_title), due_date in override_dict.items():
            if (
                dict_section.strip().lower() == section_full and
                dict_title.strip().lower() == milestone_key
            ):
                return due_date
        return None

    # Parse/adjust Friday date
    if isinstance(friday_date, str):
        try:
            friday_date = datetime.strptime(friday_date, "%m-%d-%Y")
        except ValueError:
            st.warning("⚠️ Invalid date format. Use MM-DD-YYYY.")
            return

    if friday_date.weekday() != 4:
        st.warning(f"⚠️ {add_ordinal_suffix(friday_date)} is not a Friday.")
        friday_date = adjust_to_most_recent_friday(friday_date)
        st.info(f"🔄 Adjusted to most recent Friday: {add_ordinal_suffix(friday_date)}")

    # Filter by track/section
    df = df[df["track"] == track]
    sections_to_process = [section] if section else df["wave_section"].unique()

    for sec in sections_to_process:
        section_df = df[df["wave_section"] == sec]
        upcoming = section_df[section_df["date"] > friday_date].sort_values("date")
        past = section_df[section_df["date"] <= friday_date].sort_values("date", ascending=False)

        if past.empty:
            st.error(f"❌ No past LiveLabs for section {sec}.")
            continue

        last = past.iloc[0]
        last_ll_num = last["LL_num"]
        last_ll_title = last["livelab_title"]
        last_ll_date = last["date"]

        next_lab = upcoming.iloc[0] if not upcoming.empty else None
        if next_lab is not None:
            next_ll_num = next_lab["LL_num"]
            next_ll_title = next_lab["livelab_title"] if pd.notna(next_lab["livelab_title"]) else "an upcoming LiveLab"
            next_ll_date = next_lab["date"]
            next_ll_description = next_lab["notes"] if pd.notna(next_lab["notes"]) else "No description available 😅"
            skillbuilder_before = next_lab["videos_watch_by"] if pd.notna(next_lab["videos_watch_by"]) else None
        else:
            next_ll_num = next_ll_title = next_ll_date = next_ll_description = skillbuilder_before = None

        future_skillbuilder = upcoming[upcoming["videos_watch_by"].notna()].iloc[0] if not upcoming[upcoming["videos_watch_by"].notna()].empty else None
        future_skillbuilder_name = future_skillbuilder["videos_watch_by"] if future_skillbuilder is not None else None
        future_skillbuilder_ll = future_skillbuilder["LL_num"] if future_skillbuilder is not None else None
        future_skillbuilder_date = future_skillbuilder["date"] if future_skillbuilder is not None else None

        milestone_due = last.get("assignment_due_after", None)
        milestone_due_date = None

        # 👉 Try to override with custom project due date
        override_due = get_custom_project_due_date(milestone_due, sec, track, PROJECT_DUE_DATES)
        if override_due:
            milestone_due_date = override_due
        else:
            if pd.notna(milestone_due):
                due_days = get_milestone_due_days(sec)
                for day in due_days:
                    idx = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
                    possible_due = last_ll_date + timedelta((idx - last_ll_date.weekday()) % 7)
                    if milestone_due_date is None or possible_due < milestone_due_date:
                        milestone_due_date = possible_due

        next_milestone_lab = upcoming[upcoming["assignment_due_after"].notna()].iloc[0] if not upcoming[upcoming["assignment_due_after"].notna()].empty else None
        next_milestone = next_milestone_due_date = None
        if next_milestone_lab is not None:
            next_milestone = next_milestone_lab["assignment_due_after"]
            base_date = next_milestone_lab["date"]
            # 🧠 Check for override for future milestone too
            override_next_due = get_custom_project_due_date(next_milestone, sec, track, PROJECT_DUE_DATES)
            if override_next_due:
                next_milestone_due_date = override_next_due
            else:
                due_days = get_milestone_due_days(sec)
                for day in due_days:
                    idx = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
                    possible_due = base_date + timedelta((idx - base_date.weekday()) % 7)
                    if next_milestone_due_date is None or possible_due < next_milestone_due_date:
                        next_milestone_due_date = possible_due

        # ---------- Streamlit block ----------
        with st.expander(f"📢 Post on **:blue[{add_ordinal_suffix(friday_date)}]**"):
            st.warning(
                f'**INSTRUCTOR SANITY CHECK**: The most recent LiveLab was **{last_ll_num}: {last_ll_title}** on {add_ordinal_suffix(last_ll_date)}',
                icon="🔎"
            )
            st.markdown("""### Hey everyone! 👋

Thanks for hanging out with me in lab this week! Here's what's coming up ⬇️
""")
            if milestone_due and milestone_due_date and (next_ll_date is None or milestone_due_date <= next_ll_date):
                st.markdown(f"🎯 **Don't forget!** **:green[{milestone_due}]** is due on **{add_ordinal_suffix(milestone_due_date)}**. Swing by a drop-in session or reach out to the HelpHub with any questions!")
            elif next_milestone and next_milestone_due_date:
                st.markdown(f"🔜 **Heads up!** Your next milestone, {next_milestone}, is due on **{add_ordinal_suffix(next_milestone_due_date)}**.")
            else:
                st.markdown("ℹ️ No scheduled milestones to announce.")

            if next_lab is not None:
                if str(next_ll_title).strip().lower() == "holiday":
                    st.markdown(f"🎉 The next scheduled day, **{add_ordinal_suffix(next_ll_date)}**, is a holiday — there will be no LiveLab that day. Enjoy your break!")
                else:
                    st.markdown(f"⏭️ Your next LiveLab is **{next_ll_title}** on **{add_ordinal_suffix(next_ll_date)}**. {next_ll_description}")
                    if skillbuilder_before:
                        st.markdown(f"🍿 To prepare, please be sure to watch **:blue[{skillbuilder_before}]** before then.")
                    elif future_skillbuilder_name and future_skillbuilder_ll:
                        st.markdown(f"📌 While there's no SkillBuilder due before the next LiveLab, your next one will be **{future_skillbuilder_name}** for {future_skillbuilder_ll} on **{add_ordinal_suffix(future_skillbuilder_date)}**.")
                    else:
                        st.markdown("📌 No upcoming SkillBuilders found in the schedule.")
            else:
                st.markdown("⏭️ No upcoming LiveLabs scheduled.")

            st.markdown("Have a wonderful weekend, and see you all next week!")


# =========================================================
# 🧩 Split into Part 1 & Part 2 by LL reset (LL restarts at 1)
# =========================================================
def split_by_part_ll_reset(df: pd.DataFrame, max_parts: int = 2):
    """
    Split a schedule into sequential parts, flipping to the next part the first
    time LL_num resets downward (e.g., 12 -> 1). Handles real datetimes or
    'Monday, 09/01 ...' strings.

    Returns: (part1_df, part2_df)
    """
    out = df.copy()

    # numeric LL index (NaN if missing)
    if "LL_num" in out.columns:
        out["ll_index"] = (
            out["LL_num"].astype(str).str.extract(r"(\d+)", expand=False).astype(float)
        )
    else:
        out["ll_index"] = pd.Series([float("nan")] * len(out))

    # robust date -> Timestamp/NaT
    out["_dt"] = (
        out["date"].apply(lambda v: pd.Timestamp(v) if isinstance(v, (pd.Timestamp, datetime)) else (_get_dt(v) or pd.NaT))
        if "date" in out.columns else pd.NaT
    )

    # keep original order as tie-breaker; stable sort avoids RangeIndex KeyError
    out = out.reset_index(drop=False).rename(columns={"index": "_orig_order"})
    out = out.sort_values(by=["_dt", "_orig_order"], kind="stable").reset_index(drop=True)

    # walk rows; bump part when LL resets downward (e.g., 12 -> 1)
    part = 1
    prev_ll = None
    parts = []
    for ll in out["ll_index"]:
        if prev_ll is not None and pd.notna(ll):
            if ll < prev_ll and part < max_parts:
                part += 1
        parts.append(part)
        if pd.notna(ll):
            prev_ll = ll

    out["part"] = parts

    p1 = out[out["part"] == 1].drop(columns=["_dt", "_orig_order", "ll_index", "part"], errors="ignore")
    p2 = out[out["part"] == 2].drop(columns=["_dt", "_orig_order", "ll_index", "part"], errors="ignore")
    return p1, p2


# =========================================================
# 🧾 Watch-by Markdown builders
# =========================================================
def _build_watch_markdown_core(df_part: pd.DataFrame, intro_header: str, intro_body: str) -> str:
    """
    Core builder used by both parts. No splitting on '&'.
    Skips rows where videos_watch_by or livelab_title is empty.
    """
    closing = (
        "Remember, your Watched Video Lesson score is the percentage of assigned SkillBuilder "
        "videos you've completed so far. It updates once a day to help you keep track of your progress."
    )

    lines = []
    for _, row in df_part.iterrows():
        vids = row.get("videos_watch_by")
        livelab = row.get("livelab_title")
        if _is_empty(vids) or _is_empty(livelab):
            continue

        dt = _get_dt(row.get("date"))
        notes = str(row.get("notes", "") or "")
        is_holiday = "holiday" in str(livelab).lower() or "no livelab" in notes.lower()
        has_ll = not _is_empty(row.get("LL_num"))

        if is_holiday and _fmt_date(dt):
            when = f"by {_fmt_date(dt)} (no LiveLab but this will help you stay on track!)"
        elif has_ll and _fmt_date(dt):
            when = f"by LiveLab on {_fmt_date(dt)}"
        elif _fmt_date(dt):
            when = f"by {_fmt_date(dt)}"
        else:
            when = "ASAP if you haven't yet!"

        lines.append(f"- Watch {str(vids).strip()} {when}")

    return "\n\n".join([intro_header, intro_body, "**📆 SkillBuilder Schedule**", "\n".join(lines), closing])


def build_watch_markdown_part1(df_part: pd.DataFrame) -> str:
    intro_header = "### Hey everyone! 👋"
    intro_body = (
        "As promised, here is this handy guide for when your SkillBuilders should be viewed before each LiveLab. "
        "Please use this as a reference, but don't you worry, the Team and I will remind you as we go. "
        "The date you see is the date you need to have seen them by! Remember: you can always come back and "
        "watch these videos to make up your Watched Video Lecture score!"
    )
    return _build_watch_markdown_core(df_part, intro_header, intro_body)


def build_watch_markdown_part2(df_part: pd.DataFrame) -> str:
    intro_header = "### Welcome back! 👋"
    intro_body = (
        "Time to switch gears into the next phase of this experience! "
        "Below is your new watch-by guide. The date shown is your deadline "
        "to be ready before each LiveLab."
    )
    return _build_watch_markdown_core(df_part, intro_header, intro_body)


# =========================================================
# 📝 End-of-LiveLab Reminders
# =========================================================
def render_end_of_livelab_reminders(df, track=None, section=None):
    """
    Streamlit expanders:
      'At the end of <LiveLab Name>' showing:
        • SkillBuilder to watch before the next LiveLab (or head-start suggestion)
        • Milestone due before the next LiveLab (with computed due date)
    """
    import streamlit as st
    from datetime import timedelta

    def _is_holiday(row):
        return "holiday" in str(row.get("livelab_title", "")).lower() or \
               "no livelab" in str(row.get("notes", "")).lower()

    def _override_due(milestone_title, section_code, track_name):
        if _is_empty(milestone_title) or _is_empty(section_code) or _is_empty(track_name):
            return None
        key_title = str(milestone_title).strip().lower()
        key_section = f"{track_name} Section {section_code}".strip().lower()
        for (dict_section, dict_title), due in PROJECT_DUE_DATES.items():
            if dict_section.strip().lower() == key_section and dict_title.strip().lower() == key_title:
                return due
        return None

    def _compute_due_date(base_date, section_code, milestone_title, track_name):
        override = _override_due(milestone_title, section_code, track_name)
        if override:
            return override
        if _is_empty(milestone_title) or base_date is None:
            return None
        days = get_milestone_due_days(section_code) or []
        best = None
        for day in days:
            idx = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].index(day)
            cand = base_date + timedelta((idx - base_date.weekday()) % 7)
            if best is None or cand < best:
                best = cand
        return best

    # scope to current track/section if provided
    _df = df.copy()
    if track is not None:
        _df = _df[_df["track"] == track]
    if section is not None:
        if "wave_section" in _df.columns:
            _df = _df[_df["wave_section"] == section]
        elif "section" in _df.columns:
            _df = _df[_df["section"] == section]

    # sort & keep only real (non-holiday) labs with titles
    _df["_dt"] = _df["date"].apply(_get_dt)
    sched = (
        _df.sort_values("_dt")
            .loc[~_df.apply(_is_holiday, axis=1)]
            .loc[~_df["livelab_title"].apply(_is_empty)]
            .reset_index(drop=True)
    )
    if sched.empty:
        st.info("No LiveLabs found to build end-of-lab reminders.")
        return

    for i in range(len(sched)):
        row = sched.iloc[i]
        curr_title = row["livelab_title"]
        curr_date  = row["_dt"]
        sec_code   = str(row.get("wave_section", row.get("section", "")))
        track_name = str(row.get("track", ""))

        # find next non-holiday lab
        next_row = sched.iloc[i+1] if i+1 < len(sched) else None
        next_title = next_row["livelab_title"] if next_row is not None else None
        next_date  = _get_dt(next_row["date"]) if next_row is not None else None

        bullets = []

        # -------- SkillBuilder due before next LL --------
        if next_row is not None:
            sb_due = next_row.get("videos_watch_by")
            if not _is_empty(sb_due):
                bullets.append(f"🎬 **Watch** *{str(sb_due).strip()}* **before** **LL: {next_title}** on **{add_ordinal_suffix(next_date)}**.")
            else:
                # head start on first later SB
                later = None
                for j in range(i+2, len(sched)):
                    r = sched.iloc[j]
                    if not _is_empty(r.get("videos_watch_by")):
                        later = r
                        break
                if later is not None:
                    bullets.append(
                        f"🎬 No SkillBuilder due before the next LiveLab — **get a head start** on "
                        f"_{later['videos_watch_by']}_ (you’ll want this before **LL: {later['livelab_title']}** on "
                        f"**{add_ordinal_suffix(_get_dt(later['date']))}**)."
                    )
        else:
            bullets.append("🎬 No upcoming LiveLab — you’re at the end of the schedule. 🎉")

        # -------- Milestone due before next LL --------
        ms_title = row.get("assignment_due_after")
        ms_due   = _compute_due_date(curr_date, sec_code, ms_title, track_name) if not _is_empty(ms_title) else None

        if ms_due is not None and (next_date is None or ms_due <= next_date):
            bullets.append(f"📌 **Milestone:** _{ms_title}_ is due **{add_ordinal_suffix(ms_due)}**.")
        else:
            # head start on next milestone
            later_ms = None
            for j in range(i+1, len(sched)):
                r = sched.iloc[j]
                if not _is_empty(r.get("assignment_due_after")):
                    later_ms = r
                    break
            if later_ms is not None:
                lm_title = later_ms["assignment_due_after"]
                lm_due   = _compute_due_date(_get_dt(later_ms["date"]), sec_code, lm_title, track_name)
                if lm_due is not None:
                    bullets.append(f"📌 No milestone due before the next LiveLab — **get a head start** on _{lm_title}_ due **{add_ordinal_suffix(lm_due)}**.")

        # -------- render --------
        with st.expander(f"📝 At the end of :violet[**{row['LL_num']} {curr_title}**] on *{_fmt_date(curr_date)}*"):
            if bullets:
                st.markdown("\n\n".join(f"- {b}" for b in bullets))
            else:
                st.markdown("- Nothing due — nice work! 🎉")

