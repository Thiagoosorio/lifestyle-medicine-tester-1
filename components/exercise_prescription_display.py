"""Display components for the exercise prescription / training program."""

import streamlit as st
from components.custom_theme import APPLE
from config.exercise_prescription_data import (
    VOLUME_LANDMARKS,
    RIR_GUIDE,
    DELOAD_PROTOCOL,
)
from config.exercise_library_data import MUSCLE_GROUPS, EQUIPMENT_TYPES

A = APPLE


def render_program_overview(program: dict):
    """Render a summary card for the generated program."""
    meso = program["mesocycle"]
    sched = program["schedule_info"]

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:20px;margin-bottom:16px">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
        f'<span style="font-size:28px">&#128170;</span>'
        f'<div>'
        f'<div style="font-family:{A["font_display"]};font-size:20px;'
        f'font-weight:700;color:{A["label_primary"]}">{meso["label"]}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
        f'{sched["label"]} &middot; {meso["weeks"]}-week mesocycle</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:20px;'
        f'margin-bottom:8px">{meso["note"]}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]};line-height:18px">'
        f'{sched["note"]}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_week_header(week_data: dict):
    """Render a week header with RIR and deload indicator."""
    rir_info = RIR_GUIDE.get(week_data["rir"], {})
    rir_color = rir_info.get("color", A["label_tertiary"])

    deload_badge = ""
    if week_data["is_deload"]:
        deload_badge = (
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:{A["green"]}15;'
            f'color:{A["green"]};margin-left:8px">DELOAD</span>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:14px 16px;margin-bottom:8px;'
        f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="font-family:{A["font_display"]};font-size:16px;'
        f'font-weight:700;color:{A["label_primary"]}">Week {week_data["week"]}</span>'
        f'{deload_badge}'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<div style="font-size:12px;color:{A["label_secondary"]}">'
        f'{week_data["label"]}</div>'
        f'<div style="font-size:11px;font-weight:600;padding:3px 10px;'
        f'border-radius:20px;background:{rir_color}15;color:{rir_color}">'
        f'RIR {week_data["rir"]}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_day_card(day_data: dict):
    """Render a training day with its exercises."""
    color = day_data["color"]

    # Header
    header_html = (
        f'<div style="background:{color}08;border:1px solid {color}20;'
        f'border-left:3px solid {color};border-radius:{A["radius_md"]};'
        f'padding:12px 16px;margin-bottom:4px">'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="font-size:20px">{day_data["icon"]}</span>'
        f'<div>'
        f'<div style="font-family:{A["font_display"]};font-size:15px;'
        f'font-weight:700;color:{color}">Day {day_data["day"]}: {day_data["label"]}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
        f'{day_data["subtitle"]}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # Exercises table
    rows_html = ""
    for ex in day_data["exercises"]:
        mg = MUSCLE_GROUPS.get(ex["muscle_group"], {})
        eq = EQUIPMENT_TYPES.get(ex["equipment"], {})
        rir_info = RIR_GUIDE.get(ex["rir"], {})
        rir_color = rir_info.get("color", A["label_tertiary"])
        type_color = A["blue"] if ex["type"] == "compound" else A["purple"]

        rows_html += (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_sm"]};padding:10px 14px;margin-bottom:3px;'
            f'display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            # Muscle icon
            f'<span style="font-size:16px;min-width:24px;text-align:center">'
            f'{mg.get("icon", "")}</span>'
            # Exercise name + type badge
            f'<div style="flex:1;min-width:160px">'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
            f'{ex["exercise_name"]}</div>'
            f'<div style="display:flex;gap:4px;margin-top:2px">'
            f'<span style="font-size:10px;padding:1px 6px;border-radius:10px;'
            f'background:{type_color}12;color:{type_color}">{ex["type"].title()}</span>'
            f'<span style="font-size:10px;padding:1px 6px;border-radius:10px;'
            f'background:{A["fill_tertiary"]};color:{A["label_tertiary"]}">'
            f'{eq.get("icon", "")} {eq.get("label", "")}</span>'
            f'</div>'
            f'</div>'
            # Sets × Reps
            f'<div style="min-width:80px;text-align:center">'
            f'<div style="font-size:14px;font-weight:700;color:{A["label_primary"]}">'
            f'{ex["sets"]} &times; {ex["reps"]}</div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]}">sets &times; reps</div>'
            f'</div>'
            # RIR badge
            f'<div style="min-width:50px;text-align:center">'
            f'<div style="font-size:12px;font-weight:600;padding:2px 8px;'
            f'border-radius:12px;background:{rir_color}15;color:{rir_color}">'
            f'RIR {ex["rir"]}</div>'
            f'</div>'
            f'</div>'
        )

    st.markdown(rows_html, unsafe_allow_html=True)


def render_volume_chart(volume: dict, level: str = "intermediate"):
    """Render a horizontal bar chart showing weekly volume per muscle group vs landmarks."""
    from services.exercise_prescription_service import get_volume_targets
    targets = get_volume_targets(level)

    bars_html = ""
    for mg_key in ["chest", "back", "shoulders", "biceps", "triceps", "legs", "glutes", "core"]:
        mg_info = MUSCLE_GROUPS.get(mg_key, {})
        actual = volume.get(mg_key, 0)
        t = targets.get(mg_key)
        if not t:
            continue

        max_val = max(t["mrv"], actual, 1)
        pct = min(actual / max_val * 100, 100)

        # Color based on where actual falls
        if actual < t["mev"]:
            bar_color = A["red"]
            zone_label = "Below MEV"
        elif actual <= t["mav_high"]:
            bar_color = A["green"]
            zone_label = "In MAV"
        elif actual <= t["mrv"]:
            bar_color = A["orange"]
            zone_label = "Near MRV"
        else:
            bar_color = A["red"]
            zone_label = "Over MRV"

        # MEV and MRV markers as percentage of max_val
        mev_pct = t["mev"] / max_val * 100
        mrv_pct = t["mrv"] / max_val * 100

        bars_html += (
            f'<div style="margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">'
            f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]}">'
            f'{mg_info.get("icon", "")} {mg_info.get("label", mg_key)}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'{actual} sets &middot; {zone_label}</div>'
            f'</div>'
            f'<div style="position:relative;height:16px;background:{A["bg_tertiary"]};'
            f'border-radius:8px;overflow:visible">'
            # Actual bar
            f'<div style="width:{pct}%;height:100%;background:{bar_color};'
            f'border-radius:8px;transition:width 0.3s"></div>'
            # MEV marker
            f'<div style="position:absolute;left:{mev_pct}%;top:-2px;bottom:-2px;'
            f'width:2px;background:{A["label_tertiary"]};opacity:0.5" '
            f'title="MEV: {t["mev"]}"></div>'
            # MRV marker
            f'<div style="position:absolute;left:{mrv_pct}%;top:-2px;bottom:-2px;'
            f'width:2px;background:{A["red"]};opacity:0.5" '
            f'title="MRV: {t["mrv"]}"></div>'
            f'</div>'
            f'</div>'
        )

    # Legend
    legend_html = (
        f'<div style="display:flex;gap:16px;margin-top:8px;flex-wrap:wrap">'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">'
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'background:{A["label_tertiary"]};border-radius:2px;margin-right:4px"></span>MEV</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">'
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'background:{A["red"]};border-radius:2px;margin-right:4px"></span>MRV</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">'
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'background:{A["green"]};border-radius:2px;margin-right:4px"></span>In MAV (optimal)</div>'
        f'</div>'
    )

    card_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:12px">'
        f'Weekly Volume per Muscle Group</div>'
        f'{bars_html}'
        f'{legend_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_rir_guide():
    """Render the RIR (Reps In Reserve) reference guide."""
    rows = ""
    for rir_val in [4, 3, 2, 1, 0]:
        info = RIR_GUIDE[rir_val]
        rows += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid {A["separator"]}">'
            f'<div style="min-width:50px;text-align:center">'
            f'<span style="font-size:13px;font-weight:700;padding:3px 10px;'
            f'border-radius:12px;background:{info["color"]}15;color:{info["color"]}">'
            f'RIR {rir_val}</span></div>'
            f'<div style="flex:1">'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
            f'{info["label"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">{info["desc"]}</div>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'RIR — Reps In Reserve Guide</div>'
        f'{rows}'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:8px;'
        f'line-height:16px">RIR = how many reps you <em>could</em> still do if pushed. '
        f'Compounds: stay at RIR 2-3. Isolations: can go to RIR 0-1. '
        f'(Helms et al., 2016 — PMID: 27834585)</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_volume_landmarks_table():
    """Render a reference table of RP volume landmarks."""
    rows = ""
    for key, vl in VOLUME_LANDMARKS.items():
        rows += (
            f'<tr>'
            f'<td style="font-size:12px;font-weight:600;color:{A["label_primary"]};padding:6px 8px">'
            f'{vl["label"]}</td>'
            f'<td style="font-size:12px;text-align:center;color:{A["label_tertiary"]};padding:6px">'
            f'{vl["mv"]}</td>'
            f'<td style="font-size:12px;text-align:center;color:{A["orange"]};padding:6px">'
            f'{vl["mev"]}</td>'
            f'<td style="font-size:12px;text-align:center;color:{A["green"]};font-weight:600;padding:6px">'
            f'{vl["mav_low"]}-{vl["mav_high"]}</td>'
            f'<td style="font-size:12px;text-align:center;color:{A["red"]};padding:6px">'
            f'{vl["mrv"]}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;overflow-x:auto">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'RP Volume Landmarks — Sets per Muscle Group per Week</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:2px solid {A["separator"]}">'
        f'<th style="text-align:left;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px 8px">Muscle</th>'
        f'<th style="text-align:center;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px">MV</th>'
        f'<th style="text-align:center;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px">MEV</th>'
        f'<th style="text-align:center;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px">MAV</th>'
        f'<th style="text-align:center;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px">MRV</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:8px;line-height:14px">'
        f'MV = Maintenance &middot; MEV = Min Effective &middot; '
        f'MAV = Max Adaptive (sweet spot) &middot; MRV = Max Recoverable<br>'
        f'Source: Israetel, Hoffmann &amp; Smith (2021); Schoenfeld et al. (2017, PMID: 28032998)</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_mesocycle_timeline(program: dict):
    """Render a horizontal mesocycle progression timeline."""
    weeks = program["weeks"]

    cells = ""
    for w in weeks:
        rir_info = RIR_GUIDE.get(w["rir"], {})
        rir_color = rir_info.get("color", A["label_tertiary"])
        bg = f"{A['green']}10" if w["is_deload"] else f"{rir_color}08"
        border_color = A["green"] if w["is_deload"] else rir_color

        cells += (
            f'<div style="flex:1;min-width:100px;background:{bg};'
            f'border:1px solid {border_color}30;border-top:3px solid {border_color};'
            f'border-radius:{A["radius_sm"]};padding:10px;text-align:center">'
            f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]}">'
            f'Week {w["week"]}</div>'
            f'<div style="font-size:11px;color:{A["label_secondary"]};margin:4px 0">'
            f'{w["label"]}</div>'
            f'<div style="font-size:11px;font-weight:600;color:{rir_color}">'
            f'RIR {w["rir"]}</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:10px">'
        f'Mesocycle Progression</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap">'
        f'{cells}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
