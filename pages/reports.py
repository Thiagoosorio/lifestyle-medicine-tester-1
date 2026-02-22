"""
Health Report — Generate and download a comprehensive lifestyle medicine report.
"""

import streamlit as st
from datetime import date
from services.pdf_report import generate_health_report

user_id = st.session_state.user_id

st.title("Health Report")
st.markdown(
    "Generate a comprehensive, print-friendly health report summarizing your "
    "lifestyle medicine data. Download the report as an HTML file and print it "
    "to PDF from your browser."
)

# ── Controls ──────────────────────────────────────────────────────────────────
col_period, col_action = st.columns([2, 1])

with col_period:
    period = st.selectbox(
        "Report Period",
        options=["week", "month", "quarter", "year", "all"],
        format_func=lambda p: {
            "week": "This Week",
            "month": "This Month",
            "quarter": "This Quarter",
            "year": "This Year",
            "all": "All Time",
        }[p],
        index=1,
        help="Choose how far back the report should cover.",
    )

with col_action:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)  # vertical spacer
    generate_clicked = st.button(
        "Generate Report",
        type="primary",
        use_container_width=True,
    )

# ── Generation ────────────────────────────────────────────────────────────────
if generate_clicked:
    with st.spinner("Generating your health report..."):
        html_report = generate_health_report(user_id, period=period)
    st.session_state["_report_html"] = html_report
    st.session_state["_report_period"] = period

# ── Display / Download ────────────────────────────────────────────────────────
if "_report_html" in st.session_state:
    html_report = st.session_state["_report_html"]
    report_period = st.session_state.get("_report_period", "month")

    # Build a sensible filename
    today_str = date.today().isoformat()
    filename = f"health_report_{report_period}_{today_str}.html"

    st.divider()

    # Download button at the top for easy access
    st.download_button(
        label="Download Report (HTML)",
        data=html_report,
        file_name=filename,
        mime="text/html",
        use_container_width=True,
        type="primary",
    )
    st.caption(
        "Tip: Open the downloaded file in your browser and use "
        "**Ctrl+P** (or **Cmd+P** on Mac) to print or save as PDF."
    )

    st.divider()

    # Inline preview
    st.markdown("### Report Preview")
    st.components.v1.html(html_report, height=1200, scrolling=True)

else:
    st.info(
        "Click **Generate Report** above to create your health report. "
        "You can then preview it here and download it."
    )
