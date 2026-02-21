import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from services.goal_service import create_smart_goal, get_all_goals, get_goal_stats
from components.goal_card import render_goal_card

user_id = st.session_state.user_id

st.title("SMART-EST Goals")
st.markdown("Set evidence-based goals aligned with the 6 pillars of lifestyle medicine.")

# ── Stats ───────────────────────────────────────────────────────────────────
stats = get_goal_stats(user_id)
stat_cols = st.columns(4)
with stat_cols[0]:
    st.metric("Active", stats["active"])
with stat_cols[1]:
    st.metric("Completed", stats["completed"])
with stat_cols[2]:
    st.metric("Abandoned", stats["abandoned"])
with stat_cols[3]:
    st.metric("Completion Rate", f"{stats['completion_rate']:.0%}")

st.divider()

# ── Filter & View ───────────────────────────────────────────────────────────
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    status_filter = st.selectbox(
        "Status", ["All", "Active", "Completed", "Abandoned", "Paused"],
        index=1,
    )
with filter_col2:
    pillar_options = {"All": None}
    pillar_options.update({PILLARS[pid]["display_name"]: pid for pid in PILLARS})
    pillar_filter = st.selectbox("Pillar", options=list(pillar_options.keys()))

status_val = status_filter.lower() if status_filter != "All" else None
pillar_val = pillar_options[pillar_filter]

goals = get_all_goals(user_id, status=status_val, pillar_id=pillar_val)

if goals:
    for goal in goals:
        render_goal_card(goal)
else:
    st.info("No goals found. Create your first goal below!")

# ── Create New Goal ─────────────────────────────────────────────────────────
st.divider()
st.markdown("### Create New Goal")
st.caption("Use the SMART-EST framework to create well-defined, evidence-based goals.")

with st.form("new_goal_form"):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Goal Title", placeholder="e.g., Walk 30 minutes daily")
        pillar_id = st.selectbox(
            "Pillar",
            options=list(PILLARS.keys()),
            format_func=lambda x: f"{PILLARS[x]['icon']} {PILLARS[x]['display_name']}",
        )
    with col2:
        start_date = st.date_input("Start Date", value=date.today())
        target_date = st.date_input("Target Date", value=date.today() + timedelta(weeks=4))

    st.markdown("**SMART Criteria**")
    specific = st.text_area(
        "Specific — What exactly will you do?",
        placeholder="I will walk briskly for 30 minutes during my lunch break",
        height=68,
    )
    measurable = st.text_area(
        "Measurable — How will you track this?",
        placeholder="Track with a timer/fitness app, 3 times per week minimum",
        height=68,
    )
    achievable = st.text_area(
        "Achievable — Why is this realistic for you right now?",
        placeholder="I have a 1-hour lunch break and there's a park nearby",
        height=68,
    )
    relevant = st.text_area(
        "Relevant — How does this connect to your values/health?",
        placeholder="I want to improve my cardiovascular health and reduce stress",
        height=68,
    )
    time_bound = st.text_area(
        "Time-bound — What's the timeframe?",
        placeholder="4 weeks starting today, then reassess",
        height=68,
    )

    with st.expander("EST Extensions (Optional — Evidence, Strategy, Tailoring)"):
        evidence_base = st.text_area(
            "Evidence-based — What evidence supports this approach?",
            placeholder="AHA recommends 150 min/week moderate aerobic activity...",
            height=68,
        )
        strategic = st.text_area(
            "Strategic — How does this fit your broader lifestyle plan?",
            placeholder="Starting with physical activity as my lowest-scoring pillar...",
            height=68,
        )
        tailored = st.text_area(
            "Tailored — How is this personalized to your situation?",
            placeholder="Walking is my preferred form of exercise; I enjoy being outdoors...",
            height=68,
        )

    with st.expander("Numeric Tracking (Optional)"):
        num_col1, num_col2 = st.columns(2)
        with num_col1:
            target_value = st.number_input("Target Value", min_value=0.0, value=0.0, step=1.0)
        with num_col2:
            unit = st.text_input("Unit", placeholder="minutes, servings, sessions, etc.")

    submitted = st.form_submit_button("Create Goal", use_container_width=True, type="primary")

    if submitted:
        if not title or not specific or not measurable or not achievable or not relevant or not time_bound:
            st.error("Please fill in all SMART fields (Title, Specific, Measurable, Achievable, Relevant, Time-bound).")
        else:
            data = {
                "pillar_id": pillar_id,
                "title": title,
                "specific": specific,
                "measurable": measurable,
                "achievable": achievable,
                "relevant": relevant,
                "time_bound": time_bound,
                "evidence_base": evidence_base,
                "strategic": strategic,
                "tailored": tailored,
                "target_value": target_value if target_value > 0 else None,
                "unit": unit,
                "start_date": start_date.isoformat(),
                "target_date": target_date.isoformat(),
            }
            create_smart_goal(user_id, data)
            st.success(f"Goal '{title}' created!")
            st.rerun()
