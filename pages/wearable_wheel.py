"""Wearable Wheel - 5-domain radar from wearable measurements."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from config.wearable_wheel_data import DOMAIN_ORDER, WEARABLE_METRIC_SPECS, WEARABLE_WHEEL_DOMAINS
from services.wearable_wheel_service import (
    build_wearable_csv_template,
    compute_wearable_wheel,
    get_latest_measurements,
    import_measurements_csv_text,
    save_measurements,
)

user_id = st.session_state.user_id

st.title(":material/donut_small: Wearable Wheel (5 Domains)")
st.caption(
    "Data-driven wheel built from wearable measurements. "
    "Scores are normalized to 0-10 and update as new data arrives."
)


def _build_radar(wheel: dict) -> go.Figure:
    labels = [WEARABLE_WHEEL_DOMAINS[code]["name"] for code in DOMAIN_ORDER]
    values = [wheel["domains"][code]["score_10"] for code in DOMAIN_ORDER]
    labels.append(labels[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(33, 150, 243, 0.18)",
            line=dict(color="#1E88E5", width=2),
            marker=dict(size=7, color="#1E88E5"),
            name="Wearable Wheel",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickvals=[2, 4, 6, 8, 10]),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=False,
        margin=dict(t=40, b=20, l=30, r=30),
        height=500,
    )
    return fig


tab_wheel, tab_upload, tab_data = st.tabs(["Wheel", "Upload", "Data"])

with tab_wheel:
    wheel = compute_wearable_wheel(user_id)
    st.metric("Overall Wearable Score", f"{wheel['overall_score_10']}/10", help="Average across 5 domains.")
    st.plotly_chart(_build_radar(wheel), use_container_width=True)

    col_cards = st.columns(5)
    for idx, domain_code in enumerate(DOMAIN_ORDER):
        domain = wheel["domains"][domain_code]
        with col_cards[idx]:
            st.markdown(f"**{domain['short']}**")
            st.metric(
                WEARABLE_WHEEL_DOMAINS[domain_code]["name"],
                f"{domain['score_10']}/10",
                help=f"Confidence {int(domain['confidence'] * 100)}%. "
                f"Metrics used: {domain['available_metrics']}/{domain['total_metrics']}",
            )
            confidence = int(domain["confidence"] * 100)
            st.progress(confidence / 100.0, text=f"Confidence {confidence}%")
            if domain["is_proxy"]:
                st.caption("Proxy domain")

    if wheel["data_points_used"] == 0:
        st.info("No wearable data yet. Upload CSV or add a manual measurement in the Upload tab.")

with tab_upload:
    st.markdown("### CSV Import")
    template_csv = build_wearable_csv_template()
    st.download_button(
        "Download CSV Template",
        data=template_csv,
        file_name="wearable_wheel_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Upload wearable measurements CSV", type=["csv"], key="wearable_csv_upload")
    if uploaded is not None and st.button("Import CSV", type="primary", use_container_width=True):
        payload = uploaded.getvalue().decode("utf-8", errors="ignore")
        summary = import_measurements_csv_text(user_id, payload)
        st.success(
            f"Imported {summary['inserted']} rows "
            f"(unknown: {summary['skipped_unknown']}, invalid: {summary['skipped_invalid']})."
        )
        st.rerun()

    st.markdown("### Quick Manual Entry")
    with st.form("wearable_manual_entry"):
        metric_code = st.selectbox(
            "Metric",
            options=sorted(WEARABLE_METRIC_SPECS.keys()),
            format_func=lambda c: f"{WEARABLE_METRIC_SPECS[c]['label']} ({c})",
        )
        value = st.number_input("Value", value=0.0, format="%.4f")
        measured_at = st.text_input("Measured At (ISO)", value="", placeholder="2026-03-26T07:00:00")
        source = st.text_input("Source", value="manual")
        submit_manual = st.form_submit_button("Save Measurement", use_container_width=True)

    if submit_manual:
        summary = save_measurements(
            user_id,
            [
                {
                    "metric_code": metric_code,
                    "value": value,
                    "measured_at": measured_at.strip() or None,
                    "source": source.strip() or "manual",
                }
            ],
        )
        if summary["inserted"] == 1:
            st.success("Measurement saved.")
            st.rerun()
        else:
            st.error("Measurement could not be saved.")

with tab_data:
    st.markdown("### Latest Measurements")
    latest = get_latest_measurements(user_id)
    if not latest:
        st.info("No wearable measurements available.")
    else:
        rows = []
        for code, row in sorted(latest.items(), key=lambda item: item[1]["measured_at"], reverse=True):
            spec = WEARABLE_METRIC_SPECS.get(code, {})
            rows.append(
                {
                    "metric_code": code,
                    "metric": spec.get("label", code),
                    "value": row["value"],
                    "unit": row.get("unit"),
                    "domain": WEARABLE_WHEEL_DOMAINS.get(spec.get("domain"), {}).get("name", "-"),
                    "measured_at": row["measured_at"],
                    "source": row.get("source"),
                }
            )
        st.dataframe(rows, use_container_width=True)

    st.markdown("### Metric Catalog")
    catalog = []
    for code, spec in sorted(WEARABLE_METRIC_SPECS.items()):
        catalog.append(
            {
                "metric_code": code,
                "label": spec["label"],
                "unit": spec.get("unit"),
                "domain": WEARABLE_WHEEL_DOMAINS[spec["domain"]]["name"],
                "mode": spec["score_mode"],
            }
        )
    st.dataframe(catalog, use_container_width=True)
