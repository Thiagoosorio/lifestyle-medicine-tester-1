"""Fasting display components — timer, zone progress, history cards."""

import streamlit as st
from components.custom_theme import APPLE

A = APPLE


def render_fasting_timer(session):
    """Render the active fasting timer with metabolic zone indicator."""
    if not session:
        return

    elapsed = session.get("elapsed_hours", 0)
    target = session.get("target_hours", 16)
    progress = session.get("progress_pct", 0)
    zone = session.get("current_zone", {})

    elapsed_h = int(elapsed)
    elapsed_m = int((elapsed - elapsed_h) * 60)
    remaining = max(0, target - elapsed)
    remaining_h = int(remaining)
    remaining_m = int((remaining - remaining_h) * 60)

    # Circular progress
    radius = 64
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - min(1, progress / 100))
    zone_color = zone.get("color", A["blue"])

    timer_html = (
        f'<div style="text-align:center;padding:20px">'
        f'<svg width="160" height="160" viewBox="0 0 160 160">'
        f'<circle cx="80" cy="80" r="{radius}" fill="none" stroke="{A["bg_tertiary"]}" stroke-width="8"/>'
        f'<circle cx="80" cy="80" r="{radius}" fill="none" stroke="{zone_color}" stroke-width="8" '
        f'stroke-linecap="round" stroke-dasharray="{circumference}" '
        f'stroke-dashoffset="{offset}" transform="rotate(-90 80 80)"/>'
        f'<text x="80" y="68" text-anchor="middle" fill="{A["label_primary"]}" '
        f'font-family="{A["font_display"]}" font-size="28" font-weight="700">'
        f'{elapsed_h}:{elapsed_m:02d}</text>'
        f'<text x="80" y="88" text-anchor="middle" fill="{A["label_tertiary"]}" '
        f'font-family="{A["font_text"]}" font-size="11">of {target}h target</text>'
        f'<text x="80" y="108" text-anchor="middle" fill="{zone_color}" '
        f'font-family="{A["font_text"]}" font-size="10" font-weight="600">'
        f'{remaining_h}:{remaining_m:02d} remaining</text>'
        f'</svg>'
        f'</div>'
    )
    st.markdown(timer_html, unsafe_allow_html=True)


def render_zone_indicator(session):
    """Render the current metabolic zone card."""
    if not session:
        return

    zone = session.get("current_zone", {})
    zone_color = zone.get("color", A["blue"])

    zone_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:3px solid {zone_color};border-radius:{A["radius_lg"]};'
        f'padding:16px;margin-bottom:12px">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
        f'<span style="font-size:24px">{zone.get("icon", "")}</span>'
        f'<div>'
        f'<div style="font-family:{A["font_display"]};font-size:16px;'
        f'font-weight:700;color:{zone_color}">{zone.get("name", "")}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
        f'{zone.get("start_hours", 0)}-{zone.get("end_hours", 0)} hours</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:13px;line-height:18px;color:{A["label_secondary"]}">'
        f'{zone.get("description", "")}</div>'
        f'</div>'
    )
    st.markdown(zone_html, unsafe_allow_html=True)

    if zone.get("causation_note"):
        note_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:12px">'
            f'<div style="font-size:11px;color:{A["orange"]}">'
            f'&#9888; {zone["causation_note"]}</div>'
            f'</div>'
        )
        st.markdown(note_html, unsafe_allow_html=True)


def render_zone_progress_bar(elapsed_hours):
    """Render a horizontal bar showing progress through all metabolic zones."""
    from config.fasting_data import FASTING_ZONES

    max_hours = 36  # max display range
    current_pct = min(100, (elapsed_hours / max_hours) * 100)

    zones_html = ""
    for zone in FASTING_ZONES:
        start_pct = (zone["start_hours"] / max_hours) * 100
        end_pct = min(100, (zone["end_hours"] / max_hours) * 100)
        width_pct = end_pct - start_pct
        is_active = zone["start_hours"] <= elapsed_hours < zone["end_hours"]
        opacity = "1.0" if is_active else "0.4"

        zones_html += (
            f'<div style="width:{width_pct}%;height:100%;background:{zone["color"]};'
            f'opacity:{opacity};display:inline-block"></div>'
        )

    # Zone labels
    labels_html = ""
    for zone in FASTING_ZONES:
        start_pct = (zone["start_hours"] / max_hours) * 100
        end_pct = min(100, (zone["end_hours"] / max_hours) * 100)
        center = (start_pct + end_pct) / 2
        labels_html += (
            f'<div style="position:absolute;left:{center}%;transform:translateX(-50%);'
            f'font-size:9px;color:{A["label_tertiary"]};white-space:nowrap">'
            f'{zone["icon"]}</div>'
        )

    bar_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:12px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'Metabolic Zones</div>'
        f'<div style="position:relative;height:16px;border-radius:8px;overflow:hidden;'
        f'display:flex">'
        f'{zones_html}'
        f'</div>'
        f'<div style="position:relative;height:16px;margin-top:4px">'
        f'{labels_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(bar_html, unsafe_allow_html=True)


def render_fasting_stat_cards(stats):
    """Render fasting statistics cards."""
    if not stats or stats.get("total_fasts", 0) == 0:
        return

    items = [
        {"label": "Total Fasts", "value": str(stats["total_fasts"]), "color": A["blue"]},
        {"label": "Avg Duration", "value": f"{stats['avg_hours']}h", "color": "#BF5AF2"},
        {"label": "Completion", "value": f"{stats['completion_rate']}%", "color": "#30D158"},
        {"label": "Longest", "value": f"{stats['longest_fast']}h", "color": "#FF9F0A"},
    ]

    cards = ""
    for item in items:
        cards += (
            f'<div style="background:{A["glass_bg"]};border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center;flex:1;min-width:80px">'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{item["color"]}">{item["value"]}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-top:2px">'
            f'{item["label"]}</div>'
            f'</div>'
        )
    html = (
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">'
        f'{cards}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
