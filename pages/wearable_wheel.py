"""Wearable Wheel — 5-domain health radar from wearable device measurements."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from config.wearable_wheel_data import (
    DOMAIN_ORDER,
    KNOWN_WEARABLE_SOURCES,
    WEARABLE_METRIC_SPECS,
    WEARABLE_WHEEL_DOMAINS,
)
from services.wearable_wheel_service import (
    build_wearable_csv_template,
    compute_wearable_wheel,
    get_latest_measurements,
    import_measurements_csv_text,
    save_measurements,
)

A = APPLE
user_id = st.session_state.user_id


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB to rgba(r,g,b,a) for Plotly compatibility."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

render_hero_banner(
    "Wearable Wheel",
    "Data-driven health radar built from your wearable measurements. "
    "5 domains scored 0-10 with readiness and resilience tracking."
)

# ══════════════════════════════════════════════════════════════════════════
# Compute wheel data
# ══════════════════════════════════════════════════════════════════════════
wheel = compute_wearable_wheel(user_id)

tab_wheel, tab_upload, tab_data = st.tabs(["Wheel", "Upload", "Data"])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Wheel — Radar + Domain Cards
# ══════════════════════════════════════════════════════════════════════════
with tab_wheel:
    if wheel["data_points_used"] == 0:
        # Empty state
        empty_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_xl"]};padding:40px;text-align:center;margin:20px 0">'
            f'<div style="font-size:48px;margin-bottom:16px">&#9201;</div>'
            f'<div style="font-family:{A["font_display"]};font-size:18px;font-weight:600;'
            f'color:{A["label_primary"]};margin-bottom:8px">No Wearable Data Yet</div>'
            f'<div style="font-size:13px;color:{A["label_secondary"]};max-width:400px;margin:0 auto">'
            f'Upload a CSV from your wearable device or add measurements manually '
            f'in the <strong>Upload</strong> tab to see your health radar.</div></div>'
        )
        st.markdown(empty_html, unsafe_allow_html=True)
    else:
        # ── Overall Score Ring + Readiness/Resilience ──────────────────
        col_ring, col_rr = st.columns([1, 2])

        with col_ring:
            score = wheel["overall_score_10"]
            score_100 = wheel["overall_score_100"]
            if score_100 >= 80:
                ring_color = "#30D158"
            elif score_100 >= 60:
                ring_color = A["blue"]
            elif score_100 >= 40:
                ring_color = "#FFD60A"
            else:
                ring_color = "#FF453A"

            radius = 58
            circumference = 2 * 3.14159 * radius
            offset = circumference * (1 - score_100 / 100)

            ring_html = (
                f'<div style="text-align:center;padding:16px">'
                f'<svg width="150" height="150" viewBox="0 0 150 150">'
                f'<circle cx="75" cy="75" r="{radius}" fill="none" stroke="{A["bg_tertiary"]}" stroke-width="10"/>'
                f'<circle cx="75" cy="75" r="{radius}" fill="none" stroke="{ring_color}" stroke-width="10" '
                f'stroke-linecap="round" stroke-dasharray="{circumference}" '
                f'stroke-dashoffset="{offset}" transform="rotate(-90 75 75)"/>'
                f'<text x="75" y="68" text-anchor="middle" fill="{A["label_primary"]}" '
                f'font-family="{A["font_display"]}" font-size="32" font-weight="700">{score}</text>'
                f'<text x="75" y="88" text-anchor="middle" fill="{A["label_tertiary"]}" '
                f'font-family="{A["font_text"]}" font-size="11">/10</text>'
                f'</svg>'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-top:4px">Overall Score</div>'
                f'</div>'
            )
            st.markdown(ring_html, unsafe_allow_html=True)

        with col_rr:
            # Readiness and Resilience cards
            rr_html = (
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px 0">'
            )
            # Readiness
            r_score = wheel["overall_readiness_10"]
            r_color = "#30D158" if r_score >= 7 else "#FFD60A" if r_score >= 5 else "#FF453A"
            rr_html += (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:6px">Readiness</div>'
                f'<div style="font-family:{A["font_display"]};font-size:32px;font-weight:700;'
                f'color:{r_color}">{r_score}</div>'
                f'<div style="font-size:11px;color:{A["label_secondary"]};margin-top:4px">'
                f'Short-horizon state</div></div>'
            )
            # Resilience
            s_score = wheel["overall_resilience_10"]
            s_color = "#30D158" if s_score >= 7 else "#FFD60A" if s_score >= 5 else "#FF453A"
            rr_html += (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:6px">Resilience</div>'
                f'<div style="font-family:{A["font_display"]};font-size:32px;font-weight:700;'
                f'color:{s_color}">{s_score}</div>'
                f'<div style="font-size:11px;color:{A["label_secondary"]};margin-top:4px">'
                f'30-day stability</div></div>'
            )
            rr_html += '</div>'

            # Data points info
            rr_html += (
                f'<div style="font-size:11px;color:{A["label_tertiary"]};text-align:center;padding:4px 0">'
                f'{wheel["data_points_used"]} metrics tracked across 5 domains</div>'
            )
            st.markdown(rr_html, unsafe_allow_html=True)

        # ── Radar Chart (premium multi-layer) ─────────────────────────
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_section_header("Health Radar", "5-domain wearable assessment")

        labels = [WEARABLE_WHEEL_DOMAINS[code]["name"] for code in DOMAIN_ORDER]
        values = [wheel["domains"][code]["score_10"] for code in DOMAIN_ORDER]
        colors = [WEARABLE_WHEEL_DOMAINS[code]["color"] for code in DOMAIN_ORDER]
        labels_closed = labels + [labels[0]]
        values_closed = values + [values[0]]
        colors_closed = colors + [colors[0]]

        fig = go.Figure()

        # Layer 1: Zone rings (subtle background zones at 4, 7, 10)
        for zone_val, zone_opacity in [(10, 0.03), (7, 0.04), (4, 0.05)]:
            fig.add_trace(go.Scatterpolar(
                r=[zone_val] * (len(DOMAIN_ORDER) + 1),
                theta=labels_closed,
                fill="toself",
                fillcolor=f"rgba(103,80,164,{zone_opacity})",
                line=dict(color=f"rgba(103,80,164,{zone_opacity + 0.04})", width=1),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Layer 2: Individual domain wedge fills (colored sectors)
        for i, code in enumerate(DOMAIN_ORDER):
            domain = wheel["domains"][code]
            color = WEARABLE_WHEEL_DOMAINS[code]["color"]
            # Create a wedge: two adjacent vertices at score, rest at 0
            r_vals = [0.0] * len(DOMAIN_ORDER)
            r_vals[i] = domain["score_10"]
            # Also fill the adjacent vertex slightly for a wedge effect
            next_i = (i + 1) % len(DOMAIN_ORDER)
            prev_i = (i - 1) % len(DOMAIN_ORDER)
            r_vals[next_i] = domain["score_10"] * 0.15
            r_vals[prev_i] = domain["score_10"] * 0.15
            r_vals_closed = r_vals + [r_vals[0]]
            fig.add_trace(go.Scatterpolar(
                r=r_vals_closed,
                theta=labels_closed,
                fill="toself",
                fillcolor=_hex_to_rgba(color, 0.12),
                line=dict(color="rgba(0,0,0,0)", width=0),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Layer 3: Main polygon — thick colored line with gradient fill
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            fillcolor="rgba(103, 80, 164, 0.15)",
            line=dict(color=A["indigo"], width=3),
            marker=dict(
                size=12,
                color=colors_closed,
                line=dict(color="white", width=2.5),
                symbol="circle",
            ),
            name="Score",
            customdata=[
                f"{WEARABLE_WHEEL_DOMAINS[code]['name']}: {wheel['domains'][code]['score_10']}/10"
                for code in DOMAIN_ORDER
            ] + [f"{WEARABLE_WHEEL_DOMAINS[DOMAIN_ORDER[0]]['name']}: {wheel['domains'][DOMAIN_ORDER[0]]['score_10']}/10"],
            hovertemplate="%{customdata}<extra></extra>",
        ))

        # Layer 4: Score value annotations on each vertex
        import math as _math
        n = len(DOMAIN_ORDER)
        for i, code in enumerate(DOMAIN_ORDER):
            angle_deg = 90 - (360 / n) * i  # Plotly polar starts at top, goes clockwise
            angle_rad = _math.radians(angle_deg)
            score_val = wheel["domains"][code]["score_10"]
            # Position label slightly outside the data point
            r_label = min(score_val + 0.8, 10.5)
            fig.add_trace(go.Scatterpolar(
                r=[r_label],
                theta=[labels[i]],
                mode="text",
                text=[f"<b>{score_val}</b>"],
                textfont=dict(
                    size=13,
                    color=WEARABLE_WHEEL_DOMAINS[code]["color"],
                    family=A["font_display"],
                ),
                showlegend=False,
                hoverinfo="skip",
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 11],
                    tickvals=[2, 4, 6, 8, 10],
                    ticktext=["2", "4", "6", "8", "10"],
                    tickfont=dict(size=9, color=A["label_quaternary"]),
                    gridcolor="rgba(0,0,0,0.05)",
                    linecolor="rgba(0,0,0,0)",
                ),
                angularaxis=dict(
                    tickfont=dict(size=13, family=A["font_display"], color=A["label_primary"]),
                    gridcolor="rgba(0,0,0,0.06)",
                    linecolor="rgba(0,0,0,0.06)",
                    direction="clockwise",
                ),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(t=40, b=40, l=80, r=80),
            height=480,
            font=dict(family=A["font_text"]),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Zone legend
        zone_legend = (
            f'<div style="display:flex;justify-content:center;gap:20px;font-size:11px;'
            f'color:{A["label_tertiary"]};margin-top:-8px;margin-bottom:16px">'
            f'<span><span style="color:#FF453A">&#9679;</span> 0-4 Needs attention</span>'
            f'<span><span style="color:#FFD60A">&#9679;</span> 4-7 Developing</span>'
            f'<span><span style="color:#30D158">&#9679;</span> 7-10 Optimal</span></div>'
        )
        st.markdown(zone_legend, unsafe_allow_html=True)

        # ── Domain Cards ───────────────────────────────────────────────
        render_section_header("Domain Breakdown", "Score, readiness, resilience per domain")

        cards_html = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">'
        for code in DOMAIN_ORDER:
            domain = wheel["domains"][code]
            d_spec = WEARABLE_WHEEL_DOMAINS[code]
            color = d_spec["color"]
            score_10 = domain["score_10"]
            conf = int(domain["confidence"] * 100)
            avail = domain["available_metrics"]
            total = domain["total_metrics"]

            # Score color
            if score_10 >= 8:
                sc = "#30D158"
            elif score_10 >= 6:
                sc = A["blue"]
            elif score_10 >= 4:
                sc = "#FFD60A"
            else:
                sc = "#FF453A"

            proxy_badge = ""
            if domain["is_proxy"]:
                proxy_badge = (
                    f'<div style="font-size:9px;color:{A["label_quaternary"]};'
                    f'background:{A["bg_tertiary"]};padding:2px 6px;border-radius:4px;'
                    f'display:inline-block;margin-top:6px">Proxy</div>'
                )

            cards_html += (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-top:3px solid {color};border-radius:{A["radius_lg"]};'
                f'padding:16px;text-align:center">'
                # Domain name
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.04em;color:{color};margin-bottom:8px">'
                f'{d_spec["short"]}</div>'
                f'<div style="font-size:12px;font-weight:500;color:{A["label_primary"]};'
                f'margin-bottom:10px">{d_spec["name"]}</div>'
                # Score
                f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                f'color:{sc}">{score_10}</div>'
                f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-bottom:10px">/10</div>'
                # Readiness / Resilience
                f'<div style="display:flex;justify-content:center;gap:12px;margin-bottom:8px">'
                f'<div style="text-align:center">'
                f'<div style="font-size:9px;color:{A["label_tertiary"]};text-transform:uppercase">Ready</div>'
                f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
                f'color:{A["label_primary"]}">{domain["readiness_10"]}</div></div>'
                f'<div style="width:1px;background:{A["separator"]}"></div>'
                f'<div style="text-align:center">'
                f'<div style="font-size:9px;color:{A["label_tertiary"]};text-transform:uppercase">Stable</div>'
                f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
                f'color:{A["label_primary"]}">{domain["resilience_10"]}</div></div></div>'
                # Confidence bar
                f'<div style="background:{A["bg_tertiary"]};border-radius:4px;height:4px;'
                f'margin:8px 0 4px 0;overflow:hidden">'
                f'<div style="background:{color};height:100%;width:{conf}%;border-radius:4px"></div></div>'
                f'<div style="font-size:9px;color:{A["label_tertiary"]}">'
                f'{avail}/{total} metrics &middot; {conf}% conf</div>'
                f'{proxy_badge}'
                f'</div>'
            )
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        # ── Metric Detail (expandable per domain) ─────────────────────
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        render_section_header("Metric Details", "Individual metric scores within each domain")

        for code in DOMAIN_ORDER:
            domain = wheel["domains"][code]
            d_spec = WEARABLE_WHEEL_DOMAINS[code]
            color = d_spec["color"]
            used_codes = domain.get("metric_codes_used", [])

            if not used_codes:
                continue

            with st.expander(f"{d_spec['name']} — {len(used_codes)} metrics"):
                metrics_html = ""
                for mc in used_codes:
                    m = wheel["metrics"].get(mc)
                    if not m:
                        continue
                    ms = m["score_100"]
                    if ms >= 80:
                        bar_color = "#30D158"
                    elif ms >= 60:
                        bar_color = A["blue"]
                    elif ms >= 40:
                        bar_color = "#FFD60A"
                    else:
                        bar_color = "#FF453A"

                    trend_icon = ""
                    td = m.get("trend_delta_100", 0)
                    if td > 2:
                        trend_icon = f'<span style="color:#30D158;font-size:11px">&#9650; +{td:.0f}</span>'
                    elif td < -2:
                        trend_icon = f'<span style="color:#FF453A;font-size:11px">&#9660; {td:.0f}</span>'

                    unit = m.get("unit") or ""
                    opt_badge = ""
                    if m.get("optional"):
                        opt_badge = (
                            f'<span style="font-size:9px;color:{A["label_quaternary"]};'
                            f'background:{A["bg_tertiary"]};padding:1px 5px;border-radius:3px;'
                            f'margin-left:6px">opt</span>'
                        )

                    metrics_html += (
                        f'<div style="display:flex;align-items:center;gap:10px;'
                        f'padding:8px 0;border-bottom:1px solid {A["separator"]}">'
                        f'<div style="flex:1">'
                        f'<div style="font-size:12px;font-weight:500;color:{A["label_primary"]}">'
                        f'{m["label"]}{opt_badge}</div>'
                        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                        f'{m["latest_raw_value"]:.1f} {unit}</div></div>'
                        f'<div style="width:100px">'
                        f'<div style="background:{A["bg_tertiary"]};border-radius:3px;height:6px;overflow:hidden">'
                        f'<div style="background:{bar_color};height:100%;width:{ms:.0f}%;border-radius:3px"></div></div></div>'
                        f'<div style="font-family:{A["font_display"]};font-size:13px;font-weight:600;'
                        f'color:{bar_color};min-width:35px;text-align:right">{ms:.0f}</div>'
                        f'{trend_icon}'
                        f'</div>'
                    )
                st.markdown(metrics_html, unsafe_allow_html=True)

        # ── Science note ───────────────────────────────────────────────
        note_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px;margin-top:16px">'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'Scores use exponential time-weighting (readiness: 1.5-day half-life, '
            f'resilience: 14-day half-life) with personalized baseline blending after 7+ data points. '
            f'Trend adjustment rewards improving trajectories. '
            f'Proxy domains (Muscle &amp; Bones, Gut &amp; Digestion) are inferred from related metrics '
            f'until dedicated wearable signals are available.</div></div>'
        )
        st.markdown(note_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Upload
# ══════════════════════════════════════════════════════════════════════════
with tab_upload:
    render_section_header("Import Data", "Upload CSV or enter measurements manually")

    # Supported devices
    devices_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:20px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'Supported Devices</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px">'
    )
    device_icons = {
        "Whoop Band": "&#9201;", "Oura Ring": "&#128141;",
        "Garmin": "&#9201;", "CGM FreeStyle Libre": "&#128137;",
        "InBody H40 Home Scale": "&#9878;", "Withings BPM Connect Pro": "&#10084;",
    }
    for dev in ["Whoop Band", "Oura Ring", "Garmin", "CGM FreeStyle Libre", "InBody H40 Home Scale", "Withings BPM Connect Pro"]:
        icon = device_icons.get(dev, "&#128225;")
        devices_html += (
            f'<div style="background:{A["bg_secondary"]};border-radius:8px;'
            f'padding:6px 12px;font-size:12px;color:{A["label_secondary"]}">'
            f'{icon} {dev}</div>'
        )
    devices_html += '</div></div>'
    st.markdown(devices_html, unsafe_allow_html=True)

    # CSV Upload
    render_section_header("CSV Import", "Download template, fill in your data, upload")

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
        st.toast(f"Imported {summary['inserted']} rows ({summary['skipped_unknown']} unknown, {summary['skipped_invalid']} invalid)")
        st.rerun()

    # Manual Entry
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    render_section_header("Quick Manual Entry", "Log a single measurement")

    with st.form("wearable_manual_entry"):
        mc1, mc2 = st.columns(2)
        with mc1:
            metric_code = st.selectbox(
                "Metric",
                options=sorted(WEARABLE_METRIC_SPECS.keys()),
                format_func=lambda c: (
                    f"{WEARABLE_METRIC_SPECS[c]['label']}"
                    + (f" ({WEARABLE_METRIC_SPECS[c].get('unit', '')})" if WEARABLE_METRIC_SPECS[c].get('unit') else "")
                    + (" [optional]" if WEARABLE_METRIC_SPECS[c].get("optional") else "")
                ),
            )
        with mc2:
            value = st.number_input("Value", value=0.0, format="%.2f")

        mc3, mc4 = st.columns(2)
        with mc3:
            measured_at = st.text_input("Date/Time (ISO)", value="", placeholder="2026-03-26T07:00:00")
        with mc4:
            source = st.selectbox("Source Device", options=KNOWN_WEARABLE_SOURCES, index=KNOWN_WEARABLE_SOURCES.index("manual"))

        submit_manual = st.form_submit_button("Save Measurement", use_container_width=True)

    if submit_manual:
        summary = save_measurements(user_id, [{
            "metric_code": metric_code,
            "value": value,
            "measured_at": measured_at.strip() or None,
            "source": source,
        }])
        if summary["inserted"] == 1:
            st.toast("Measurement saved.")
            st.rerun()
        else:
            st.error("Measurement could not be saved.")

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Data
# ══════════════════════════════════════════════════════════════════════════
with tab_data:
    render_section_header("Latest Measurements", "Most recent value per metric")

    latest = get_latest_measurements(user_id)
    if not latest:
        st.info("No wearable measurements available. Upload data in the **Upload** tab.")
    else:
        table_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};overflow:hidden">'
        )
        # Header
        table_html += (
            f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;'
            f'gap:0;padding:10px 16px;background:{A["bg_secondary"]};'
            f'font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">'
            f'<div>Metric</div><div>Value</div><div>Domain</div><div>Source</div><div>Date</div></div>'
        )
        sorted_latest = sorted(latest.items(), key=lambda item: item[1].get("measured_at", ""), reverse=True)
        for code, row in sorted_latest:
            spec = WEARABLE_METRIC_SPECS.get(code, {})
            domain_name = WEARABLE_WHEEL_DOMAINS.get(spec.get("domain", ""), {}).get("name", "-")
            domain_color = WEARABLE_WHEEL_DOMAINS.get(spec.get("domain", ""), {}).get("color", A["label_tertiary"])
            unit = row.get("unit") or spec.get("unit") or ""
            date_str = (row.get("measured_at") or "")[:16]
            table_html += (
                f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;'
                f'gap:0;padding:10px 16px;border-top:1px solid {A["separator"]};'
                f'font-size:12px;color:{A["label_primary"]};align-items:center">'
                f'<div style="font-weight:500">{spec.get("label", code)}</div>'
                f'<div>{row["value"]:.1f} <span style="color:{A["label_tertiary"]}">{unit}</span></div>'
                f'<div><span style="color:{domain_color};font-weight:500">{domain_name}</span></div>'
                f'<div style="color:{A["label_tertiary"]}">{row.get("source", "-")}</div>'
                f'<div style="color:{A["label_tertiary"]};font-size:11px">{date_str}</div></div>'
            )
        table_html += '</div>'
        st.markdown(table_html, unsafe_allow_html=True)

    # Metric catalog
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    with st.expander("Metric Catalog (all supported metrics)"):
        catalog_html = ""
        for d_code in DOMAIN_ORDER:
            d_spec = WEARABLE_WHEEL_DOMAINS[d_code]
            domain_metrics = [
                (c, s) for c, s in sorted(WEARABLE_METRIC_SPECS.items())
                if s.get("domain") == d_code
            ]
            if not domain_metrics:
                continue
            catalog_html += (
                f'<div style="font-size:12px;font-weight:600;color:{d_spec["color"]};'
                f'margin:12px 0 6px 0">{d_spec["name"]}</div>'
            )
            for mc, ms in domain_metrics:
                opt = " [optional]" if ms.get("optional") else ""
                unit = ms.get("unit") or ""
                catalog_html += (
                    f'<div style="display:flex;gap:8px;padding:4px 0;'
                    f'border-bottom:1px solid {A["separator"]};font-size:11px">'
                    f'<div style="color:{A["label_primary"]};flex:1">{ms["label"]}{opt}</div>'
                    f'<div style="color:{A["label_tertiary"]};min-width:60px">{unit}</div>'
                    f'<div style="color:{A["label_tertiary"]};min-width:50px">{mc}</div></div>'
                )
        st.markdown(catalog_html, unsafe_allow_html=True)
