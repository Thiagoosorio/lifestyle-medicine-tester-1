import streamlit as st
from models.user import get_user, update_user, change_password, verify_user
from services.export_service import export_all_json
from services.habit_service import initialize_default_habits
from config.settings import PILLARS, DEFAULT_HABITS
from models.habit import create_habit, get_active_habits, deactivate_habit

user_id = st.session_state.user_id

st.title("Settings")

user = get_user(user_id)

# ── Profile ─────────────────────────────────────────────────────────────────
st.markdown("### Profile")
with st.form("profile_form"):
    display_name = st.text_input("Display Name", value=user["display_name"] or "")
    email = st.text_input("Email", value=user["email"] or "")
    if st.form_submit_button("Update Profile"):
        update_user(user_id, display_name=display_name, email=email)
        st.session_state.display_name = display_name
        st.success("Profile updated!")

# ── Change Password ─────────────────────────────────────────────────────────
st.divider()
st.markdown("### Change Password")
with st.form("password_form"):
    current_pw = st.text_input("Current Password", type="password")
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm New Password", type="password")
    if st.form_submit_button("Change Password"):
        if not current_pw or not new_pw:
            st.error("Please fill in all fields.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        elif len(new_pw) < 6:
            st.error("Password must be at least 6 characters.")
        elif not verify_user(user["username"], current_pw):
            st.error("Current password is incorrect.")
        else:
            change_password(user_id, new_pw)
            st.success("Password changed!")

# ── Manage Habits ───────────────────────────────────────────────────────────
st.divider()
st.markdown("### Manage Habits")

habits = get_active_habits(user_id)
if habits:
    for habit in habits:
        pillar = PILLARS.get(habit["pillar_id"], {})
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"{pillar.get('icon', '')} **{habit['name']}** — *{pillar.get('display_name', '')}*")
        with col2:
            if st.button("Remove", key=f"rm_habit_{habit['id']}"):
                deactivate_habit(habit["id"], user_id)
                st.rerun()
else:
    st.caption("No active habits.")

with st.expander("Add Custom Habit"):
    with st.form("add_habit_settings"):
        h_name = st.text_input("Habit name")
        h_pillar = st.selectbox(
            "Pillar",
            options=list(PILLARS.keys()),
            format_func=lambda x: PILLARS[x]["display_name"],
        )
        if st.form_submit_button("Add"):
            if h_name:
                create_habit(user_id, h_pillar, h_name)
                st.success(f"Habit '{h_name}' added!")
                st.rerun()

with st.expander("Reset to Default Habits"):
    st.warning("This will deactivate all current habits and add the default set.")
    if st.button("Reset Habits"):
        for h in get_active_habits(user_id):
            deactivate_habit(h["id"], user_id)
        for pillar_id, habit_names in DEFAULT_HABITS.items():
            for name in habit_names:
                create_habit(user_id, pillar_id, name)
        st.success("Habits reset to defaults!")
        st.rerun()

# ── Data Management ─────────────────────────────────────────────────────────
st.divider()
st.markdown("### Data Management")

json_data = export_all_json(user_id)
st.download_button(
    "Export All Data (JSON)",
    json_data,
    "lifestyle_medicine_full_export.json",
    "application/json",
    use_container_width=True,
)

st.divider()
st.markdown("### About")
st.markdown("""
**Lifestyle Medicine Coach** — An evidence-based coaching app built on the 6 pillars of lifestyle medicine
as defined by the [American College of Lifestyle Medicine (ACLM)](https://lifestylemedicine.org/).

**Frameworks used:**
- Transtheoretical Model (Stages of Change)
- COM-B Model for Behavior Change
- Motivational Interviewing (OARS)
- SMART-EST Goal Setting

*Built with Streamlit, Plotly, and Python.*
""")
