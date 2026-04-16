"""
shared.py — Κοινός κώδικας για form_app.py και dashboard_app.py
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
SHEET_NAME = "Groups & Conferences Data"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

PRICE_COMBOS = ["1+0", "2+0", "2+1", "2+2", "3+0", "3+1", "4+0"]

COLOR_PALETTE = [
    "#4C9BE8", "#F28C38", "#5DBB8A", "#E8637A", "#A78BFA",
    "#F59E0B", "#34D399", "#60A5FA", "#F472B6", "#38BDF8",
    "#FB923C", "#A3E635", "#E879F9", "#2DD4BF", "#FCA5A5",
    "#93C5FD", "#6EE7B7", "#FCD34D", "#C4B5FD", "#86EFAC",
]

ROOM_TYPES = [
    "Garden Room",
    "Tower Room Garden View",
    "Tower Room Sea View",
    "ABAV² Room Garden View",
    "ABAV² Room Sea View",
    "Executive Room Garden View",
    "Executive Room Sea View",
    "Executive Suite (Corner)",
    "Junior Suite",
    "Presidential Suite",
    "ABAV² Junior Suite",
    "ABAV² Presidential Suite",
    "ABAV² Royal Suite",
    "Bungalow",
    "ABAV² Bungalow Suite",
    "Garden Suite (Family)",
    "Garden Suite (Loft)",
    "ABAV² Garden Suite",
    "ABAV² Garden Swimup Suite (Shared Pool)",
    "ABAV² Garden Swimup Suite (Exclusive Pool)",
    "ABAV² Maisonette Suite",
    "ABAV² Imperial Suite (Exclusive Pool & Spa)",
    "ABAV² Presidential Villa",
]

RATE_PLANS = [
    "Breakfast Buffet",
    "Half Board",
    "Full Board",
    "All Inclusive",
]

CANCELLATION_POLICIES = [
    "Flexible",
    "Night Deposit",
    "Non Refundable",
]

SPACE_NAMES = [
    "Delfi",
    "Alpha",
    "Jupiter",
    "Nafsika A",
    "Nafsika B",
    "Nafsika Full",
    "Nefeli A",
    "Nefeli B",
    "Nefeli Full",
    "Salon des Roses A",
    "Salon des Roses B",
    "Salon des Roses Full",
    "Epsilon",
    "Athena",
    "VIP Lounge",
    "Lobby Foyer",
    "Lobby Atrium",
    "Dome",
    "Garden Area",
    "Castellania",
    "12 Nissia Deck",
    "12 Nissia Interior",
    "Main Bar Deck",
    "Main Bar Interior",
    "Terrasse Bar",
    "Terrasse Interior",
    "Terrasse Exterior",
]

SERVICES = [
    "Coffee Break",
    "Dinner",
    "Gala Dinner",
    "Lunch",
    "Aperitivo",
    "Buffet",
    "Farewell Buffet",
    "Party",
    "DJ Party",
]


# ─────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────
def get_sheet():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1


def build_header():
    cols = [
        "submitted_at", "submitted_by",
        "event_name", "event_start", "event_end", "attendees",
        "includes_accommodation", "acc_start", "acc_end",
    ]
    for i in range(1, 11):
        cols += [f"room{i}_type", f"room{i}_count", f"room{i}_rate_plan"]
        for combo in PRICE_COMBOS:
            cols.append(f"room{i}_price_{combo.replace('+', '_')}")
    cols += [
        "booking_code", "cut_off_date",
        "cancellation_policy", "cancellation_days", "deposit_days",
        "minimum_stay", "includes_meeting_spaces",
    ]
    for i in range(1, 11):
        cols.append(f"space{i}_name")
        for j in range(1, 11):
            cols += [f"space{i}_service{j}_type", f"space{i}_service{j}_pax"]
    return cols


def ensure_header(sheet):
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "submitted_at":
        sheet.insert_row(build_header(), 1)


@st.cache_data(ttl=60)
def load_data():
    """Load all rows, return only the latest version of each event_name."""
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for col in ["event_start", "event_end", "acc_start", "acc_end", "cut_off_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")
    # Keep only the latest version per event
    df = df.sort_values("submitted_at").groupby("event_name", as_index=False).last()
    return df


def append_row(row_data: list):
    sheet = get_sheet()
    ensure_header(sheet)
    sheet.append_row(row_data, value_input_option="USER_ENTERED")
    # Clear cache so dashboard reloads fresh data
    load_data.clear()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def event_color(idx: int) -> str:
    return COLOR_PALETTE[idx % len(COLOR_PALETTE)]


def count_rooms(row) -> int:
    total = 0
    for i in range(1, 11):
        col = f"room{i}_type"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            total += int(row.get(f"room{i}_count", 0) or 0)
    return total


def count_spaces(row) -> int:
    total = 0
    for i in range(1, 11):
        col = f"space{i}_name"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            total += 1
    return total


def num_days(row) -> int:
    try:
        return (row["event_end"] - row["event_start"]).days
    except Exception:
        return 0


def safe_date(val) -> date:
    """Convert a value to date safely."""
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return date.today()


def safe_int(val, default=0) -> int:
    try:
        return int(val or default)
    except Exception:
        return default


def safe_str(val, default="") -> str:
    if pd.isna(val) if not isinstance(val, str) else False:
        return default
    return str(val) if val else default


# ─────────────────────────────────────────────
# SHARED FORM STATE INIT
# ─────────────────────────────────────────────
def init_form_state(prefix=""):
    """Initialize session state counters for rooms/spaces."""
    if f"{prefix}num_rooms" not in st.session_state:
        st.session_state[f"{prefix}num_rooms"] = 1
    if f"{prefix}num_spaces" not in st.session_state:
        st.session_state[f"{prefix}num_spaces"] = 1
    if f"{prefix}space_services" not in st.session_state:
        st.session_state[f"{prefix}space_services"] = {1: 1}


def prefill_form_state(row, prefix=""):
    """Pre-fill session state from an existing row (for edit mode)."""
    st.session_state[f"{prefix}submitted_by"] = safe_str(row.get("submitted_by"))
    st.session_state[f"{prefix}event_name"] = safe_str(row.get("event_name"))
    st.session_state[f"{prefix}attendees"] = safe_int(row.get("attendees"))
    st.session_state[f"{prefix}event_start"] = safe_date(row.get("event_start"))
    st.session_state[f"{prefix}event_end"] = safe_date(row.get("event_end"))
    st.session_state[f"{prefix}includes_accommodation"] = str(row.get("includes_accommodation", "")).lower() == "true"
    st.session_state[f"{prefix}acc_start"] = safe_date(row.get("acc_start"))
    st.session_state[f"{prefix}acc_end"] = safe_date(row.get("acc_end"))
    st.session_state[f"{prefix}booking_code"] = safe_str(row.get("booking_code"))
    st.session_state[f"{prefix}cut_off_date"] = safe_date(row.get("cut_off_date"))
    st.session_state[f"{prefix}cancellation_policy"] = safe_str(row.get("cancellation_policy"), "Flexible")
    st.session_state[f"{prefix}cancellation_days"] = safe_int(row.get("cancellation_days"))
    st.session_state[f"{prefix}deposit_days"] = safe_int(row.get("deposit_days"))
    st.session_state[f"{prefix}minimum_stay"] = safe_int(row.get("minimum_stay"))
    st.session_state[f"{prefix}includes_meeting_spaces"] = str(row.get("includes_meeting_spaces", "")).lower() == "true"

    # Rooms
    num_rooms = 0
    for i in range(1, 11):
        rtype = safe_str(row.get(f"room{i}_type"))
        if not rtype:
            break
        num_rooms = i
        st.session_state[f"{prefix}room{i}_type"] = rtype
        st.session_state[f"{prefix}room{i}_count"] = safe_int(row.get(f"room{i}_count"), 1)
        st.session_state[f"{prefix}room{i}_rate_plan"] = safe_str(row.get(f"room{i}_rate_plan"), RATE_PLANS[0])
        for combo in PRICE_COMBOS:
            k = f"room{i}_price_{combo.replace('+', '_')}"
            st.session_state[f"{prefix}{k}"] = safe_int(row.get(k), 0)
    st.session_state[f"{prefix}num_rooms"] = max(num_rooms, 1)

    # Spaces
    num_spaces = 0
    space_services = {}
    for i in range(1, 11):
        sname = safe_str(row.get(f"space{i}_name"))
        if not sname:
            break
        num_spaces = i
        st.session_state[f"{prefix}space{i}_name"] = sname
        num_sv = 0
        for j in range(1, 11):
            stype = safe_str(row.get(f"space{i}_service{j}_type"))
            if not stype:
                break
            num_sv = j
            st.session_state[f"{prefix}space{i}_service{j}_type"] = stype
            st.session_state[f"{prefix}space{i}_service{j}_pax"] = safe_int(row.get(f"space{i}_service{j}_pax"))
        space_services[i] = max(num_sv, 1)
    st.session_state[f"{prefix}num_spaces"] = max(num_spaces, 1)
    st.session_state[f"{prefix}space_services"] = space_services if space_services else {1: 1}


# ─────────────────────────────────────────────
# SHARED FORM UI
# ─────────────────────────────────────────────
def render_room_block(idx, prefix=""):
    with st.container(border=True):
        st.markdown(f"**🛏️ Room Type {idx}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.selectbox("Room Type", ROOM_TYPES, key=f"{prefix}room{idx}_type")
        with c2:
            st.number_input("Number of Rooms", min_value=1, step=1, value=1, key=f"{prefix}room{idx}_count")
        with c3:
            st.selectbox("Rate Plan", RATE_PLANS, key=f"{prefix}room{idx}_rate_plan")

        st.markdown("**Τιμές (€) — συμπλήρωσε όσα ισχύουν:**")
        pcols = st.columns(len(PRICE_COMBOS))
        for ci, combo in enumerate(PRICE_COMBOS):
            with pcols[ci]:
                st.number_input(
                    combo, min_value=0, step=1, value=0,
                    key=f"{prefix}room{idx}_price_{combo.replace('+', '_')}",
                )


def render_space_block(s_idx, prefix=""):
    with st.container(border=True):
        st.markdown(f"**🏛️ Space {s_idx}**")
        st.selectbox("Space Name", SPACE_NAMES, key=f"{prefix}space{s_idx}_name")

        num_sv = st.session_state[f"{prefix}space_services"].get(s_idx, 1)
        for sv_idx in range(1, num_sv + 1):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.selectbox(f"Service {sv_idx}", SERVICES, key=f"{prefix}space{s_idx}_service{sv_idx}_type")
            with c2:
                st.number_input(f"Pax {sv_idx}", min_value=0, step=1, key=f"{prefix}space{s_idx}_service{sv_idx}_pax")

        if st.button("➕ Add Service", key=f"{prefix}add_service_{s_idx}"):
            st.session_state[f"{prefix}space_services"][s_idx] = num_sv + 1
            st.rerun()


def render_event_form(prefix="", submit_label="💾 Save Event"):
    """
    Full event form. Returns True if submitted successfully.
    prefix: used to namespace session state keys (useful for edit form in dashboard).
    """
    init_form_state(prefix)

    # ── 1. Basic Info ────────────────────────
    st.subheader("1. Basic Information")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Your Name *", key=f"{prefix}submitted_by")
        st.text_input("Event Name *", key=f"{prefix}event_name")
        st.number_input("Number of Attendees", min_value=1, step=1, key=f"{prefix}attendees")
    with c2:
        st.date_input("Event Start Date *", key=f"{prefix}event_start")
        st.date_input("Event End Date *", key=f"{prefix}event_end")

    st.divider()

    # ── 2. Accommodation ─────────────────────
    st.subheader("2. Accommodation")
    incl_acc = st.toggle("Includes Accommodation", key=f"{prefix}includes_accommodation")

    if incl_acc:
        c1, c2 = st.columns(2)
        with c1:
            st.date_input("Check-in Date", key=f"{prefix}acc_start")
        with c2:
            st.date_input("Check-out Date", key=f"{prefix}acc_end")

        st.markdown("#### Room Types")
        num_rooms = st.session_state[f"{prefix}num_rooms"]
        for i in range(1, num_rooms + 1):
            render_room_block(i, prefix)

        if st.button("➕ Add Another Room Type", key=f"{prefix}add_room"):
            st.session_state[f"{prefix}num_rooms"] += 1
            st.rerun()

        st.markdown("#### Booking Terms")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Booking Code", key=f"{prefix}booking_code")
            st.number_input("Minimum Stay (nights)", min_value=0, step=1, key=f"{prefix}minimum_stay")
        with c2:
            st.date_input("Cut-off Date", key=f"{prefix}cut_off_date")
        with c3:
            cancel_policy = st.selectbox(
                "Cancellation Policy", CANCELLATION_POLICIES,
                key=f"{prefix}cancellation_policy",
            )

        if cancel_policy == "Flexible":
            st.number_input(
                "Free cancellation up to X days before arrival",
                min_value=0, step=1, key=f"{prefix}cancellation_days",
            )
        elif cancel_policy == "Night Deposit":
            st.number_input(
                "Deposit required X days before arrival",
                min_value=0, step=1, key=f"{prefix}deposit_days",
            )

    st.divider()

    # ── 3. Meeting Spaces ────────────────────
    st.subheader("3. Meeting Spaces & Events")
    incl_spaces = st.toggle("Includes Meeting Spaces / Events", key=f"{prefix}includes_meeting_spaces")

    if incl_spaces:
        num_spaces = st.session_state[f"{prefix}num_spaces"]
        for s_idx in range(1, num_spaces + 1):
            render_space_block(s_idx, prefix)

        if st.button("➕ Add Another Space", key=f"{prefix}add_space"):
            new_idx = st.session_state[f"{prefix}num_spaces"] + 1
            st.session_state[f"{prefix}num_spaces"] = new_idx
            st.session_state[f"{prefix}space_services"][new_idx] = 1
            st.rerun()

    st.divider()

    # ── Submit ───────────────────────────────
    if st.button(submit_label, type="primary", use_container_width=True, key=f"{prefix}submit_btn"):
        errors = []
        if not st.session_state.get(f"{prefix}submitted_by", "").strip():
            errors.append("Το όνομά σου είναι υποχρεωτικό.")
        if not st.session_state.get(f"{prefix}event_name", "").strip():
            errors.append("Το όνομα του event είναι υποχρεωτικό.")
        if errors:
            for e in errors:
                st.error(e)
            return False

        row = build_row_from_state(prefix, incl_acc, incl_spaces)
        with st.spinner("Αποθήκευση..."):
            try:
                append_row(row)
                return True
            except Exception as e:
                st.error(f"❌ Σφάλμα: {e}")
                return False

    return False


# ─────────────────────────────────────────────
# BUILD ROW FROM STATE
# ─────────────────────────────────────────────
def build_row_from_state(prefix, incl_acc, incl_spaces):
    header = build_header()
    row = {col: "" for col in header}

    row["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row["submitted_by"] = st.session_state.get(f"{prefix}submitted_by", "")
    row["event_name"] = st.session_state.get(f"{prefix}event_name", "")
    row["event_start"] = str(st.session_state.get(f"{prefix}event_start", ""))
    row["event_end"] = str(st.session_state.get(f"{prefix}event_end", ""))
    row["attendees"] = st.session_state.get(f"{prefix}attendees", "")
    row["includes_accommodation"] = str(incl_acc)

    if incl_acc:
        row["acc_start"] = str(st.session_state.get(f"{prefix}acc_start", ""))
        row["acc_end"] = str(st.session_state.get(f"{prefix}acc_end", ""))
        for i in range(1, st.session_state[f"{prefix}num_rooms"] + 1):
            row[f"room{i}_type"] = st.session_state.get(f"{prefix}room{i}_type", "")
            row[f"room{i}_count"] = st.session_state.get(f"{prefix}room{i}_count", "")
            row[f"room{i}_rate_plan"] = st.session_state.get(f"{prefix}room{i}_rate_plan", "")
            for combo in PRICE_COMBOS:
                k = f"room{i}_price_{combo.replace('+', '_')}"
                row[k] = st.session_state.get(f"{prefix}{k}", 0)
        row["booking_code"] = st.session_state.get(f"{prefix}booking_code", "")
        row["cut_off_date"] = str(st.session_state.get(f"{prefix}cut_off_date", ""))
        row["cancellation_policy"] = st.session_state.get(f"{prefix}cancellation_policy", "")
        row["cancellation_days"] = st.session_state.get(f"{prefix}cancellation_days", "")
        row["deposit_days"] = st.session_state.get(f"{prefix}deposit_days", "")
        row["minimum_stay"] = st.session_state.get(f"{prefix}minimum_stay", "")

    row["includes_meeting_spaces"] = str(incl_spaces)

    if incl_spaces:
        for s_idx in range(1, st.session_state[f"{prefix}num_spaces"] + 1):
            row[f"space{s_idx}_name"] = st.session_state.get(f"{prefix}space{s_idx}_name", "")
            num_sv = st.session_state[f"{prefix}space_services"].get(s_idx, 1)
            for sv_idx in range(1, num_sv + 1):
                row[f"space{s_idx}_service{sv_idx}_type"] = st.session_state.get(
                    f"{prefix}space{s_idx}_service{sv_idx}_type", ""
                )
                row[f"space{s_idx}_service{sv_idx}_pax"] = st.session_state.get(
                    f"{prefix}space{s_idx}_service{sv_idx}_pax", ""
                )

    return [row[col] for col in header]