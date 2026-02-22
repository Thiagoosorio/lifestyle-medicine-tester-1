"""Diet assessment display components — HEI score circle, diet pattern card, component bars."""

import streamlit as st
from components.custom_theme import APPLE

A = APPLE


def render_hei_score_circle(score, label="Diet Quality Score"):
    """Render an HEI score circle gauge (same SVG technique as sleep score)."""
    if score is None:
        st.caption("No diet assessment yet. Take the quiz to see your score.")
        return

    from services.diet_service import get_hei_score_zone
    zone = get_hei_score_zone(score)
    color = zone["color"]

    radius = 54
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - score / 100)

    html = (
        f'<div style="text-align:center;padding:16px">'
        f'<svg width="140" height="140" viewBox="0 0 140 140">'
        f'<circle cx="70" cy="70" r="{radius}" fill="none" stroke="{A["bg_tertiary"]}" stroke-width="10"/>'
        f'<circle cx="70" cy="70" r="{radius}" fill="none" stroke="{color}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{circumference}" '
        f'stroke-dashoffset="{offset}" transform="rotate(-90 70 70)"/>'
        f'<text x="70" y="64" text-anchor="middle" fill="{A["label_primary"]}" '
        f'font-family="{A["font_display"]}" font-size="28" font-weight="700">{score}</text>'
        f'<text x="70" y="84" text-anchor="middle" fill="{color}" '
        f'font-family="{A["font_text"]}" font-size="11" font-weight="600">{zone["label"]}</text>'
        f'</svg>'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-top:4px">{label}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-top:4px">'
        f'{zone["message"]}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_diet_pattern_card(assessment):
    """Render a diet pattern result card (similar to chronotype card)."""
    if not assessment:
        return

    data = assessment.get("data", {})
    name = data.get("name", "Unknown")
    subtitle = data.get("subtitle", "")
    icon = data.get("icon", "")
    color = data.get("color", A["blue"])
    description = data.get("description", "")
    hei_score = assessment.get("hei_score", "")

    strengths_html = ""
    for s in data.get("strengths", []):
        strengths_html += (
            f'<div style="font-size:12px;color:{A["label_secondary"]};'
            f'padding:2px 0">&#9989; {s}</div>'
        )

    improvements_html = ""
    for imp in data.get("improvements", []):
        improvements_html += (
            f'<div style="font-size:12px;color:{A["label_tertiary"]};'
            f'padding:2px 0">&#128161; {imp}</div>'
        )

    evidence_html = ""
    evidence = data.get("evidence", "")
    if evidence:
        evidence_html = (
            f'<div style="font-size:11px;color:{A["label_quaternary"]};'
            f'margin-top:8px;font-style:italic">{evidence}</div>'
        )

    card_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:3px solid {color};border-radius:{A["radius_lg"]};'
        f'padding:20px;margin-bottom:16px">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">'
        f'<span style="font-size:32px">{icon}</span>'
        f'<div>'
        f'<div style="font-family:{A["font_display"]};font-size:20px;'
        f'font-weight:700;color:{color}">{name}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
        f'{subtitle} &middot; HEI Score: {hei_score}</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:13px;line-height:20px;color:{A["label_secondary"]};'
        f'margin-bottom:10px">{description}</div>'
        f'<div style="margin-bottom:6px">'
        f'<div style="font-size:11px;font-weight:600;color:{A["label_primary"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">Strengths</div>'
        f'{strengths_html}'
        f'</div>'
        f'<div>'
        f'<div style="font-size:11px;font-weight:600;color:{A["label_primary"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">Areas to Improve</div>'
        f'{improvements_html}'
        f'</div>'
        f'{evidence_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_hei_component_bars(component_scores):
    """Render horizontal bars for each HEI-2020 component."""
    if not component_scores:
        return

    from config.diet_data import HEI_COMPONENTS

    bars_html = ""
    for key, info in HEI_COMPONENTS.items():
        score = component_scores.get(key, 0)
        max_score = info["max_score"]
        pct = (score / max_score * 100) if max_score > 0 else 0
        color = info["color"]
        comp_type = "&#9650;" if info["type"] == "adequacy" else "&#9660;"

        bars_html += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<div style="font-size:11px;color:{A["label_secondary"]};min-width:150px;text-align:right">'
            f'{comp_type} {info["label"]}</div>'
            f'<div style="flex:1;background:{A["fill_tertiary"]};border-radius:9999px;height:6px;overflow:hidden">'
            f'<div style="background:{color};width:{pct:.0f}%;height:100%;border-radius:9999px"></div>'
            f'</div>'
            f'<div style="font-size:11px;font-weight:600;color:{color};min-width:40px">'
            f'{score}/{max_score}</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]};'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">'
        f'HEI-2020 Components (&#9650; Adequacy &middot; &#9660; Moderation)</div>'
        f'{bars_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
