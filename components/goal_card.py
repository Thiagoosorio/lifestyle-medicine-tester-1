import streamlit as st
from config.settings import PILLARS, get_score_color


def render_goal_card(goal: dict, show_actions: bool = True):
    """Render a single goal as an expandable card."""
    pillar = PILLARS.get(goal["pillar_id"], {})
    status_colors = {
        "active": "green", "completed": "blue",
        "abandoned": "red", "paused": "orange",
    }
    status_color = status_colors.get(goal["status"], "gray")

    with st.expander(
        f"{pillar.get('icon', '')} **{goal['title']}** — :{status_color}[{goal['status'].upper()}]",
        expanded=goal["status"] == "active",
    ):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Pillar:** {pillar.get('display_name', 'Unknown')}")
            st.progress(goal["progress_pct"] / 100)
            st.caption(f"Progress: {goal['progress_pct']}%")

            if goal.get("target_value") and goal.get("unit"):
                st.caption(f"Target: {goal['current_value']}/{goal['target_value']} {goal['unit']}")

        with col2:
            from services.goal_service import get_days_remaining
            days = get_days_remaining(goal)
            if goal["status"] == "active":
                if days > 0:
                    st.metric("Days Left", days)
                elif days == 0:
                    st.metric("Days Left", "Today!")
                else:
                    st.metric("Days Left", f"{abs(days)} overdue")
            st.caption(f"Due: {goal['target_date'][:10]}")

        # SMART-EST details
        st.markdown("---")
        st.markdown("**SMART-EST Breakdown:**")
        details = {
            "Specific": goal["specific"],
            "Measurable": goal["measurable"],
            "Achievable": goal["achievable"],
            "Relevant": goal["relevant"],
            "Time-bound": goal["time_bound"],
        }
        for label, value in details.items():
            if value:
                st.markdown(f"- **{label}:** {value}")

        if goal.get("evidence_base"):
            st.markdown(f"- **Evidence-based:** {goal['evidence_base']}")
        if goal.get("strategic"):
            st.markdown(f"- **Strategic:** {goal['strategic']}")
        if goal.get("tailored"):
            st.markdown(f"- **Tailored:** {goal['tailored']}")

        # Action buttons
        if show_actions and goal["status"] == "active":
            st.markdown("---")
            act_cols = st.columns(4)
            with act_cols[0]:
                new_progress = st.number_input(
                    "Progress %", 0, 100, goal["progress_pct"],
                    key=f"prog_{goal['id']}",
                )
            with act_cols[1]:
                if st.button("Update", key=f"update_{goal['id']}"):
                    from services.goal_service import update_progress
                    update_progress(goal["id"], goal["user_id"], new_progress)
                    st.rerun()
            with act_cols[2]:
                if st.button("Complete", key=f"complete_{goal['id']}"):
                    from services.goal_service import mark_completed
                    mark_completed(goal["id"], goal["user_id"])
                    st.rerun()
            with act_cols[3]:
                if st.button("Abandon", key=f"abandon_{goal['id']}"):
                    from services.goal_service import mark_abandoned
                    mark_abandoned(goal["id"], goal["user_id"])
                    st.rerun()
