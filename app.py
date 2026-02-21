import streamlit as st
from db.database import init_db

st.set_page_config(
    page_title="Lifestyle Medicine Coach",
    page_icon=":material/favorite:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database on first run
init_db()

# ── Authentication gate ─────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    pg = st.navigation([st.Page("pages/login.py", title="Login", icon=":material/login:")])
else:
    pg = st.navigation(
        {
            "Overview": [
                st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
                st.Page("pages/wheel_assessment.py", title="Wheel of Life", icon=":material/donut_large:"),
            ],
            "Planning": [
                st.Page("pages/weekly_plan.py", title="Weekly Plan", icon=":material/calendar_view_week:"),
                st.Page("pages/monthly_plan.py", title="Monthly Plan", icon=":material/calendar_month:"),
                st.Page("pages/goals.py", title="Goals", icon=":material/flag:"),
            ],
            "Tracking": [
                st.Page("pages/progress.py", title="Progress", icon=":material/trending_up:"),
                st.Page("pages/analytics.py", title="Analytics", icon=":material/insights:"),
                st.Page("pages/ai_coach.py", title="AI Coach", icon=":material/psychology:"),
            ],
            "Growth": [
                st.Page("pages/lessons.py", title="Micro-Lessons", icon=":material/school:"),
                st.Page("pages/future_self.py", title="Future Self", icon=":material/mail:"),
            ],
            "Account": [
                st.Page("pages/settings_page.py", title="Settings", icon=":material/settings:"),
            ],
        }
    )
    with st.sidebar:
        st.markdown(f"### {st.session_state.get('display_name', 'User')}")
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

pg.run()
