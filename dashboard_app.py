import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import hashlib

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


@st.cache_data(ttl=60)
def load_data():
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
    return df


def event_color(idx):
    return COLOR_PALETTE[idx % len(COLOR_PALETTE)]


def count_rooms(row):
    total = 0
    for i in range(1, 11):
        col = f"room{i}_type"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            total += int(row.get(f"room{i}_count", 0) or 0)
    return total


def count_spaces(row):
    total = 0
    for i in range(1, 11):
        col = f"space{i}_name"
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            total += 1
    return total


def num_days(row):
    try:
        return (row["event_end"] - row["event_start"]).days
    except Exception:
        return 0


def render_client_card(row, color):
    st.markdown(
        f"""<div style="border-left:5px solid {color};padding:0.6rem 1.2rem;
        background:#f8fafc;border-radius:8px;margin-bottom:1rem;">
        <h3 style="margin:0;color:#1e293b;">{row['event_name']}</h3>
        <p style="margin:0;color:#64748b;">Submitted by <b>{row.get('submitted_by','—')}</b></p>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.expander("📌 General Information", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Start", row["event_start"].strftime("%d/%m/%Y") if pd.notna(row["event_start"]) else "—")
        c2.metric("End", row["event_end"].strftime("%d/%m/%Y") if pd.notna(row["event_end"]) else "—")
        c3.metric("Duration", f"{num_days(row)} nights")
        c4.metric("Attendees", int(row.get("attendees", 0) or 0))

    if str(row.get("includes_accommodation", "")).lower() == "true":
        with st.expander("🛏️ Accommodation", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            acc_start = row.get("acc_start")
            acc_end = row.get("acc_end")
            c1.metric("Check-in", acc_start.strftime("%d/%m/%Y") if pd.notna(acc_start) else "—")
            c2.metric("Check-out", acc_end.strftime("%d/%m/%Y") if pd.notna(acc_end) else "—")
            c3.metric("Booking Code", row.get("booking_code") or "—")
            c4.metric("Min Stay", f"{int(row.get('minimum_stay', 0) or 0)} nights")

            policy = row.get("cancellation_policy", "—")
            if policy == "Flexible":
                st.info(f"✅ Flexible — Free cancellation up to **{int(row.get('cancellation_days', 0) or 0)} days** before arrival")
            elif policy == "Night Deposit":
                st.warning(f"💳 Night Deposit — Required **{int(row.get('deposit_days', 0) or 0)} days** before arrival")
            elif policy == "Non Refundable":
                st.error("🔒 Non Refundable")

            cut_off = row.get("cut_off_date")
            if pd.notna(cut_off):
                st.markdown(f"**Cut-off Date:** {cut_off.strftime('%d/%m/%Y')}")

            st.markdown("---")
            st.markdown("**Room Types**")
            room_rows = []
            for i in range(1, 11):
                rtype = row.get(f"room{i}_type", "")
                if not rtype or str(rtype).strip() == "":
                    continue
                prices = {}
                for combo in PRICE_COMBOS:
                    k = f"room{i}_price_{combo.replace('+', '_')}"
                    v = row.get(k, 0)
                    if v and int(v or 0) > 0:
                        prices[combo] = f"€{int(v)}"
                room_rows.append({
                    "Room Type": rtype,
                    "Count": int(row.get(f"room{i}_count", 0) or 0),
                    "Rate Plan": row.get(f"room{i}_rate_plan", "—"),
                    **prices,
                })
            if room_rows:
                st.dataframe(pd.DataFrame(room_rows), use_container_width=True, hide_index=True)

    if str(row.get("includes_meeting_spaces", "")).lower() == "true":
        with st.expander("🏛️ Meeting Spaces & Events", expanded=True):
            for i in range(1, 11):
                sname = row.get(f"space{i}_name", "")
                if not sname or str(sname).strip() == "":
                    continue
                st.markdown(f"**{sname}**")
                services = []
                for j in range(1, 11):
                    stype = row.get(f"space{i}_service{j}_type", "")
                    spax = row.get(f"space{i}_service{j}_pax", 0)
                    if stype and str(stype).strip():
                        services.append({"Service": stype, "Pax": int(spax or 0)})
                if services:
                    st.dataframe(pd.DataFrame(services), use_container_width=True, hide_index=True)


def render_gantt(df_year, year):
    df_plot = df_year.dropna(subset=["event_start", "event_end"]).sort_values("event_start").reset_index(drop=True)
    if df_plot.empty:
        st.info("Δεν υπάρχουν events με έγκυρες ημερομηνίες.")
        return

    fig = go.Figure()

    for idx, row in df_plot.iterrows():
        color = event_color(idx)
        start = row["event_start"]
        end = row["event_end"]
        days = (end - start).days or 1

        hover = (
            f"<b>{row['event_name']}</b><br>"
            f"📅 {start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}<br>"
            f"🌙 {days} nights<br>"
            f"👥 {int(row.get('attendees', 0) or 0)} attendees<br>"
            f"🛏️ {count_rooms(row)} rooms | 🏛️ {count_spaces(row)} spaces"
        )

        fig.add_trace(go.Bar(
            x=[days],
            y=[row["event_name"]],
            base=[start.timestamp() * 1000],
            orientation="h",
            marker_color=color,
            marker_line_color="white",
            marker_line_width=1.5,
            hovertemplate=hover + "<extra></extra>",
            showlegend=False,
        ))

        mid = (start.timestamp() + (end.timestamp() - start.timestamp()) / 2) * 1000
        fig.add_annotation(
            x=mid, y=row["event_name"],
            text=row["event_name"] if days > 3 else "",
            showarrow=False,
            font=dict(color="white", size=11, family="Arial Bold"),
            xref="x", yref="y",
        )

    fig.update_layout(
        height=max(400, len(df_plot) * 50),
        xaxis=dict(
            type="date",
            range=[
                datetime(year, 1, 1).timestamp() * 1000,
                datetime(year, 12, 31).timestamp() * 1000,
            ],
            tickformat="%b",
            dtick="M1",
            showgrid=True,
            gridcolor="#e2e8f0",
            tickfont=dict(size=12),
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=220, r=30, t=50, b=40),
        bargap=0.35,
        title=dict(text=f"Groups & Conferences — {year}", font=dict(size=18)),
    )

    st.plotly_chart(fig, use_container_width=True)


def main():
    st.set_page_config(
        page_title="Groups & Conferences — Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.title("📊 Groups & Conferences Dashboard")

    with st.spinner("Φόρτωση δεδομένων..."):
        df = load_data()

    if df.empty:
        st.warning("Δεν υπάρχουν δεδομένα ακόμα.")
        return

    available_years = sorted(df["event_start"].dropna().dt.year.unique().tolist())
    if not available_years:
        st.warning("Δεν βρέθηκαν έγκυρες ημερομηνίες.")
        return

    selected_year = st.selectbox("📅 Έτος", available_years, index=len(available_years) - 1)
    df_year = df[df["event_start"].dt.year == selected_year].copy().reset_index(drop=True)

    tab1, tab2 = st.tabs(["📋 Events", "📅 Gantt Chart"])

    with tab1:
        st.subheader(f"Events {selected_year}  —  {len(df_year)} total")

        # Header row
        hc = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1, 1, 1])
        for col, label in zip(hc[2:], ["Event", "Start", "End", "Nights", "Attendees", "Rooms", "Spaces"]):
            col.markdown(f"**{label}**")
        st.divider()

        selected_idx = None
        for i, row in df_year.iterrows():
            color = event_color(i)
            cols = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1, 1, 1])
            checked = cols[0].checkbox("", key=f"chk_{i}", label_visibility="collapsed")
            cols[1].markdown(
                f'<div style="width:14px;height:14px;border-radius:50%;background:{color};margin-top:8px;"></div>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(f"**{row.get('event_name', '')}**")
            cols[3].write(row["event_start"].strftime("%d/%m/%Y") if pd.notna(row["event_start"]) else "—")
            cols[4].write(row["event_end"].strftime("%d/%m/%Y") if pd.notna(row["event_end"]) else "—")
            cols[5].write(f"{num_days(row)}")
            cols[6].write(f"{int(row.get('attendees', 0) or 0)}")
            cols[7].write(f"{count_rooms(row)}")
            cols[8].write(f"{count_spaces(row)}")

            if checked:
                selected_idx = i

        if selected_idx is not None:
            st.divider()
            st.subheader("📄 Client Card")
            render_client_card(df_year.loc[selected_idx], event_color(selected_idx))

    with tab2:
        st.subheader(f"Gantt Chart — {selected_year}")
        render_gantt(df_year, selected_year)


if __name__ == "__main__":
    main()