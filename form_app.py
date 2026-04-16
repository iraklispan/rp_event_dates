"""
form_app.py — User app για εισαγωγή νέων events
"""

import streamlit as st
from shared import render_event_form


def main():
    st.set_page_config(
        page_title="Groups & Conferences — New Event",
        page_icon="📋",
        layout="wide",
    )
    st.title("📋 New Group / Conference Event")

    success = render_event_form(prefix="form_", submit_label="💾 Save Event")

    if success:
        st.success("✅ Το event αποθηκεύτηκε επιτυχώς!")
        st.balloons()


if __name__ == "__main__":
    main()