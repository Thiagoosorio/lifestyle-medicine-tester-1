"""Science Review dashboard for evidence and scoring governance."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.science_review_service import build_science_review, summarize_counts


A = APPLE
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()

render_hero_banner(
    "Science Review",
    "Audit the app's formula provenance, evidence freshness, HPR movement-science import, "
    "and next scientific validation actions.",
)

review = build_science_review()
score_audit = review["scores"]
evidence_audit = review["evidence"]
hpr_audit = review["hpr"]
actions = review["actions"]

summary_cols = st.columns(4)
summary_cols[0].metric("Score formulas", score_audit["total_scores"])
summary_cols[1].metric("Evidence entries", evidence_audit["total_entries"])
summary_cols[2].metric("HPR protocol rows", hpr_audit["total_protocol_rows"])
summary_cols[3].metric("Review actions", len(actions))

st.caption(
    "This page is a governance dashboard. It does not diagnose, prescribe, or change formula outputs; "
    "it exposes provenance and review status so clinicians can challenge the science openly."
)

tab_actions, tab_scores, tab_evidence, tab_hpr = st.tabs(
    ["Action Plan", "Score Governance", "Evidence Library", "HPR Movement"]
)

with tab_actions:
    render_section_header("Scientific Improvement Plan", "Highest-value review actions from the current app state")
    st.dataframe(pd.DataFrame(actions), use_container_width=True, hide_index=True)

    st.markdown("**Review principles**")
    st.markdown(
        "- Do not upgrade a research/derived score to validated without an explicit source and test fixture.\n"
        "- Do not change formulas silently; add a source-linked test before changing clinical math.\n"
        "- Prefer current guidelines and systematic reviews for recommendations, while keeping landmark derivation studies for formula provenance.\n"
        "- Keep HPR movement scores in audit mode until the hidden normalization and composite formulas are independently reconstructed or replaced."
    )

with tab_scores:
    render_section_header("Score Governance", "Formula tiers, lifecycle labels, domains, and metadata gaps")

    col_tier, col_lifecycle = st.columns(2)
    with col_tier:
        st.markdown("**Formula tier mix**")
        st.dataframe(pd.DataFrame(summarize_counts(score_audit["tier_counts"])), hide_index=True, use_container_width=True)
    with col_lifecycle:
        st.markdown("**Lifecycle mix**")
        st.dataframe(pd.DataFrame(summarize_counts(score_audit["lifecycle_counts"])), hide_index=True, use_container_width=True)

    domain_rows = summarize_counts(score_audit["domain_counts"])
    if domain_rows:
        fig = go.Figure(
            go.Bar(
                x=[row["Count"] for row in domain_rows],
                y=[row["Label"] for row in domain_rows],
                orientation="h",
                marker_color=A["indigo"],
            )
        )
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=A["chart_bg"],
            plot_bgcolor=A["chart_bg"],
            font=dict(color=A["chart_text"]),
            xaxis_title="Scores",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    if score_audit["issues"]:
        st.markdown("**Metadata issues to review**")
        st.dataframe(pd.DataFrame(score_audit["issues"]), use_container_width=True, hide_index=True)
    else:
        st.success("No score metadata issues detected by the governance scan.")

    with st.expander("All score rows", expanded=False):
        st.dataframe(pd.DataFrame(score_audit["score_rows"]), use_container_width=True, hide_index=True)

with tab_evidence:
    render_section_header("Evidence Library", "Freshness, missing metadata, and review candidates")

    col_grade, col_fresh = st.columns(2)
    with col_grade:
        st.markdown("**Evidence grades**")
        st.dataframe(pd.DataFrame(summarize_counts(evidence_audit["grade_counts"])), hide_index=True, use_container_width=True)
    with col_fresh:
        st.markdown("**Freshness status**")
        st.dataframe(pd.DataFrame(summarize_counts(evidence_audit["freshness_counts"])), hide_index=True, use_container_width=True)

    st.markdown("**Refresh candidates**")
    if evidence_audit["refresh_candidates"]:
        st.dataframe(pd.DataFrame(evidence_audit["refresh_candidates"]), use_container_width=True, hide_index=True)
    else:
        st.success("No stale or legacy evidence candidates detected.")

    st.markdown("**Missing metadata**")
    if evidence_audit["missing_metadata"]:
        st.dataframe(pd.DataFrame(evidence_audit["missing_metadata"]), use_container_width=True, hide_index=True)
    else:
        st.success("No required evidence metadata gaps detected.")

with tab_hpr:
    render_section_header("HPR Movement Science Import", "Current fidelity and validation limits")

    hpr_cols = st.columns(4)
    hpr_cols[0].metric("Categories", len(hpr_audit["categories"]))
    hpr_cols[1].metric("Protocol rows", hpr_audit["total_protocol_rows"])
    hpr_cols[2].metric("Reference issues", hpr_audit["reference_issue_count"])
    hpr_cols[3].metric("Last reviewed", hpr_audit["last_reviewed"])

    st.warning(hpr_audit["score_formula_status"])
    if hpr_audit.get("consistency_warnings"):
        st.markdown("**Known consistency warnings**")
        st.dataframe(pd.DataFrame(hpr_audit["consistency_warnings"]), use_container_width=True, hide_index=True)
    st.markdown("**Rows by category**")
    st.dataframe(
        pd.DataFrame(
            [
                {"Category": category.title(), "Protocol rows": count}
                for category, count in hpr_audit["rows_by_category"].items()
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(
        "The HPR module is useful for protocol transparency and colleague review, but the app should not "
        "present HPR composite scores as validated until the raw score transformation and weighting model are known."
    )
