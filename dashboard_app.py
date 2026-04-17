"""
dashboard_app.py — Admin app με dashboard, client card και edit mode
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from shared import (
    load_data, event_color, num_days,
    get_event_rooms, get_event_spaces,
    PRICE_COMBOS, render_event_form,
    prefill_form_state, init_form_state,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def count_rooms_from_df(rooms_df, event_id):
    if rooms_df.empty:
        return 0
    ev = rooms_df[rooms_df["event_id"] == event_id]
    total = 0
    for _, r in ev.iterrows():
        try:
            total += int(float(r.get("room_count", 0) or 0))
        except Exception:
            pass
    return total


def count_spaces_from_df(spaces_df, event_id):
    if spaces_df.empty:
        return 0
    return len(spaces_df[spaces_df["event_id"] == event_id])


# ─────────────────────────────────────────────
# CLIENT CARD
# ─────────────────────────────────────────────
def render_client_card(event_row, rooms_df, spaces_list, color, row_idx):
    st.markdown(
        f"""<div style="border-left:5px solid {color};padding:0.6rem 1.2rem;
        background:#f8fafc;border-radius:8px;margin-bottom:1rem;">
        <h3 style="margin:0;color:#1e293b;">{event_row['event_name']}</h3>
        <p style="margin:0;color:#64748b;">Submitted by
        <b>{event_row.get('submitted_by','—')}</b></p>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.button("✏️ Edit this Event", key=f"edit_btn_{row_idx}"):
        st.session_state["editing_event"] = event_row["event_name"]
        init_form_state("edit_")
        prefill_form_state(event_row, rooms_df, spaces_list, prefix="edit_")
        st.rerun()

    # General
    with st.expander("📌 General Information", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Type", event_row.get("event_type") or "—")
        c2.metric("Start", event_row["event_start"].strftime("%d/%m/%Y")
                  if pd.notna(event_row["event_start"]) else "—")
        c3.metric("End", event_row["event_end"].strftime("%d/%m/%Y")
                  if pd.notna(event_row["event_end"]) else "—")
        c4.metric("Duration", f"{num_days(event_row)} nights")
        c5.metric("Attendees", int(event_row.get("attendees", 0) or 0))

    # Accommodation
    if str(event_row.get("includes_accommodation", "")).lower() == "true":
        with st.expander("🛏️ Accommodation", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            acc_start = event_row.get("acc_start")
            acc_end   = event_row.get("acc_end")
            c1.metric("Check-in",  acc_start.strftime("%d/%m/%Y") if pd.notna(acc_start) else "—")
            c2.metric("Check-out", acc_end.strftime("%d/%m/%Y")   if pd.notna(acc_end)   else "—")
            c3.metric("Booking Code", event_row.get("booking_code") or "—")
            c4.metric("Min Stay", f"{int(event_row.get('minimum_stay', 0) or 0)} nights")

            policy = event_row.get("cancellation_policy", "—")
            if policy == "Flexible":
                st.info(f"✅ Flexible — Free cancellation up to "
                        f"**{int(event_row.get('cancellation_days', 0) or 0)} days** before arrival")
            elif policy == "Night Deposit":
                st.warning(f"💳 Night Deposit — Required "
                           f"**{int(event_row.get('deposit_days', 0) or 0)} days** before arrival")
            elif policy == "Non Refundable":
                st.error("🔒 Non Refundable")

            cut_off = event_row.get("cut_off_date")
            if pd.notna(cut_off):
                st.markdown(f"**Cut-off Date:** {cut_off.strftime('%d/%m/%Y')}")

            if not rooms_df.empty:
                st.markdown("---")
                st.markdown("**Room Types**")
                room_rows = []
                for _, r in rooms_df.iterrows():
                    prices = {}
                    for combo in PRICE_COMBOS:
                        k = f"price_{combo.replace('+', '_')}"
                        try:
                            v = int(float(r.get(k, 0) or 0))
                        except Exception:
                            v = 0
                        if v > 0:
                            prices[combo] = f"€{v}"
                    room_rows.append({
                        "Room Type": r.get("room_type", ""),
                        "Count":     int(float(r.get("room_count", 0) or 0)),
                        "Rate Plan": r.get("rate_plan", "—"),
                        **prices,
                    })
                st.dataframe(pd.DataFrame(room_rows),
                             use_container_width=True, hide_index=True)

    # Meeting Spaces
    if str(event_row.get("includes_meeting_spaces", "")).lower() == "true" and spaces_list:
        with st.expander("🏛️ Meeting Spaces & Events", expanded=True):
            for sp in spaces_list:
                st.markdown(f"**{sp['space_name']}**")
                if sp["services"]:
                    svc_df = pd.DataFrame([
                        {"Service": sv["type"], "Pax": sv["pax"]}
                        for sv in sp["services"]
                    ])
                    st.dataframe(svc_df, use_container_width=True, hide_index=True)
                st.markdown("")


# ─────────────────────────────────────────────
# EDIT CARD
# ─────────────────────────────────────────────
def render_edit_card(event_name):
    st.markdown(
        f"""<div style="border-left:5px solid #F59E0B;padding:0.6rem 1.2rem;
        background:#fffbeb;border-radius:8px;margin-bottom:1rem;">
        <h3 style="margin:0;color:#92400e;">✏️ Editing: {event_name}</h3>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("❌ Cancel Edit"):
        st.session_state["editing_event"] = None
        st.rerun()

    success = render_event_form(prefix="edit_", submit_label="💾 Save Changes")
    if success:
        st.success("✅ Οι αλλαγές αποθηκεύτηκαν!")
        st.session_state["editing_event"] = None
        st.rerun()


# ─────────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────────
def render_gantt(df_all, rooms_df, spaces_df):
    from streamlit_echarts import st_echarts
    import calendar

    df_valid = df_all.dropna(subset=["event_start", "event_end"]).copy()
    if df_valid.empty:
        st.info("Δεν υπάρχουν events με έγκυρες ημερομηνίες.")
        return

    # ── Year filter ───────────────────────────
    available_years = sorted(df_valid["event_start"].dt.year.unique().tolist())
    selected_year = st.selectbox(
        "📅 Έτος", available_years,
        index=len(available_years) - 1,
        key="gantt_year",
    )

    df_plot = (
        df_valid[df_valid["event_start"].dt.year == selected_year]
        .sort_values("event_start")
        .reset_index(drop=True)
    )

    if df_plot.empty:
        st.info(f"Δεν υπάρχουν events για το {selected_year}.")
        return

    # ── Build data για ECharts ─────────────────
    # Τα events ως y-axis categories (αντεστραμμένα για top-to-bottom)
    event_names = df_plot["event_name"].tolist()
    event_names_reversed = list(reversed(event_names))

    series_data = []
    for idx, row in df_plot.iterrows():
        eid   = row["event_id"]
        color = event_color(idx)
        rooms  = count_rooms_from_df(rooms_df, eid)
        spaces = count_spaces_from_df(spaces_df, eid)
        nights = (row["event_end"] - row["event_start"]).days or 1

        series_data.append({
            "name":  row["event_name"],
            "value": [
                event_names_reversed.index(row["event_name"]),  # y index
                row["event_start"].strftime("%Y-%m-%d"),
                row["event_end"].strftime("%Y-%m-%d"),
                row["event_name"],
                row.get("event_type", "—"),
                nights,
                int(row.get("attendees", 0) or 0),
                rooms,
                spaces,
            ],
            "itemStyle": {"color": color},
        })

    # ── ECharts option ────────────────────────
    option = {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "item",
            "formatter": (
                "function(params) {"
                "  var v = params.value;"
                "  return '<b>' + v[3] + '</b><br/>'"
                "    + 'Τύπος: ' + v[4] + '<br/>'"
                "    + '📅 ' + v[1] + ' → ' + v[2] + '<br/>'"
                "    + '🌙 ' + v[5] + ' nights<br/>'"
                "    + '👥 ' + v[6] + ' attendees<br/>'"
                "    + '🛏️ ' + v[7] + ' rooms | 🏛️ ' + v[8] + ' spaces';"
                "}"
            ),
        },
        "title": {
            "text": f"Groups & Conferences — {selected_year}",
            "textStyle": {"fontSize": 18, "fontWeight": "normal"},
            "top": 10,
            "left": 10,
        },
        "grid": {
            "top":    60,
            "bottom": 80,   # χώρος για dataZoom slider
            "left":   200,  # χώρος για event names
            "right":  20,
        },
        "xAxis": {
            "type": "time",
            "min": f"{selected_year}-01-01",
            "max": f"{selected_year}-12-31",
            "axisLabel": {
                "formatter": (
                    "function(val) {"
                    "  var d = new Date(val);"
                    "  var months = ['Ιαν','Φεβ','Μαρ','Απρ','Μάι','Ιουν',"
                    "               'Ιουλ','Αυγ','Σεπ','Οκτ','Νοε','Δεκ'];"
                    # Όταν ζουμάρει φαίνονται ημέρες, αλλιώς μήνες
                    "  if (d.getDate() === 1 || d.getDate() === 15) {"
                    "    return d.getDate() === 1"
                    "      ? months[d.getMonth()]"
                    "      : d.getDate();"
                    "  }"
                    "  return '';"
                    "}"
                ),
                "fontSize": 11,
                "color": "#475569",
            },
            "splitLine": {"show": True, "lineStyle": {"color": "#e2e8f0"}},
            "axisLine":  {"lineStyle": {"color": "#cbd5e1"}},
        },
        "yAxis": {
            "type": "category",
            "data": event_names_reversed,
            "axisLabel": {
                "fontSize": 12,
                "color": "#1e293b",
                "width": 180,
                "overflow": "truncate",
            },
            "axisLine":  {"show": False},
            "axisTick":  {"show": False},
            "splitLine": {"show": False},
        },
        # ── dataZoom: οριζόντιος slider κάτω + scroll με mouse wheel ─────
        "dataZoom": [
            {
                "type":       "slider",   # ορατός slider κάτω από το chart
                "xAxisIndex": 0,
                "start":      16,         # ~Μάρτιος
                "end":        84,         # ~Οκτώβριος
                "height":     20,
                "bottom":     15,
                "fillerColor": "rgba(148,163,184,0.2)",
                "borderColor": "#cbd5e1",
                "handleStyle": {"color": "#64748b"},
                "labelFormatter": (
                    "function(val) {"
                    "  var d = new Date(val);"
                    "  var months = ['Ιαν','Φεβ','Μαρ','Απρ','Μάι','Ιουν',"
                    "               'Ιουλ','Αυγ','Σεπ','Οκτ','Νοε','Δεκ'];"
                    "  return months[d.getMonth()] + ' ' + d.getFullYear();"
                    "}"
                ),
            },
            {
                "type":       "inside",   # scroll με mouse wheel
                "xAxisIndex": 0,
                "start":      16,
                "end":        84,
                "zoomOnMouseWheel":  True,
                "moveOnMouseMove":   True,
                "moveOnMouseWheel":  False,
            },
        ],
        "series": [
            {
                "type": "custom",
                "renderItem": (
                    "function(params, api) {"
                    "  var categoryIndex = api.value(0);"
                    "  var start  = api.coord([api.value(1), categoryIndex]);"
                    "  var end    = api.coord([api.value(2), categoryIndex]);"
                    "  var height = api.size([0, 1])[1] * 0.72;"  # ύψος μπάρας (72% του row)
                    "  var x = start[0];"
                    "  var y = start[1] - height / 2;"
                    "  var width = Math.max(end[0] - start[0], 2);"
                    "  return {"
                    "    type: 'group',"
                    "    children: [{"
                    "      type: 'rect',"
                    "      shape: {x:x, y:y, width:width, height:height, r:4},"
                    "      style: api.style(),"
                    "    }]"
                    "  };"
                    "}"
                ),
                "encode": {"x": [1, 2], "y": 0},
                "data":   series_data,
            }
        ],
    }

    chart_height = max(400, len(df_plot) * 40 + 140)
    st_echarts(option, height=f"{chart_height}px", key=f"gantt_{selected_year}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Groups & Conferences — Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.title("📊 Groups & Conferences Dashboard")

    if "editing_event" not in st.session_state:
        st.session_state["editing_event"] = None

    with st.spinner("Φόρτωση δεδομένων..."):
        data = load_data()

    events_df   = data["events"]
    rooms_df    = data["rooms"]
    spaces_df   = data["spaces"]
    services_df = data["services"]

    if events_df.empty:
        st.warning("Δεν υπάρχουν δεδομένα ακόμα.")
        return

    available_years = sorted(events_df["event_start"].dropna().dt.year.unique().tolist())
    if not available_years:
        st.warning("Δεν βρέθηκαν έγκυρες ημερομηνίες.")
        return

    selected_year = st.selectbox("📅 Έτος", available_years,
                                 index=len(available_years) - 1)
    df_year = events_df[
        events_df["event_start"].dt.year == selected_year
    ].copy().reset_index(drop=True)

    tab1, tab2 = st.tabs(["📋 Events", "📅 Gantt Chart"])

    # ── TAB 1 ─────────────────────────────────
    with tab1:
        st.subheader(f"Events {selected_year}  —  {len(df_year)} total")

        hcols = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1.2, 1, 1])
        for col, label in zip(hcols[2:],
                               ["Event", "Start", "End", "Nights",
                                "Attendees", "Rooms", "Spaces"]):
            col.markdown(f"**{label}**")
        st.divider()

        selected_idx = None
        for i, row in df_year.iterrows():
            color = event_color(i)
            eid   = row["event_id"]
            cols  = st.columns([0.4, 0.2, 3, 1.5, 1.5, 1, 1.2, 1, 1])

            checked = cols[0].checkbox("", key=f"chk_{i}",
                                       label_visibility="collapsed")
            cols[1].markdown(
                f'<div style="width:14px;height:14px;border-radius:50%;'
                f'background:{color};margin-top:8px;"></div>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(f"**{row.get('event_name', '')}**")
            cols[3].write(row["event_start"].strftime("%d/%m/%Y")
                          if pd.notna(row["event_start"]) else "—")
            cols[4].write(row["event_end"].strftime("%d/%m/%Y")
                          if pd.notna(row["event_end"]) else "—")
            cols[5].write(str(num_days(row)))
            cols[6].write(str(int(row.get("attendees", 0) or 0)))
            cols[7].write(str(count_rooms_from_df(rooms_df, eid)))
            cols[8].write(str(count_spaces_from_df(spaces_df, eid)))

            if checked:
                selected_idx = i

        if selected_idx is not None:
            st.divider()
            st.subheader("📄 Client Card")
            selected_row  = df_year.loc[selected_idx]
            color         = event_color(selected_idx)
            eid           = selected_row["event_id"]
            ev_rooms_df   = get_event_rooms(rooms_df, eid)
            ev_spaces     = get_event_spaces(spaces_df, services_df, eid)

            editing = st.session_state.get("editing_event")
            if editing and editing == selected_row["event_name"]:
                render_edit_card(editing)
            else:
                render_client_card(selected_row, ev_rooms_df, ev_spaces,
                                   color, selected_idx)

    # ── TAB 2 ─────────────────────────────────
    with tab2:
        render_gantt(events_df, rooms_df, spaces_df)


if __name__ == "__main__":
    main()