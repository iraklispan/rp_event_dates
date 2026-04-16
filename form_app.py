import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime

st.set_page_config(page_title="Group & Conference Form", page_icon="🏨", layout="wide")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_sheet():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open("Groups & Conferences Data").sheet1

ROOM_TYPES = [
    "Garden Room","Tower Room Garden View","Tower Room Sea View",
    "ABAV² Room Garden View","ABAV² Room Sea View",
    "Executive Room Garden View","Executive Room Sea View",
    "Executive Suite (Corner)","Junior Suite","Presidential Suite",
    "ABAV² Junior Suite","ABAV² Presidential Suite","ABAV² Royal Suite",
    "Bungalow","ABAV² Bungalow Suite","Garden Suite (Family)",
    "Garden Suite (Loft)","ABAV² Garden Suite",
    "ABAV² Garden Swimup Suite (Shared Pool)",
    "ABAV² Garden Swimup Suite (Exclusive Pool)",
    "ABAV² Maisonette Suite",
    "ABAV² Imperial Suite (Exclusive Pool & Spa)",
    "ABAV² Presidential Villa",
]
RATE_PLANS = ["Breakfast Buffet","Half Board","Full Board","All Inclusive"]
PRICE_COMBOS = ["1+0","2+0","2+1","2+2","3+0","3+1","4+0"]
CANCELLATION_POLICIES = ["Flexible","Night Deposit","Non Refundable"]
SPACE_NAMES = [
    "Delfi","Alpha","Jupiter",
    "Nafsika A","Nafsika B","Nafsika Full",
    "Nefeli A","Nefeli B","Nefeli Full",
    "Salon des Roses A","Salon des Roses B","Salon des Roses Full",
    "Epsilon","Athena","VIP Lounge","Lobby Foyer","Lobby Atrium",
    "Dome","Garden Area","Castellania",
    "12 Nissia Deck","12 Nissia Interior",
    "Main Bar Deck","Main Bar Interior",
    "Terrasse Bar","Terrasse Interior","Terrasse Exterior",
]
SERVICES = [
    "Coffee Break","Dinner","Gala Dinner","Lunch",
    "Aperitivo","Buffet","Farewell Buffet","Party","DJ Party",
]

def render_room(idx):
    st.markdown(f"##### 🛏️ Room Type {idx}")
    c1, c2 = st.columns(2)
    with c1:
        rtype = st.selectbox("Room Type", ROOM_TYPES, key=f"room_type_{idx}")
        rcount = st.number_input("Αριθμός Δωματίων", min_value=1, step=1, key=f"room_count_{idx}")
    with c2:
        rplan = st.selectbox("Rate Plan", RATE_PLANS, key=f"room_rate_{idx}")
    st.markdown("###### Τιμές (Adults+Children)")
    pcols = st.columns(len(PRICE_COMBOS))
    prices = {}
    for i, combo in enumerate(PRICE_COMBOS):
        with pcols[i]:
            v = st.number_input(combo, min_value=0, step=1, value=0, key=f"room_price_{idx}_{combo}")
            prices[combo] = v if v > 0 else None
    return {"type": rtype, "count": rcount, "rate_plan": rplan, "prices": prices}

def render_service(space_idx, svc_idx):
    c1, c2 = st.columns(2)
    with c1:
        svc = st.selectbox(f"Service {svc_idx}", SERVICES, key=f"sp{space_idx}_svc{svc_idx}_type")
    with c2:
        pax = st.number_input("Pax", min_value=1, step=1, key=f"sp{space_idx}_svc{svc_idx}_pax")
    return {"service": svc, "pax": pax}

def render_space(idx):
    st.markdown(f"##### 🏛️ Space {idx}")
    sname = st.selectbox("Space Name", SPACE_NAMES, key=f"space_name_{idx}")
    svc_key = f"svc_count_{idx}"
    if svc_key not in st.session_state:
        st.session_state[svc_key] = 1
    services = [render_service(idx, s) for s in range(1, st.session_state[svc_key] + 1)]
    if st.button(f"➕ Add Service for Space {idx}", key=f"add_svc_{idx}"):
        st.session_state[svc_key] += 1
        st.rerun()
    return {"name": sname, "services": services}

def flatten_row(data):
    row = {
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_by": data["submitted_by"],
        "event_name": data["event_name"],
        "event_start": str(data["event_start"]),
        "event_end": str(data["event_end"]),
        "attendees": data["attendees"],
        "includes_accommodation": data["includes_accommodation"],
    }
    if data["includes_accommodation"]:
        row.update({
            "acc_start": str(data["acc_start"]),
            "acc_end": str(data["acc_end"]),
            "booking_code": data.get("booking_code",""),
            "cut_off_date": str(data.get("cut_off_date","")),
            "cancellation_policy": data.get("cancellation_policy",""),
            "cancellation_days": data.get("cancellation_days",""),
            "deposit_days": data.get("deposit_days",""),
            "minimum_stay": data.get("minimum_stay",""),
        })
        for i, room in enumerate(data.get("rooms",[]), 1):
            p = f"room{i}_"
            row[f"{p}type"] = room["type"]
            row[f"{p}count"] = room["count"]
            row[f"{p}rate_plan"] = room["rate_plan"]
            for combo in PRICE_COMBOS:
                row[f"{p}price_{combo.replace('+','_')}"] = room["prices"].get(combo) or ""
    else:
        for f in ["acc_start","acc_end","booking_code","cut_off_date",
                  "cancellation_policy","cancellation_days","deposit_days","minimum_stay"]:
            row[f] = ""
    row["includes_meeting_spaces"] = data["includes_meeting_spaces"]
    if data["includes_meeting_spaces"]:
        for i, space in enumerate(data.get("spaces",[]), 1):
            row[f"space{i}_name"] = space["name"]
            for j, svc in enumerate(space.get("services",[]), 1):
                row[f"space{i}_service{j}_type"] = svc["service"]
                row[f"space{i}_service{j}_pax"] = svc["pax"]
    return row

