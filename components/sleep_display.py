"""Sleep display components — score circle, chronotype card, body clock."""

import streamlit as st
from components.custom_theme import APPLE

A = APPLE


def render_sleep_score_circle(score, label="Sleep Score"):
    """Render a circular sleep score gauge."""
    if score is None:
        st.caption("No sleep data yet. Log your first night to see your score.")
        return

    from services.sleep_service import get_sleep_score_zone
    zone = get_sleep_score_zone(score)
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


def render_chronotype_card(chronotype_data):
    """Render a chronotype result card."""
    if not chronotype_data:
        return

    data = chronotype_data.get("data", {})
    name = data.get("name", "Unknown")
    subtitle = data.get("subtitle", "")
    icon = data.get("icon", "")
    color = data.get("color", A["blue"])
    description = data.get("description", "")
    meq_score = chronotype_data.get("meq_score", "")

    traits_html = ""
    for trait in data.get("traits", []):
        traits_html += (
            f'<div style="font-size:12px;color:{A["label_secondary"]};'
            f'padding:2px 0">&#8226; {trait}</div>'
        )

    schedule_html = ""
    if data.get("ideal_bedtime"):
        schedule_html = (
            f'<div style="display:flex;gap:16px;margin-top:12px;flex-wrap:wrap">'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'&#128164; Bedtime: <span style="color:{A["label_secondary"]};font-weight:600">'
            f'{data["ideal_bedtime"]}</span></div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'&#127749; Wake: <span style="color:{A["label_secondary"]};font-weight:600">'
            f'{data["ideal_waketime"]}</span></div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'&#129504; Peak Focus: <span style="color:{A["label_secondary"]};font-weight:600">'
            f'{data["peak_focus"]}</span></div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'&#127939; Best Exercise: <span style="color:{A["label_secondary"]};font-weight:600">'
            f'{data["peak_exercise"]}</span></div>'
            f'</div>'
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
        f'{subtitle} &middot; MEQ Score: {meq_score}</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:13px;line-height:20px;color:{A["label_secondary"]};'
        f'margin-bottom:8px">{description}</div>'
        f'{traits_html}'
        f'{schedule_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_sleep_stat_cards(averages):
    """Render sleep average stat cards."""
    if not averages or not averages.get("log_count"):
        return

    def fmt_hours(mins):
        if mins is None:
            return "--"
        h = int(mins // 60)
        m = int(mins % 60)
        return f"{h}h {m}m"

    items = [
        {"icon": "&#128164;", "value": fmt_hours(averages["avg_duration"]),
         "label": "Avg Duration", "color": "#0A84FF"},
        {"icon": "&#128171;", "value": f"{averages['avg_efficiency']:.0f}%",
         "label": "Avg Efficiency", "color": "#30D158"},
        {"icon": "&#9202;", "value": f"{averages['avg_latency']:.0f}m",
         "label": "Avg Latency", "color": "#FFD60A"},
        {"icon": "&#11088;", "value": f"{averages['avg_score']:.0f}",
         "label": "Avg Score", "color": "#BF5AF2"},
    ]

    cards = ""
    for item in items:
        cards += (
            f'<div style="background:{A["glass_bg"]};border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center;flex:1;min-width:100px">'
            f'<div style="font-size:18px;margin-bottom:4px">{item["icon"]}</div>'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{item["color"]}">{item["value"]}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-top:2px">'
            f'{item["label"]}</div>'
            f'</div>'
        )
    strip_html = (
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">'
        f'{cards}'
        f'</div>'
    )
    st.markdown(strip_html, unsafe_allow_html=True)


def render_sleep_hygiene_tips(tips):
    """Render sleep hygiene recommendations."""
    if not tips:
        return

    tips_html = ""
    for tip in tips:
        tips_html += (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:8px">'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]};'
            f'margin-bottom:4px">{tip["tip"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'{tip["evidence"]}</div>'
            f'</div>'
        )
    st.markdown(tips_html, unsafe_allow_html=True)
