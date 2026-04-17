# ─────────────────────────────────────────────
# GANTT (βελτιωμένη έκδοση)
# ─────────────────────────────────────────────
def render_gantt(df_all, rooms_df, spaces_df):
    import plotly.express as px

    df_valid = df_all.dropna(subset=["event_start", "event_end"]).copy()
    if df_valid.empty:
        st.info("Δεν υπάρχουν events με έγκυρες ημερομηνίες.")
        return

    # Year filter
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

    # Build records
    records = []
    for idx, row in df_plot.iterrows():
        eid = row["event_id"]
        days = (row["event_end"] - row["event_start"]).days or 1
        records.append({
            "Event":     row["event_name"],
            "Type":      row.get("event_type", ""),
            "Start":     row["event_start"],
            "Finish":    row["event_end"],
            "Attendees": int(row.get("attendees", 0) or 0),
            "Nights":    days,
            "Rooms":     count_rooms_from_df(rooms_df, eid),
            "Spaces":    count_spaces_from_df(spaces_df, eid),
            "Color":     event_color(idx),
        })

    df_gantt = pd.DataFrame(records)

    fig = px.timeline(
        df_gantt,
        x_start="Start",
        x_end="Finish",
        y="Event",
        color="Event",
        color_discrete_sequence=df_gantt["Color"].tolist(),
        custom_data=["Type", "Nights", "Attendees", "Rooms", "Spaces"],
    )

    # === ΒΕΛΤΙΩΣΕΙΣ ===
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Type: %{customdata[0]}<br>"
            "📅 %{base|%d/%m/%Y} → %{x|%d/%m/%Y}<br>"
            "🌙 %{customdata[1]} nights<br>"
            "👥 %{customdata[2]} attendees<br>"
            "🛏️ %{customdata[3]} rooms | 🏛️ %{customdata[4]} spaces"
            "<extra></extra>"
        )
    )

    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12), title="")

    # === ΝΕΑ ΡΥΘΜΙΣΗ X-AXIS (μήνες → ημέρες αυτόματα) ===
    fig.update_xaxes(
        range=[f"{selected_year}-03-01", f"{selected_year}-10-31"],
        showgrid=True,
        gridcolor="#e2e8f0",
        gridwidth=1,
        # Αυτόματα αλλάζει format ανάλογα με το πόσο έχεις ζουμάρει
        tickformatstops=[
            dict(dtickrange=[None, "M1"], value="%B %Y"),      # πολύ zoomed-out → Μήνας + Έτος
            dict(dtickrange=["M1", "M3"], value="%b"),         # μεσαίο zoom → Μήνας
            dict(dtickrange=["M3", None], value="%d %b"),      # zoomed-in → Αριθμός ημέρας + Μήνας
        ],
        tickfont=dict(size=13),
        fixedrange=False,
    )

    # === ΜΙΚΡΟΤΕΡΟ ΚΕΝΟ ΑΝΑΜΕΣΑ ΣΤΙΣ ΜΠΑΡΕΣ ===
    fig.update_layout(
        height=max(480, len(df_plot) * 48),        # λίγο πιο compact
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=40),
        bargap=0.08,                               # ← ΕΔΩ ΜΕΙΩΝΕΤΑΙ Η ΑΠΟΣΤΑΣΗ (0.08 = πολύ καλό)
        showlegend=False,
        title=dict(
            text=f"Groups & Conferences — {selected_year}",
            font=dict(size=18),
        ),
        dragmode="pan",
        # Προσθήκη rangeslider για ακόμα καλύτερο zoom & πλοήγηση
        xaxis_rangeslider_visible=True,
    )

    # Ετικέτες μέσα στις μπάρες (όταν είναι αρκετά φαρδιές)
    for _, row in df_gantt.iterrows():
        if row["Nights"] >= 3:
            mid = row["Start"] + (row["Finish"] - row["Start"]) / 2
            fig.add_annotation(
                x=mid, y=row["Event"],
                text=row["Event"],
                showarrow=False,
                font=dict(color="white", size=10, family="Arial Bold"),
                xref="x", yref="y",
            )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
        }
    )