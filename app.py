import streamlit as st
from db.database import init_db

st.set_page_config(
    page_title="Lifestyle Medicine Coach",
    page_icon=":material/favorite:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database on first run
init_db()

# Auto-seed demo account if it doesn't exist (needed for Streamlit Cloud)
from db.database import get_connection as _get_conn
_c = _get_conn()
_demo_exists = _c.execute("SELECT id FROM users WHERE username = 'maria.silva'").fetchone()
_c.close()
if not _demo_exists:
    from seed_demo import main as _seed_demo
    _seed_demo()

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
                st.Page("pages/recovery.py", title="Recovery", icon=":material/hotel:"),
            ],
            "Planning": [
                st.Page("pages/weekly_plan.py", title="Weekly Plan", icon=":material/calendar_view_week:"),
                st.Page("pages/monthly_plan.py", title="Monthly Plan", icon=":material/calendar_month:"),
                st.Page("pages/goals.py", title="Goals", icon=":material/flag:"),
            ],
            "Tracking": [
                st.Page("pages/progress.py", title="Progress", icon=":material/trending_up:"),
                st.Page("pages/exercise_tracker.py", title="Exercise", icon=":material/fitness_center:"),
                st.Page("pages/exercise_library.py", title="Exercise Library", icon=":material/menu_book:"),
                st.Page("pages/exercise_prescription.py", title="Training Program", icon=":material/assignment:"),
                st.Page("pages/body_metrics.py", title="Body Metrics", icon=":material/monitor_weight:"),
                st.Page("pages/biomarkers.py", title="Biomarkers", icon=":material/bloodtype:"),
                st.Page("pages/organ_health.py", title="Organ Scores", icon=":material/monitor_heart:"),
                st.Page("pages/sleep_tracker.py", title="Sleep", icon=":material/bedtime:"),
                st.Page("pages/nutrition_logger.py", title="Nutrition", icon=":material/restaurant:"),
                st.Page("pages/diet_assessment.py", title="Diet Pattern", icon=":material/eco:"),
                st.Page("pages/fasting_tracker.py", title="Fasting", icon=":material/timer:"),
                st.Page("pages/sibo_tracker.py", title="SIBO & FODMAP", icon=":material/science:"),
                st.Page("pages/analytics.py", title="Analytics", icon=":material/insights:"),
                st.Page("pages/ai_coach.py", title="AI Coach", icon=":material/psychology:"),
            ],
            "Science": [
                st.Page("pages/research_library.py", title="Research Library", icon=":material/science:"),
                st.Page("pages/protocols.py", title="Daily Protocols", icon=":material/labs:"),
            ],
            "Growth": [
                st.Page("pages/daily_growth.py", title="Daily Growth", icon=":material/spa:"),
                st.Page("pages/lessons.py", title="Micro-Lessons", icon=":material/school:"),
                st.Page("pages/challenges.py", title="Challenges", icon=":material/emoji_events:"),
                st.Page("pages/future_self.py", title="Future Self", icon=":material/mail:"),
            ],
            "Reports": [
                st.Page("pages/reports.py", title="Health Report", icon=":material/summarize:"),
            ],
            "Account": [
                st.Page("pages/settings_page.py", title="Settings", icon=":material/settings:"),
                st.Page("pages/garmin_import.py", title="Garmin Connect", icon=":material/watch:"),
            ],
        }
    )
    with st.sidebar:
        display = st.session_state.get("display_name", "User")
        sidebar_html = (
            '<div style="background:#FFFFFF;border:1px solid rgba(0,0,0,0.10);'
            'border-radius:16px;padding:16px;margin-bottom:12px;text-align:center">'
            '<div style="font-size:2rem;margin-bottom:4px">&#128075;</div>'
            f'<div style="font-family:\'Google Sans\',\'Product Sans\',-apple-system,BlinkMacSystemFont,'
            f'\'Segoe UI\',Roboto,system-ui,sans-serif;font-size:17px;line-height:22px;'
            f'font-weight:600;color:#1D1B20">{display}</div>'
            '<div style="font-size:11px;line-height:13px;color:#79747E;'
            'margin-top:4px">Lifestyle Medicine Journey</div>'
            '</div>'
        )
        st.markdown(sidebar_html, unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

pg.run()
