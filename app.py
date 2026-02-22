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

# Inject Apple Design System + Tailwind utility CSS
from components.custom_theme import inject_custom_css
inject_custom_css()

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
                st.Page("pages/body_metrics.py", title="Body Metrics", icon=":material/monitor_weight:"),
                st.Page("pages/analytics.py", title="Analytics", icon=":material/insights:"),
                st.Page("pages/ai_coach.py", title="AI Coach", icon=":material/psychology:"),
            ],
            "Growth": [
                st.Page("pages/lessons.py", title="Micro-Lessons", icon=":material/school:"),
                st.Page("pages/challenges.py", title="Challenges", icon=":material/emoji_events:"),
                st.Page("pages/future_self.py", title="Future Self", icon=":material/mail:"),
            ],
            "Reports": [
                st.Page("pages/reports.py", title="Health Report", icon=":material/summarize:"),
            ],
            "Account": [
                st.Page("pages/settings_page.py", title="Settings", icon=":material/settings:"),
            ],
        }
    )
    with st.sidebar:
        display = st.session_state.get("display_name", "User")
        sidebar_html = (
            '<div style="background:#1C1C1E;border:1px solid rgba(84,84,88,0.6);'
            'border-radius:16px;padding:16px;margin-bottom:12px;text-align:center">'
            '<div style="font-size:2rem;margin-bottom:4px">&#128075;</div>'
            f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'SF Pro Display\','
            f'\'Helvetica Neue\',system-ui,sans-serif;font-size:17px;line-height:22px;'
            f'font-weight:600;color:rgba(255,255,255,1.0)">{display}</div>'
            '<div style="font-size:11px;line-height:13px;color:rgba(235,235,245,0.3);'
            'margin-top:4px">Lifestyle Medicine Journey</div>'
            '</div>'
        )
        st.markdown(sidebar_html, unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

pg.run()
