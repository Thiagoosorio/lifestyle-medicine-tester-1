import streamlit as st
from config.settings import PILLARS, STAGES_OF_CHANGE, get_score_label, get_score_color
from services.wheel_service import submit_assessment, get_current_wheel, get_history, compute_changes, get_total_score, get_score_summary
from components.wheel_chart import create_wheel_chart, create_comparison_chart, create_trend_chart

user_id = st.session_state.user_id

st.title("Wheel of Life Assessment")
st.markdown("Rate each of the **6 pillars of lifestyle medicine** on a scale of 1-10 based on how you're doing right now.")

tab_assess, tab_history = st.tabs(["Take Assessment", "History & Compare"])

# ── Take Assessment ─────────────────────────────────────────────────────────
with tab_assess:
    col_form, col_preview = st.columns([1, 1])

    scores = {}
    stages = {}
    notes = {}

    with col_form:
        with st.form("assessment_form"):
            for pid, pillar in PILLARS.items():
                st.markdown(f"**{pillar['icon']} {pillar['display_name']}**")
                st.caption(pillar["description"])
                scores[pid] = st.slider(
                    f"Score for {pillar['display_name']}",
                    min_value=1, max_value=10, value=5,
                    key=f"score_{pid}",
                    label_visibility="collapsed",
                )
                with st.expander("Stage of Change & Notes", expanded=False):
                    stages[pid] = st.radio(
                        "Where are you on your change journey?",
                        options=list(STAGES_OF_CHANGE.keys()),
                        format_func=lambda x: f"{STAGES_OF_CHANGE[x]['label']} — {STAGES_OF_CHANGE[x]['description']}",
                        key=f"stage_{pid}",
                        index=2,
                    )
                    notes[pid] = st.text_area(
                        "Reflection notes (optional)",
                        key=f"notes_{pid}",
                        height=68,
                    )
                st.divider()

            submitted = st.form_submit_button("Submit Assessment", use_container_width=True, type="primary")

    with col_preview:
        st.markdown("### Live Preview")
        preview_scores = {}
        for pid in PILLARS:
            key = f"score_{pid}"
            preview_scores[pid] = st.session_state.get(key, 5)
        fig = create_wheel_chart(preview_scores, title="Your Wheel of Life")
        st.plotly_chart(fig, use_container_width=True)

        total = get_total_score(preview_scores)
        st.metric("Total Score", f"{total}/60")
        st.caption(get_score_summary(preview_scores))

        st.markdown("#### Pillar Breakdown")
        for pid in sorted(preview_scores.keys()):
            score = preview_scores[pid]
            label = get_score_label(score)
            color = get_score_color(score)
            st.markdown(
                f"<span style='color:{color}'>●</span> **{PILLARS[pid]['display_name']}**: {score}/10 — {label}",
                unsafe_allow_html=True,
            )

    if submitted:
        session_id = submit_assessment(user_id, scores, notes, stages)
        st.success("Assessment saved!")

        changes = compute_changes(user_id)
        if changes:
            st.markdown("#### Changes from Last Assessment")
            cols = st.columns(3)
            for i, (pid, change) in enumerate(changes.items()):
                with cols[i % 3]:
                    delta = change["delta"]
                    arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                    delta_str = f"+{delta}" if delta > 0 else str(delta)
                    st.metric(
                        PILLARS[pid]["display_name"],
                        f"{change['current']}/10",
                        delta=f"{delta_str}" if delta != 0 else None,
                    )

# ── History & Compare ───────────────────────────────────────────────────────
with tab_history:
    history = get_history(user_id)

    if not history:
        st.info("No assessments yet. Take your first assessment above!")
    else:
        st.markdown(f"### Assessment History ({len(history)} assessments)")

        # Trend chart
        if len(history) >= 2:
            st.plotly_chart(create_trend_chart(history), use_container_width=True)

        # Comparison selector
        st.markdown("### Compare Assessments")
        st.caption("Select up to 3 assessments to overlay on the radar chart.")

        options = {
            h["session_id"]: f"{h['assessed_at'][:10]} — Total: {h['total']}/60"
            for h in history
        }
        selected = st.multiselect(
            "Select assessments to compare",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            max_selections=3,
            default=[history[0]["session_id"]] if history else [],
        )

        if selected:
            compare_data = []
            for sid in selected:
                for h in history:
                    if h["session_id"] == sid:
                        compare_data.append({
                            "scores": h["scores"],
                            "label": h["assessed_at"][:10],
                        })
                        break

            if len(compare_data) == 1:
                st.plotly_chart(
                    create_wheel_chart(compare_data[0]["scores"], title=f"Assessment: {compare_data[0]['label']}"),
                    use_container_width=True,
                )
            else:
                st.plotly_chart(create_comparison_chart(compare_data), use_container_width=True)

        # Assessment table
        st.markdown("### All Assessments")
        for h in history:
            with st.expander(f"{h['assessed_at'][:10]} — Total: {h['total']}/60"):
                cols = st.columns(6)
                for i, pid in enumerate(sorted(h["scores"].keys())):
                    with cols[i]:
                        score = h["scores"][pid]
                        color = get_score_color(score)
                        st.markdown(f"**{PILLARS[pid]['display_name']}**")
                        st.markdown(
                            f"<h2 style='color:{color}; margin:0'>{score}</h2>",
                            unsafe_allow_html=True,
                        )
                        st.caption(get_score_label(score))
