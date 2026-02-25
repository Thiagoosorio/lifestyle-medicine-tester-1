"""Biomarker display components — range bars, status badges, score gauge."""

import streamlit as st
from components.custom_theme import APPLE

A = APPLE


def render_biomarker_range_bar(result, definition=None):
    """Render a horizontal range bar showing value position against standard/optimal ranges."""
    if definition is None:
        definition = result

    value = result.get("value")
    if value is None:
        return

    name = definition.get("name", "")
    unit = definition.get("unit", "")
    std_low = definition.get("standard_low")
    std_high = definition.get("standard_high")
    opt_low = definition.get("optimal_low")
    opt_high = definition.get("optimal_high")
    crit_low = definition.get("critical_low")
    crit_high = definition.get("critical_high")

    from services.biomarker_service import classify_result, get_classification_display
    classification = classify_result(value, definition)
    cls_display = get_classification_display(classification)

    # Determine bar range (min to max for display)
    all_vals = [v for v in [crit_low, std_low, opt_low, opt_high, std_high, crit_high, value] if v is not None]
    if not all_vals:
        return
    bar_min = min(all_vals) * 0.7
    bar_max = max(all_vals) * 1.3
    if bar_min == bar_max:
        bar_max = bar_min + 1
    bar_range = bar_max - bar_min

    def pct(v):
        if v is None:
            return None
        return max(0, min(100, ((v - bar_min) / bar_range) * 100))

    val_pct = pct(value)

    # Build zone backgrounds
    zones_html = ""
    # Optimal zone (green)
    if opt_low is not None and opt_high is not None:
        left = pct(opt_low)
        width = pct(opt_high) - left
        zones_html += (
            f'<div style="position:absolute;left:{left}%;width:{width}%;'
            f'height:100%;background:#30D15830;border-radius:4px"></div>'
        )
    elif opt_high is not None:
        width = pct(opt_high)
        zones_html += (
            f'<div style="position:absolute;left:0;width:{width}%;'
            f'height:100%;background:#30D15830;border-radius:4px"></div>'
        )
    elif opt_low is not None:
        left = pct(opt_low)
        zones_html += (
            f'<div style="position:absolute;left:{left}%;right:0;'
            f'height:100%;background:#30D15830;border-radius:4px"></div>'
        )

    # Standard zone (subtle blue)
    if std_low is not None and std_high is not None:
        left = pct(std_low)
        width = pct(std_high) - left
        zones_html += (
            f'<div style="position:absolute;left:{left}%;width:{width}%;'
            f'height:100%;background:#64D2FF15;border-radius:4px"></div>'
        )

    # Value marker
    marker_html = (
        f'<div style="position:absolute;left:{val_pct}%;top:-2px;'
        f'width:3px;height:calc(100% + 4px);background:{cls_display["color"]};'
        f'border-radius:2px;transform:translateX(-50%)"></div>'
    )

    # Value label below
    val_label_html = (
        f'<div style="position:absolute;left:{val_pct}%;top:18px;'
        f'transform:translateX(-50%);font-size:11px;font-weight:700;'
        f'color:{cls_display["color"]}">{value}</div>'
    )

    # Build reference range text
    range_parts = []
    if std_low is not None and std_high is not None:
        range_parts.append(f"Ref: {std_low}-{std_high} {unit}")
    elif std_high is not None:
        range_parts.append(f"Ref: &lt;{std_high} {unit}")
    elif std_low is not None:
        range_parts.append(f"Ref: &gt;{std_low} {unit}")
    if opt_low is not None and opt_high is not None:
        range_parts.append(f"Optimal: {opt_low}-{opt_high}")
    range_text = " &middot; ".join(range_parts)

    bar_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:14px 16px 32px 16px;margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
        f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
        f'color:{A["label_primary"]}">{name}</div>'
        f'<div style="display:flex;align-items:center;gap:6px">'
        f'<span style="font-size:14px;font-weight:700;color:{cls_display["color"]}">'
        f'{value} {unit}</span>'
        f'<span style="font-size:10px;font-weight:600;padding:2px 6px;'
        f'border-radius:4px;background:{cls_display["color"]}20;'
        f'color:{cls_display["color"]}">{cls_display["label"]}</span>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'{range_text}</div>'
        f'<div style="position:relative;height:14px;background:{A["bg_tertiary"]};'
        f'border-radius:7px;overflow:visible">'
        f'{zones_html}'
        f'{marker_html}'
        f'{val_label_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(bar_html, unsafe_allow_html=True)


def render_biomarker_score_gauge(score, label="Biomarker Score"):
    """Render a circular score gauge for the composite biomarker score."""
    if score is None:
        st.caption("No biomarker data yet. Log your first lab results to see your score.")
        return

    if score >= 85:
        color = "#30D158"
        zone = "Excellent"
    elif score >= 70:
        color = "#64D2FF"
        zone = "Good"
    elif score >= 50:
        color = "#FFD60A"
        zone = "Fair"
    else:
        color = "#FF453A"
        zone = "Needs Attention"

    # SVG circular gauge
    radius = 54
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - score / 100)

    gauge_html = (
        f'<div style="text-align:center;padding:16px">'
        f'<svg width="140" height="140" viewBox="0 0 140 140">'
        f'<circle cx="70" cy="70" r="{radius}" fill="none" stroke="{A["bg_tertiary"]}" stroke-width="10"/>'
        f'<circle cx="70" cy="70" r="{radius}" fill="none" stroke="{color}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{circumference}" '
        f'stroke-dashoffset="{offset}" transform="rotate(-90 70 70)"/>'
        f'<text x="70" y="64" text-anchor="middle" fill="{A["label_primary"]}" '
        f'font-family="{A["font_display"]}" font-size="28" font-weight="700">{score}</text>'
        f'<text x="70" y="84" text-anchor="middle" fill="{A["label_tertiary"]}" '
        f'font-family="{A["font_text"]}" font-size="11" font-weight="600">{zone}</text>'
        f'</svg>'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-top:4px">{label}</div>'
        f'</div>'
    )
    st.markdown(gauge_html, unsafe_allow_html=True)


def render_biomarker_summary_strip(summary):
    """Render a summary strip of biomarker classification counts."""
    items = [
        ("Optimal", summary.get("optimal", 0), "#30D158"),
        ("Normal", summary.get("normal", 0), "#64D2FF"),
        ("Borderline", summary.get("borderline", 0), "#FFD60A"),
        ("Abnormal", summary.get("abnormal", 0), "#FF453A"),
        ("Critical", summary.get("critical", 0), "#FF453A"),
    ]
    cards = ""
    for label, count, color in items:
        cards += (
            f'<div style="text-align:center;min-width:60px">'
            f'<div style="font-family:{A["font_display"]};font-size:22px;'
            f'font-weight:700;color:{color}">{count}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">{label}</div>'
            f'</div>'
        )
    strip_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:8px">'
        f'{cards}'
        f'</div>'
        f'</div>'
    )
    st.markdown(strip_html, unsafe_allow_html=True)


def render_category_header(category_key, category_info):
    """Render a category section header with icon."""
    header_html = (
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'margin-top:20px;margin-bottom:12px">'
        f'<span style="font-size:18px">{category_info.get("icon", "")}</span>'
        f'<span style="font-family:{A["font_display"]};font-size:17px;'
        f'font-weight:600;color:{A["label_primary"]}">'
        f'{category_info.get("label", category_key)}</span>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