def ensure_headers(sheet, row):
    if not sheet.row_values(1):
        sheet.append_row(list(row.keys()))

def main():
    st.title("🏨 Group & Conference Entry Form")

    for k, v in [("room_count",1),("space_count",1),("submitted",False)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.submitted:
        st.success("✅ Η εγγραφή υποβλήθηκε επιτυχώς!")
        if st.button("➕ Νέα Εγγραφή"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    st.header("📋 Βασικά Στοιχεία")
    submitted_by = st.text_input("Όνομα Χρήστη *", placeholder="π.χ. Μαρία Παπαδοπούλου")
    c1, c2 = st.columns(2)
    with c1:
        event_name = st.text_input("Όνομα Event *", placeholder="π.χ. ΣΥΝΕΔΡΙΟ ROTARY 2026")
    with c2:
        attendees = st.number_input("Αριθμός Συμμετεχόντων", min_value=0, step=1)
    c3, c4 = st.columns(2)
    with c3:
        event_start = st.date_input("Ημερομηνία Έναρξης *", value=date.today())
    with c4:
        event_end = st.date_input("Ημερομηνία Λήξης *", value=date.today())

    st.divider()
    st.header("🛏️ Διαμονή")
    includes_accommodation = st.toggle("Περιλαμβάνει Διαμονή;")

    rooms_data, acc_start, acc_end = [], None, None
    booking_code = cut_off_date = cancellation_policy = None
    cancellation_days = deposit_days = minimum_stay = None

    if includes_accommodation:
        c1, c2 = st.columns(2)
        with c1:
            acc_start = st.date_input("Check-in *", value=event_start, key="acc_start")
        with c2:
            acc_end = st.date_input("Check-out *", value=event_end, key="acc_end")
        st.markdown("#### Τύποι Δωματίων")
        for r in range(1, st.session_state.room_count + 1):
            with st.container(border=True):
                rooms_data.append(render_room(r))
        if st.button("➕ Προσθήκη Room Type"):
            st.session_state.room_count += 1
            st.rerun()
        st.divider()
        st.markdown("#### 📄 Όροι Κράτησης")
        c1, c2 = st.columns(2)
        with c1:
            booking_code = st.text_input("Booking Code")
            cancellation_policy = st.selectbox("Cancellation Policy", CANCELLATION_POLICIES)
        with c2:
            cut_off_date = st.date_input("Cut-off Date", value=None)
            minimum_stay = st.number_input("Minimum Stay (νύχτες)", min_value=0, step=1)
        if cancellation_policy == "Flexible":
            cancellation_days = st.number_input("Δωρεάν ακύρωση έως (μέρες πριν)", min_value=0, step=1, key="cancel_days")
        elif cancellation_policy == "Night Deposit":
            deposit_days = st.number_input("Deposit (νύχτες)", min_value=0, step=1, key="deposit_days_input")

    st.divider()
    st.header("🏛️ Χώροι & Υπηρεσίες")
    includes_meeting_spaces = st.toggle("Περιλαμβάνει Χώρους / Events;")

    spaces_data = []
    if includes_meeting_spaces:
        for sp in range(1, st.session_state.space_count + 1):
            with st.container(border=True):
                spaces_data.append(render_space(sp))
        if st.button("➕ Προσθήκη Space"):
            st.session_state.space_count += 1
            st.rerun()

    st.divider()
    st.header("📤 Υποβολή")
    errors = []
    if not submitted_by:
        errors.append("Το πεδίο 'Όνομα Χρήστη' είναι υποχρεωτικό.")
    if not event_name:
        errors.append("Το πεδίο 'Όνομα Event' είναι υποχρεωτικό.")
    if event_end < event_start:
        errors.append("Η ημερομηνία λήξης δεν μπορεί να είναι πριν την έναρξη.")
    for e in errors:
        st.warning(e)

    if st.button("💾 Αποθήκευση", type="primary", disabled=bool(errors)):
        data = {
            "submitted_by": submitted_by, "event_name": event_name,
            "event_start": event_start, "event_end": event_end,
            "attendees": attendees, "includes_accommodation": includes_accommodation,
            "acc_start": acc_start, "acc_end": acc_end, "rooms": rooms_data,
            "booking_code": booking_code, "cut_off_date": cut_off_date,
            "cancellation_policy": cancellation_policy,
            "cancellation_days": cancellation_days, "deposit_days": deposit_days,
            "minimum_stay": minimum_stay, "includes_meeting_spaces": includes_meeting_spaces,
            "spaces": spaces_data,
        }
        try:
            with st.spinner("Αποθήκευση..."):
                sheet = get_sheet()
                row = flatten_row(data)
                ensure_headers(sheet, row)
                sheet.append_row(list(row.values()))
            st.session_state.submitted = True
            st.rerun()
        except Exception as ex:
            st.error(f"❌ Σφάλμα: {ex}")

if __name__ == "__main__":
    main()
