"""Exercise display components — score gauge, weekly progress, workout cards."""

import streamlit as st
from components.custom_theme import APPLE
from config.exercise_data import (
    EXERCISE_TYPES,
    INTENSITY_LEVELS,
    WEEKLY_TARGETS,
    EXERCISE_CATEGORIES,
)

A = APPLE


def render_exercise_score_gauge(score, label="Exercise Score"):
    """Render a circular score gauge for the weekly exercise score."""
    if score is None:
        st.caption("No exercise data this week. Log your first workout to see your score.")
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
        zone = "Needs Work"

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


def render_weekly_progress_bar(stats):
    """Render horizontal progress bars for aerobic and strength targets."""
    target_aerobic = WEEKLY_TARGETS["aerobic_moderate_min"]
    target_strength = WEEKLY_TARGETS["strength_days"]
    aeq = stats.get("aerobic_equivalent_min", 0)
    strength_days = stats.get("strength_days", 0)

    aerobic_pct = min(100, round(aeq / target_aerobic * 100)) if target_aerobic > 0 else 0
    strength_pct = min(100, round(strength_days / target_strength * 100)) if target_strength > 0 else 0

    # Aerobic color
    if aerobic_pct >= 100:
        aero_color = "#30D158"
    elif aerobic_pct >= 66:
        aero_color = "#64D2FF"
    elif aerobic_pct >= 33:
        aero_color = "#FFD60A"
    else:
        aero_color = "#FF453A"

    # Strength color
    str_color = "#30D158" if strength_pct >= 100 else ("#FFD60A" if strength_pct >= 50 else "#FF453A")

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
        # Aerobic
        f'<div style="margin-bottom:14px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">&#10084; Aerobic</div>'
        f'<div style="font-size:13px;font-weight:700;color:{aero_color}">{aeq}/{target_aerobic} min</div>'
        f'</div>'
        f'<div style="height:10px;background:{A["bg_tertiary"]};border-radius:5px;overflow:hidden">'
        f'<div style="height:100%;width:{aerobic_pct}%;background:{aero_color};'
        f'border-radius:5px;transition:width 0.3s"></div>'
        f'</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:3px">'
        f'Moderate + 2&times;Vigorous min (WHO guideline: 150 min/wk)</div>'
        f'</div>'
        # Strength
        f'<div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">&#127947; Strength</div>'
        f'<div style="font-size:13px;font-weight:700;color:{str_color}">'
        f'{strength_days}/{target_strength} days</div>'
        f'</div>'
        f'<div style="height:10px;background:{A["bg_tertiary"]};border-radius:5px;overflow:hidden">'
        f'<div style="height:100%;width:{strength_pct}%;background:{str_color};'
        f'border-radius:5px;transition:width 0.3s"></div>'
        f'</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:3px">'
        f'Strength training days (WHO guideline: 2+ days/wk)</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_exercise_summary_strip(stats):
    """Render a summary strip of exercise stats for the week."""
    items = [
        ("Sessions", stats.get("session_count", 0), "#0A84FF"),
        ("Cardio", f"{stats.get('cardio_min', 0)}m", "#FF453A"),
        ("Strength", f"{stats.get('strength_min', 0)}m", "#0A84FF"),
        ("Flex", f"{stats.get('flexibility_min', 0)}m", "#BF5AF2"),
        ("Total", f"{stats.get('total_min', 0)}m", A["label_primary"]),
    ]
    cards = ""
    for label, value, color in items:
        cards += (
            f'<div style="text-align:center;min-width:55px">'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{color}">{value}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">{label}</div>'
            f'</div>'
        )
    strip_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
        f'<div style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:8px">'
        f'{cards}'
        f'</div>'
        f'</div>'
    )
    st.markdown(strip_html, unsafe_allow_html=True)


def render_exercise_card(exercise):
    """Render a single exercise/workout card."""
    ex_type = exercise.get("exercise_type", "other")
    type_info = EXERCISE_TYPES.get(ex_type, EXERCISE_TYPES["other"])
    intensity = exercise.get("intensity", "moderate")
    int_info = INTENSITY_LEVELS.get(intensity, INTENSITY_LEVELS["moderate"])

    duration = exercise.get("duration_min", 0)
    distance = exercise.get("distance_km")
    calories = exercise.get("calories")
    avg_hr = exercise.get("avg_hr")
    source = exercise.get("source", "manual")
    notes = exercise.get("notes", "")

    # Build detail chips
    details = []
    if distance:
        details.append(f"{distance:.1f} km")
    if calories:
        details.append(f"{calories} kcal")
    if avg_hr:
        details.append(f"&#10084; {avg_hr} bpm")
    if exercise.get("rpe"):
        details.append(f"RPE {exercise['rpe']}/10")

    details_html = ""
    if details:
        chips = " &nbsp;&middot;&nbsp; ".join(details)
        details_html = (
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:4px">'
            f'{chips}</div>'
        )

    source_badge = ""
    if source == "strava":
        source_badge = (
            f'<span style="font-size:9px;font-weight:600;padding:1px 5px;'
            f'border-radius:3px;background:#FC4C0220;color:#FC4C02;'
            f'margin-left:6px">STRAVA</span>'
        )
    elif source == "garmin":
        source_badge = (
            f'<span style="font-size:9px;font-weight:600;padding:1px 5px;'
            f'border-radius:3px;background:#007DC320;color:#007DC3;'
            f'margin-left:6px">GARMIN</span>'
        )

    notes_html = ""
    if notes:
        notes_html = (
            f'<div style="font-size:11px;color:{A["label_tertiary"]};'
            f'margin-top:4px;font-style:italic">{notes}</div>'
        )

    card_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:3px solid {int_info["color"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="font-size:18px">{type_info["icon"]}</span>'
        f'<div>'
        f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
        f'color:{A["label_primary"]}">{type_info["label"]}{source_badge}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
        f'{exercise.get("exercise_date", "")}</div>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:16px;font-weight:700;color:{A["label_primary"]}">'
        f'{duration} min</div>'
        f'<span style="font-size:10px;font-weight:600;padding:2px 6px;'
        f'border-radius:4px;background:{int_info["color"]}20;'
        f'color:{int_info["color"]}">{int_info["label"]}</span>'
        f'</div>'
        f'</div>'
        f'{details_html}'
        f'{notes_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
