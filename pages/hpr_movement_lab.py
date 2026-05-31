"""HPR Movement Lab integration page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.hpr_service import (
    SCORE_FORMULA_CAVEAT,
    build_anchor_rows,
    get_categories,
    get_category_label,
    get_category_rationale,
    get_domain_label,
    get_domain_scores,
    get_evidence_audit,
    get_evidence_references,
    get_metrics_by_domain,
    get_protocol,
    get_protocol_domains,
    get_protocol_rows,
    get_sample_assessment,
    infer_metric_score,
    score_band,
)


A = APPLE
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()

render_hero_banner(
    "HPR Movement Lab",
    "Movement medicine protocols, visible score anchors, prescription examples, "
    "and evidence audit imported from the HPR reference app.",
)


def _status_chip(text: str, color: str) -> str:
    return (
        f'<span style="display:inline-flex;align-items:center;border-radius:999px;'
        f'padding:5px 10px;background:{color}18;color:{color};font-size:12px;'
        f'font-weight:700;border:1px solid {color}35">{text}</span>'
    )


def _metric_label(metric: dict) -> str:
    unit = metric.get("unit")
    label = metric.get("label", metric.get("key", "Metric"))
    return f"{label} ({unit})" if unit else label


categories = get_categories()
category = st.radio(
    "Testing category",
    options=categories,
    format_func=get_category_label,
    horizontal=True,
    key="hpr_category",
)

rationale = get_category_rationale(category)
protocol = get_protocol(category)

with st.container(border=True):
    col_text, col_status = st.columns([4, 1])
    with col_text:
        st.markdown(f"**{get_category_label(category)} rationale**")
        st.write(rationale.get("rationale", "No rationale found for this category."))
        st.caption(rationale.get("scoring_note", ""))
    with col_status:
        st.markdown(
            _status_chip("Audit mode", A["orange"]),
            unsafe_allow_html=True,
        )

overview_tab, protocol_tab, calculator_tab, prescription_tab, audit_tab = st.tabs(
    [
        "Overview",
        "Protocol Reference",
        "Metric Calculator",
        "Prescription",
        "Evidence Audit",
    ]
)

with overview_tab:
    sample = get_sample_assessment(category)
    render_section_header("Extracted Assessment Snapshot", "Demo scores and workflow from the HPR reference model")
    st.caption(SCORE_FORMULA_CAVEAT)

    if not sample:
        st.info("No sample assessment is available for this category yet.")
    else:
        domain_scores = get_domain_scores(sample)
        overall = sample.get("overall_score")
        confidence = sample.get("overall_confidence")

        cols = st.columns(5)
        with cols[0]:
            st.metric(
                "Overall",
                f"{float(overall):.1f}/10" if overall is not None else "N/A",
                f"{float(confidence) * 100:.0f}% confidence" if confidence else None,
            )
        for index, score in enumerate(domain_scores, start=1):
            with cols[index]:
                st.metric(
                    score["label"],
                    f"{score['score']:.1f}/10",
                    (
                        f"{float(score['confidence']) * 100:.0f}% confidence"
                        if score.get("confidence")
                        else None
                    ),
                )

        if domain_scores:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=[item["label"] for item in domain_scores],
                        y=[item["score"] for item in domain_scores],
                        marker_color=[A["red"], A["blue"], A["teal"], A["purple"]],
                    )
                ]
            )
            fig.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=20, b=10),
                yaxis=dict(range=[0, 10], title="Score / 10"),
                xaxis=dict(title=""),
                paper_bgcolor=A["chart_bg"],
                plot_bgcolor=A["chart_bg"],
                font=dict(color=A["chart_text"]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        red_flags = sample.get("red_flags", [])
        if red_flags:
            st.markdown("**Flags from the extracted demo case**")
            for flag in red_flags:
                severity = str(flag.get("severity", "note")).title()
                st.warning(
                    f"{severity}: {get_domain_label(flag.get('domain', ''))} - "
                    f"{flag.get('metric', 'Metric')}: {flag.get('note', '')}"
                )

        workflow_steps = sample.get("workflow_steps", [])
        if workflow_steps:
            done = sum(1 for step in workflow_steps if step.get("status") == "completed")
            st.progress(
                done / len(workflow_steps),
                text=f"{done}/{len(workflow_steps)} workflow steps complete",
            )

with protocol_tab:
    render_section_header(
        f"{get_category_label(category)} Protocol Reference",
        "Equipment-matched rows, reference ranges, expected values, and evidence notes",
    )
    st.write(protocol.get("description", ""))
    st.caption(protocol.get("scoring_anchor", ""))

    domains = ["All"] + get_protocol_domains(category)
    selected_domain = st.selectbox("Domain", domains, key="hpr_protocol_domain")
    rows = get_protocol_rows(category, selected_domain)

    if rows:
        df = pd.DataFrame(rows)
        display_columns = [
            "domain",
            "metric",
            "equipment",
            "protocol",
            "unit",
            "reference_range",
            "expected",
            "direction",
            "notes",
        ]
        available_columns = [column for column in display_columns if column in df.columns]
        renamed = df[available_columns].rename(
            columns={
                "domain": "Domain",
                "metric": "Metric",
                "equipment": "Equipment",
                "protocol": "Protocol",
                "unit": "Unit",
                "reference_range": "Reference Range",
                "expected": "Expected",
                "direction": "Direction",
                "notes": "Evidence Notes",
            }
        )
        st.dataframe(renamed, use_container_width=True, hide_index=True)
    else:
        st.info("No protocol rows found for this filter.")

    with st.expander("Category references", expanded=False):
        for reference in protocol.get("references", []):
            st.markdown(f"- {reference}")

with calculator_tab:
    render_section_header(
        "Visible Anchor Calculator",
        "Inferred metric score from public norm anchors only",
    )
    st.caption(SCORE_FORMULA_CAVEAT)

    metric_domains = ["strength", "movement", "cardiovascular", "cognitive"]
    selected_metric_domain = st.selectbox(
        "Metric domain",
        metric_domains,
        format_func=get_domain_label,
        key="hpr_metric_domain",
    )
    metric_options = get_metrics_by_domain(selected_metric_domain)
    metric_lookup = {metric["key"]: metric for metric in metric_options}
    selected_metric_key = st.selectbox(
        "Metric",
        list(metric_lookup.keys()),
        format_func=lambda key: _metric_label(metric_lookup[key]),
        key="hpr_metric",
    )
    selected_metric = metric_lookup[selected_metric_key]
    norms = selected_metric.get("norms", {}).get(category)

    if not norms:
        st.info("This metric does not have visible norm anchors for the selected category.")
    else:
        default_value = float(norms.get("expected", norms.get("min", 0)))
        raw_value = st.number_input(
            f"Raw value ({selected_metric.get('unit', 'unit')})",
            value=default_value,
            step=0.1,
            key="hpr_raw_value",
        )
        inferred_score = infer_metric_score(raw_value, norms)

        score_cols = st.columns(3)
        score_cols[0].metric(
            "Inferred metric score",
            f"{inferred_score:.1f}/10" if inferred_score is not None else "N/A",
        )
        score_cols[1].metric("Band", score_band(inferred_score))
        score_cols[2].metric(
            "Direction",
            "Higher is better"
            if selected_metric.get("direction") == "higher_better"
            else "Lower is better",
        )

        if inferred_score is not None:
            st.progress(
                inferred_score / 10,
                text=f"{inferred_score:.1f}/10 inferred from visible anchors",
            )

        st.markdown("**Visible anchors**")
        st.dataframe(pd.DataFrame(build_anchor_rows(norms)), use_container_width=True, hide_index=True)
        st.markdown("**Metric notes**")
        st.write(selected_metric.get("notes", ""))

with prescription_tab:
    render_section_header(
        "Extracted Prescription Examples",
        "Sample FITT-VP and periodization content from the HPR reference model",
    )
    st.caption(
        "These are category/sample prescription examples from the HPR model. "
        "They are not yet generated from this app user's personal movement data."
    )

    sample = get_sample_assessment(category)
    prescriptions = sample.get("prescriptions", {})
    if not prescriptions:
        st.info("No prescription example is available for this category.")
    else:
        prescription_domain = st.selectbox(
            "Prescription domain",
            list(prescriptions.keys()),
            format_func=get_domain_label,
            key="hpr_prescription_domain",
        )
        rx = prescriptions[prescription_domain]

        st.markdown(f"**Goal:** {rx.get('goal', '')}")
        st.markdown(f"**Principle:** {rx.get('principle', '')}")

        fitt = rx.get("fitt", {})
        fitt_cols = st.columns(4)
        for column, (label, key) in zip(
            fitt_cols,
            [
                ("Frequency", "frequency"),
                ("Intensity", "intensity"),
                ("Time", "time"),
                ("Type", "type"),
            ],
        ):
            with column:
                st.markdown(f"**{label}**")
                st.write(fitt.get(key, "N/A"))

        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown("**Progression**")
            st.write(rx.get("progression", ""))
            st.markdown("**Retest trigger**")
            st.write(rx.get("retest_trigger", ""))
        with detail_cols[1]:
            st.markdown("**Safety**")
            st.write(rx.get("safety", ""))
            st.markdown("**Monitoring metric**")
            st.write(rx.get("monitoring_metric", ""))

        phases = rx.get("phases", {})
        if phases:
            st.markdown("**Periodization phases**")
            st.dataframe(
                pd.DataFrame(
                    [{"Phase": phase.title(), "Focus": focus} for phase, focus in phases.items()]
                ),
                use_container_width=True,
                hide_index=True,
            )

with audit_tab:
    render_section_header(
        "Evidence and Scoring Audit",
        "What is extracted, what is corrected, and what still needs validation",
    )
    audit = get_evidence_audit()

    st.warning(audit.get("score_formula_status", SCORE_FORMULA_CAVEAT))
    audit_cols = st.columns(2)
    audit_cols[0].metric("Extraction status", audit.get("status", "unknown"))
    audit_cols[1].metric("Last reviewed", audit.get("last_reviewed", "unknown"))

    statuses = audit.get("reference_statuses", {})
    if statuses:
        status_rows = []
        for key, item in statuses.items():
            status_rows.append(
                {
                    "Reference": key,
                    "Status": item.get("status"),
                    "Note": item.get("note"),
                    "Original URL": item.get("original_url", ""),
                    "Corrected URL": item.get("corrected_url", ""),
                }
            )
        st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

    st.markdown("**Evidence reference library**")
    for group in get_evidence_references():
        with st.expander(group.get("category", "References")):
            for item in group.get("items", []):
                text = item.get("text", "")
                url = item.get("url")
                if url:
                    st.markdown(f"- [{text}]({url})")
                else:
                    st.markdown(f"- {text}")

    st.markdown("**Integration status**")
    st.markdown(
        "- Imported: category protocols, protocol rows, visible norm anchors, demo scores, "
        "sample prescriptions, and evidence-audit notes.\n"
        "- Not yet validated: hidden HPR normalization, percentile calculation, domain weighting, "
        "overall score formula, and patient-specific movement-data persistence.\n"
        "- Next improvement: add real patient movement test entry and persist raw results before "
        "generating personalized prescriptions."
    )
