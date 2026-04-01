"""Precision Plans page - dedicated lifestyle program builder workspace."""

from __future__ import annotations

import streamlit as st

from components.custom_theme import render_hero_banner, render_hero_stats, render_section_header
from services.ai_cds_service import (
    build_lifestyle_intervention_support,
    build_precision_plan,
    build_precision_plan_markdown,
    build_precision_plan_weekly_schedule,
    get_lifestyle_evidence_base,
    get_precision_plan_goals,
    get_precision_plan_templates,
)
from services.clinical_command_service import build_clinical_snapshot


def _domain_by_name(snapshot: dict) -> dict[str, dict]:
    rows = snapshot.get("organ_domain_categories", []) or []
    return {row.get("domain_name"): row for row in rows if row.get("domain_name")}


def _render_priority_domains(plan: dict, snapshot: dict) -> None:
    render_section_header(
        "Priority Domains",
        "Current risk and confidence profile for domains selected by this plan.",
    )
    by_name = _domain_by_name(snapshot)
    domains = plan.get("priority_domains", [])
    if not domains:
        st.info("No priority domains available yet.")
        return

    cols = st.columns(len(domains))
    for idx, name in enumerate(domains):
        row = by_name.get(name)
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                if not row:
                    st.caption("No score data available.")
                    continue
                score_10 = row.get("score_10")
                confidence = row.get("confidence_pct", 0)
                elevated = row.get("elevated_or_worse", 0)
                if score_10 is None:
                    st.metric("Domain Score", "N/A")
                else:
                    st.metric("Domain Score", f"{score_10}/10")
                st.caption(f"Confidence: {confidence}% | Elevated+: {elevated}")
                systems = row.get("systems_covered") or []
                if systems:
                    st.caption("Covered: " + ", ".join(systems))


def _render_tracks(plan: dict) -> None:
    render_section_header("Action Tracks", "Structured tracks generated for this 8-week cycle.")
    tracks = plan.get("tracks", [])
    if not tracks:
        st.info("No action tracks generated yet.")
        return
    for track in tracks:
        with st.expander(track.get("title", "Track"), expanded=True):
            for action in track.get("actions", []):
                st.markdown(f"- {action}")


def _render_weekly_schedule(plan: dict) -> None:
    render_section_header("8-Week Roadmap", "Execution phases with checkpoints and progression.")
    weeks = build_precision_plan_weekly_schedule(plan)
    if not weeks:
        st.info("No weekly roadmap generated yet.")
        return
    st.dataframe(weeks, use_container_width=True, hide_index=True)


def _render_evidence(plan: dict, evidence_by_topic: dict[str, dict]) -> None:
    render_section_header("Evidence Matrix", "Primary sources backing the selected plan.")
    topics = plan.get("evidence_topics", [])
    if not topics:
        st.info("No evidence topics linked yet.")
        return

    for topic in topics:
        ev = evidence_by_topic.get(topic)
        with st.container(border=True):
            st.markdown(f"**{topic}**")
            if not ev:
                st.caption("Source pending")
                continue
            st.caption(
                f"{ev.get('evidence')} ({ev.get('source_type')}, {ev.get('year')})"
            )
            if ev.get("pmid"):
                st.caption(f"PMID: {ev.get('pmid')}")
            if ev.get("doi"):
                st.caption(f"DOI: {ev.get('doi')}")
            st.link_button("Open source", ev.get("link"), use_container_width=True)


def _render_checkpoints(plan: dict) -> None:
    left, right = st.columns(2)
    with left:
        render_section_header("Checkpoints", "Behavior and execution checks.")
        for item in plan.get("checkpoints", []):
            st.markdown(f"- {item}")
    with right:
        render_section_header("Retest Windows", "When to re-evaluate labs and score trends.")
        for item in plan.get("retest_windows", []):
            st.markdown(f"- {item}")


user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()

snapshot = build_clinical_snapshot(user_id)
evidence_rows = get_lifestyle_evidence_base()
evidence_by_topic = {row.get("topic"): row for row in evidence_rows}

render_hero_banner(
    "Precision Plans",
    "Dedicated lifestyle intervention workspace inspired by modern precision-health plan builders.",
)
st.caption(
    "This is a full section for generating, reviewing, and exporting structured 8-week plans. "
    "It is no longer embedded as a small block in Clinical Summary."
)

goal_options = get_precision_plan_goals()
template_options = get_precision_plan_templates()
goal_map = {row["label"]: row["code"] for row in goal_options}
template_map = {row["label"]: row["code"] for row in template_options}

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    selected_goal_label = st.selectbox(
        "Primary Goal",
        options=list(goal_map.keys()),
        index=0,
        key="precision_page_goal",
    )
with c2:
    selected_template_label = st.selectbox(
        "Plan Template",
        options=list(template_map.keys()),
        index=0,
        key="precision_page_template",
    )
with c3:
    st.caption(" ")
    generate_now = st.button(
        "Generate Plan",
        type="primary",
        use_container_width=True,
        key="precision_page_generate",
    )

if generate_now or "precision_page_plan" not in st.session_state:
    st.session_state["precision_page_plan"] = build_precision_plan(
        snapshot,
        goal_code=goal_map[selected_goal_label],
        template_code=template_map[selected_template_label],
    )

plan = st.session_state.get("precision_page_plan")
if not plan:
    st.error("Unable to generate precision plan right now.")
    st.stop()

render_hero_stats(
    [
        {"icon": "🎯", "value": plan.get("goal_label", "N/A"), "label": "Primary Goal", "color": "#6750A4"},
        {"icon": "🧭", "value": plan.get("template_label", "N/A"), "label": "Template", "color": "#1A73E8"},
        {"icon": "📅", "value": f"{plan.get('horizon_weeks', 8)} Weeks", "label": "Horizon", "color": "#1E8E3E"},
        {"icon": "🫀", "value": len(plan.get("priority_domains", [])), "label": "Priority Domains", "color": "#E8710A"},
    ]
)

overview_tab, roadmap_tab, evidence_tab, export_tab = st.tabs(
    ["Plan Overview", "Weekly Roadmap", "Evidence", "Export"]
)

with overview_tab:
    _render_priority_domains(plan, snapshot)
    st.divider()
    _render_tracks(plan)
    st.divider()
    _render_checkpoints(plan)
    st.divider()
    render_section_header(
        "Live Recommendation Snapshot",
        "Current domain-level suggestions derived from latest profile, scores, and wearables.",
    )
    recommendations = build_lifestyle_intervention_support(snapshot)
    for item in recommendations:
        with st.container(border=True):
            st.markdown(f"**{item.get('domain')}** ({item.get('priority')})")
            st.caption(item.get("trigger"))
            st.markdown(item.get("recommendation"))

with roadmap_tab:
    _render_weekly_schedule(plan)

with evidence_tab:
    _render_evidence(plan, evidence_by_topic)

with export_tab:
    render_section_header("Export & Sharing", "Download plan for physician review or patient briefing.")
    plan_markdown = build_precision_plan_markdown(plan, evidence_by_topic)
    st.download_button(
        "Download Precision Plan (Markdown)",
        data=plan_markdown,
        file_name=f"precision_plan_{plan.get('goal_code', 'lifestyle')}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.code(plan_markdown, language="markdown")
    st.info(plan.get("disclaimer"))
