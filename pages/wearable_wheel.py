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
    "5 domains scored 0-10 with daily and baseline tracking."
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
        # ── Custom SVG Radar Chart ─────────────────────────────────────
        import math as _math

        _n = len(DOMAIN_ORDER)
        _cx, _cy = 220, 220  # center
        _max_r = 180  # max radius
        _font = A["font_display"]

        def _polar_xy(angle_idx, radius_frac):
            """Convert domain index + 0-1 fraction to SVG x,y."""
            angle = -_math.pi / 2 + (2 * _math.pi / _n) * angle_idx
            r = _max_r * radius_frac
            return _cx + r * _math.cos(angle), _cy + r * _math.sin(angle)

        # Build SVG
        svg = f'<svg viewBox="0 0 440 440" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:520px;margin:0 auto;display:block">'

        # Defs: gradient for main polygon
        svg += '<defs>'
        svg += '<radialGradient id="radarGrad" cx="50%" cy="50%" r="50%">'
        svg += '<stop offset="0%" stop-color="#6750A4" stop-opacity="0.25"/>'
        svg += '<stop offset="100%" stop-color="#6750A4" stop-opacity="0.05"/>'
        svg += '</radialGradient>'
        # Glow filter
        svg += '<filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/>'
        svg += '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        svg += '</defs>'

        # Background circle
        svg += f'<circle cx="{_cx}" cy="{_cy}" r="{_max_r}" fill="none" stroke="{A["separator"]}" stroke-width="0.5"/>'

        # Grid rings at 2, 4, 6, 8, 10 with zone coloring
        zone_colors = [
            (0.2, "#FF453A", 0.03), (0.4, "#FF453A", 0.02),  # 2, 4 — red zone
            (0.6, "#FFD60A", 0.03), (0.8, "#FFD60A", 0.02),  # 6, 8 — yellow zone
            (1.0, "#30D158", 0.03),  # 10 — green zone
        ]
        for frac, zc, zo in zone_colors:
            r = _max_r * frac
            svg += f'<circle cx="{_cx}" cy="{_cy}" r="{r}" fill="none" stroke="{zc}" stroke-opacity="{zo + 0.06}" stroke-width="1" stroke-dasharray="4 4"/>'

        # Zone fill bands (subtle colored rings)
        # 0-4: faint red, 4-7: faint yellow, 7-10: faint green
        svg += f'<circle cx="{_cx}" cy="{_cy}" r="{_max_r * 0.4}" fill="#FF453A" fill-opacity="0.02"/>'
        svg += f'<circle cx="{_cx}" cy="{_cy}" r="{_max_r * 0.7}" fill="#FFD60A" fill-opacity="0.015"/>'
        svg += f'<circle cx="{_cx}" cy="{_cy}" r="{_max_r}" fill="#30D158" fill-opacity="0.01"/>'

        # Spoke lines
        for i in range(_n):
            x2, y2 = _polar_xy(i, 1.0)
            svg += f'<line x1="{_cx}" y1="{_cy}" x2="{x2}" y2="{y2}" stroke="{A["separator"]}" stroke-width="0.5"/>'

        # Grid tick labels (2, 4, 6, 8, 10) along first spoke
        for val in [2, 4, 6, 8, 10]:
            lx, ly = _polar_xy(0, val / 10.0)
            svg += f'<text x="{lx + 6}" y="{ly + 3}" font-size="8" fill="{A["label_quaternary"]}" font-family="{_font}">{val}</text>'

        # Domain-colored sector fills (wedge between spokes)
        for i, code in enumerate(DOMAIN_ORDER):
            domain = wheel["domains"][code]
            color = WEARABLE_WHEEL_DOMAINS[code]["color"]
            score_frac = domain["score_10"] / 10.0
            # Wedge: center → point on spoke i → arc → point on spoke i+1 → center
            x1, y1 = _polar_xy(i, score_frac)
            x2, y2 = _polar_xy((i + 1) % _n, wheel["domains"][DOMAIN_ORDER[(i + 1) % _n]]["score_10"] / 10.0)
            svg += f'<polygon points="{_cx},{_cy} {x1},{y1} {x2},{y2}" fill="{color}" fill-opacity="0.08"/>'

        # Main data polygon (gradient fill + glow)
        points = []
        for i in range(_n):
            score_frac = wheel["domains"][DOMAIN_ORDER[i]]["score_10"] / 10.0
            x, y = _polar_xy(i, score_frac)
            points.append(f"{x},{y}")
        points_str = " ".join(points)
        svg += f'<polygon points="{points_str}" fill="url(#radarGrad)" stroke="#6750A4" stroke-width="2.5" stroke-linejoin="round" filter="url(#glow)"/>'

        # Data points (large colored dots with white ring)
        for i, code in enumerate(DOMAIN_ORDER):
            domain = wheel["domains"][code]
            color = WEARABLE_WHEEL_DOMAINS[code]["color"]
            score_frac = domain["score_10"] / 10.0
            x, y = _polar_xy(i, score_frac)
            svg += f'<circle cx="{x}" cy="{y}" r="8" fill="{color}" stroke="white" stroke-width="3"/>'

        # Score labels next to each dot
        for i, code in enumerate(DOMAIN_ORDER):
            domain = wheel["domains"][code]
            color = WEARABLE_WHEEL_DOMAINS[code]["color"]
            score_frac = domain["score_10"] / 10.0
            # Position label outside the dot
            lx, ly = _polar_xy(i, min(score_frac + 0.09, 1.05))
            anchor = "middle"
            # Adjust horizontal anchor based on position
            angle = -_math.pi / 2 + (2 * _math.pi / _n) * i
            if _math.cos(angle) > 0.3:
                anchor = "start"
                lx += 10
            elif _math.cos(angle) < -0.3:
                anchor = "end"
                lx -= 10
            svg += (
                f'<text x="{lx}" y="{ly + 4}" text-anchor="{anchor}" '
                f'font-family="{_font}" font-size="14" font-weight="700" fill="{color}">'
                f'{domain["score_10"]}</text>'
            )

        # Domain name labels at the outer edge
        for i, code in enumerate(DOMAIN_ORDER):
            d_spec = WEARABLE_WHEEL_DOMAINS[code]
            lx, ly = _polar_xy(i, 1.18)
            anchor = "middle"
            angle = -_math.pi / 2 + (2 * _math.pi / _n) * i
            if _math.cos(angle) > 0.3:
                anchor = "start"
            elif _math.cos(angle) < -0.3:
                anchor = "end"
            # Domain short name
            svg += (
                f'<text x="{lx}" y="{ly - 2}" text-anchor="{anchor}" '
                f'font-family="{_font}" font-size="12" font-weight="600" fill="{d_spec["color"]}">'
                f'{d_spec["name"]}</text>'
            )

        # Center: overall score
        overall = wheel["overall_score_10"]
        oc = "#30D158" if overall >= 7 else "#FFD60A" if overall >= 5 else "#FF453A"
        svg += f'<circle cx="{_cx}" cy="{_cy}" r="28" fill="white" stroke="{A["separator"]}" stroke-width="1"/>'
        svg += f'<text x="{_cx}" y="{_cy - 2}" text-anchor="middle" font-family="{_font}" font-size="22" font-weight="700" fill="{oc}">{overall}</text>'
        svg += f'<text x="{_cx}" y="{_cy + 12}" text-anchor="middle" font-family="{_font}" font-size="8" fill="{A["label_tertiary"]}">/10</text>'

        svg += '</svg>'

        # Wrap in styled container
        radar_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_xl"]};padding:24px 16px;margin:8px 0">'
            f'{svg}'
            # Zone legend below
            f'<div style="display:flex;justify-content:center;gap:20px;font-size:11px;'
            f'color:{A["label_tertiary"]};margin-top:12px">'
            f'<span><span style="color:#FF453A">&#9679;</span> 0-4 Needs attention</span>'
            f'<span><span style="color:#FFD60A">&#9679;</span> 4-7 Developing</span>'
            f'<span><span style="color:#30D158">&#9679;</span> 7-10 Optimal</span></div>'
            f'</div>'
        )
        st.markdown(radar_html, unsafe_allow_html=True)

        # ── Today / Baseline Cards ─────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        tb_html = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">'

        # Overall
        tb_html += (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;'
            f'color:{A["label_tertiary"]};margin-bottom:4px">Overall</div>'
            f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
            f'color:{oc}">{overall}<span style="font-size:13px;color:{A["label_tertiary"]}">/10</span></div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:2px">'
            f'{wheel["data_points_used"]} metrics</div></div>'
        )

        # Today (readiness)
        t_score = wheel["overall_readiness_10"]
        t_color = "#30D158" if t_score >= 7 else "#FFD60A" if t_score >= 5 else "#FF453A"
        tb_html += (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;'
            f'color:{A["label_tertiary"]};margin-bottom:4px">Today</div>'
            f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
            f'color:{t_color}">{t_score}<span style="font-size:13px;color:{A["label_tertiary"]}">/10</span></div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:2px">'
            f'Last 1-3 days</div></div>'
        )

        # Baseline (resilience)
        b_score = wheel["overall_resilience_10"]
        b_color = "#30D158" if b_score >= 7 else "#FFD60A" if b_score >= 5 else "#FF453A"
        tb_html += (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;'
            f'color:{A["label_tertiary"]};margin-bottom:4px">Baseline</div>'
            f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
            f'color:{b_color}">{b_score}<span style="font-size:13px;color:{A["label_tertiary"]}">/10</span></div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:2px">'
            f'30-day average</div></div>'
        )
        tb_html += '</div>'
        st.markdown(tb_html, unsafe_allow_html=True)

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
                f'<div style="font-size:9px;color:{A["label_tertiary"]};text-transform:uppercase">Today</div>'
                f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
                f'color:{A["label_primary"]}">{domain["readiness_10"]}</div></div>'
                f'<div style="width:1px;background:{A["separator"]}"></div>'
                f'<div style="text-align:center">'
                f'<div style="font-size:9px;color:{A["label_tertiary"]};text-transform:uppercase">Baseline</div>'
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
