"""Display components for the exercise prescription / training program."""

import streamlit as st
from components.custom_theme import APPLE
from config.exercise_prescription_data import (
    VOLUME_LANDMARKS,
    PPL_SPLIT,
    RIR_GUIDE,
    DELOAD_PROTOCOL,
)
from config.exercise_library_data import MUSCLE_GROUPS, EQUIPMENT_TYPES

A = APPLE


def render_key_terms_guide():
    """Render a compact reference card explaining all key terms and colors."""
    html = (
        f'<div style="background:{A["bg_secondary"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:10px">&#128218; Quick Guide — Key Terms &amp; Colors</div>'
        # Terms grid
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-bottom:12px">'
        # RIR
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["label_primary"]}">RIR</span>'
        f'<span style="color:{A["label_secondary"]}"> = Reps In Reserve — '
        f'how many more reps you <em>could</em> do before failure. '
        f'Lower RIR = harder effort.</span></div>'
        # Sets
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["label_primary"]}">Sets &times; Reps</span>'
        f'<span style="color:{A["label_secondary"]}"> = e.g. "4 &times; 6-10" means '
        f'do 4 sets of 6 to 10 repetitions each.</span></div>'
        # Compound
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["blue"]}">Compound</span>'
        f'<span style="color:{A["label_secondary"]}"> = multi-joint exercise (e.g. squat, bench press) — '
        f'works several muscles at once.</span></div>'
        # Isolation
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["purple"]}">Isolation</span>'
        f'<span style="color:{A["label_secondary"]}"> = single-joint exercise (e.g. curl, fly) — '
        f'targets one specific muscle.</span></div>'
        # Mesocycle
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["label_primary"]}">Mesocycle</span>'
        f'<span style="color:{A["label_secondary"]}"> = a training block (4-6 weeks) that starts easy, '
        f'gets progressively harder, then deloads.</span></div>'
        # Deload
        f'<div style="font-size:12px;line-height:16px">'
        f'<span style="font-weight:700;color:{A["green"]}">Deload</span>'
        f'<span style="color:{A["label_secondary"]}"> = a recovery week with reduced volume (fewer sets) '
        f'to let your body recover and adapt.</span></div>'
        f'</div>'
        # Color meanings
        f'<div style="font-size:12px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:6px">Volume Bar Colors</div>'
        f'<div style="display:flex;gap:16px;flex-wrap:wrap">'
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["green"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Optimal zone — good stimulus for growth</span></div>'
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["orange"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Near max recoverable — high fatigue risk</span></div>'
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["red"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Too low or too high — adjust volume</span></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


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
        f'{sched["label"]} &middot; {meso["weeks"]}-week mesocycle '
        f'(training block)</div>'
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

    rir_desc = rir_info.get("desc", "")

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:14px 16px;margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;'
        f'margin-bottom:4px">'
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
        f'RIR {week_data["rir"]} ({rir_info.get("label", "")})</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:14px">'
        f'Target effort: {rir_desc} Stop each set with ~{week_data["rir"]} reps still possible.</div>'
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
        rir_label = rir_info.get("label", "")
        type_color = A["blue"] if ex["type"] == "compound" else A["purple"]
        type_hint = "Multi-joint" if ex["type"] == "compound" else "Single-joint"

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
            f'background:{type_color}12;color:{type_color}">'
            f'{ex["type"].title()} ({type_hint})</span>'
            f'<span style="font-size:10px;padding:1px 6px;border-radius:10px;'
            f'background:{A["fill_tertiary"]};color:{A["label_tertiary"]}">'
            f'{eq.get("icon", "")} {eq.get("label", "")}</span>'
            f'</div>'
            f'</div>'
            # Sets × Reps
            f'<div style="min-width:90px;text-align:center">'
            f'<div style="font-size:14px;font-weight:700;color:{A["label_primary"]}">'
            f'{ex["sets"]} sets &times; {ex["reps"]}</div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]}">reps per set</div>'
            f'</div>'
            # RIR badge with explanation
            f'<div style="min-width:70px;text-align:center">'
            f'<div style="font-size:11px;font-weight:600;padding:2px 8px;'
            f'border-radius:12px;background:{rir_color}15;color:{rir_color}">'
            f'{rir_label}</div>'
            f'<div style="font-size:9px;color:{A["label_tertiary"]};margin-top:1px">'
            f'{ex["rir"]} reps left</div>'
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

        # Color based on where actual falls relative to volume landmarks
        if actual < t["mev"]:
            bar_color = A["red"]
            zone_label = "Below minimum for growth"
        elif actual <= t["mav_high"]:
            bar_color = A["green"]
            zone_label = "Optimal growth zone"
        elif actual <= t["mrv"]:
            bar_color = A["orange"]
            zone_label = "Near max — fatigue risk"
        else:
            bar_color = A["red"]
            zone_label = "Over max — reduce volume"

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

    # Legend — expanded with full names
    legend_html = (
        f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid {A["separator"]}">'
        f'<div style="font-size:11px;font-weight:600;color:{A["label_primary"]};margin-bottom:6px">'
        f'What the markers mean:</div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:6px">'
        # MEV marker
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:2px;height:12px;'
        f'background:{A["label_tertiary"]}"></span>'
        f'<span style="color:{A["label_secondary"]}">MEV (Minimum Effective Volume) '
        f'— below this line, not enough stimulus for growth</span></div>'
        # MRV marker
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:2px;height:12px;'
        f'background:{A["red"]}"></span>'
        f'<span style="color:{A["label_secondary"]}">MRV (Maximum Recoverable Volume) '
        f'— beyond this line, too much to recover from</span></div>'
        f'</div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap">'
        # Green bar
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["green"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Green = optimal zone for muscle growth</span></div>'
        # Orange bar
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["orange"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Orange = high volume, watch for fatigue</span></div>'
        # Red bar
        f'<div style="font-size:11px;display:flex;align-items:center;gap:4px">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{A["red"]};border-radius:3px"></span>'
        f'<span style="color:{A["label_secondary"]}">Red = too low or too high, needs adjusting</span></div>'
        f'</div>'
        f'</div>'
    )

    card_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:4px">'
        f'Weekly Volume per Muscle Group</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-bottom:12px">'
        f'Total hard sets per muscle this week. Aim to keep bars in the green zone.</div>'
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
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:4px">'
        f'Volume Landmarks — Sets per Muscle Group per Week</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-bottom:10px;line-height:16px">'
        f'How many hard sets to do per week for each muscle. Train within the '
        f'green MAV range for best results.</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:2px solid {A["separator"]}">'
        f'<th style="text-align:left;font-size:11px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px 8px">Muscle</th>'
        f'<th style="text-align:center;font-size:10px;font-weight:600;color:{A["label_tertiary"]};'
        f'padding:6px"><div>MV</div><div style="font-weight:400;font-size:9px">Maintenance</div></th>'
        f'<th style="text-align:center;font-size:10px;font-weight:600;color:{A["orange"]};'
        f'padding:6px"><div>MEV</div><div style="font-weight:400;font-size:9px">Min for Growth</div></th>'
        f'<th style="text-align:center;font-size:10px;font-weight:600;color:{A["green"]};'
        f'padding:6px"><div>MAV</div><div style="font-weight:400;font-size:9px">Optimal Range</div></th>'
        f'<th style="text-align:center;font-size:10px;font-weight:600;color:{A["red"]};'
        f'padding:6px"><div>MRV</div><div style="font-weight:400;font-size:9px">Max Recoverable</div></th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-top:10px;line-height:16px">'
        f'<strong>MV</strong> = Maintenance Volume (keep muscle, no growth) &middot; '
        f'<strong>MEV</strong> = Minimum Effective Volume (minimum to start growing) &middot; '
        f'<strong>MAV</strong> = Maximum Adaptive Volume (sweet spot for most people) &middot; '
        f'<strong>MRV</strong> = Maximum Recoverable Volume (beyond this = overtraining)<br>'
        f'Source: Renaissance Periodization (Israetel, Hoffmann &amp; Smith, 2021); '
        f'Schoenfeld et al. (2017, PMID: 28032998)</div>'
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

        rir_label = rir_info.get("label", "")
        cells += (
            f'<div style="flex:1;min-width:110px;background:{bg};'
            f'border:1px solid {border_color}30;border-top:3px solid {border_color};'
            f'border-radius:{A["radius_sm"]};padding:10px;text-align:center">'
            f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]}">'
            f'Week {w["week"]}</div>'
            f'<div style="font-size:11px;color:{A["label_secondary"]};margin:4px 0">'
            f'{w["label"]}</div>'
            f'<div style="font-size:10px;font-weight:600;color:{rir_color}">'
            f'{rir_label} effort</div>'
            f'<div style="font-size:9px;color:{A["label_tertiary"]};margin-top:2px">'
            f'Stop {w["rir"]} reps before failure</div>'
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


# ── Workout Logging Display ────────────────────────────────────────────────

def render_recent_workouts(workouts: list[dict]):
    """Render a list of recent workout sessions."""
    if not workouts:
        st.caption("No workouts logged yet. Use the **Log Workout** tab to start tracking.")
        return

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:10px">'
        f'Recent Workouts</div>'
    )

    split_colors = {
        "push": "#D93025",
        "pull": "#1A73E8",
        "legs": "#1E8E3E",
    }
    split_icons = {
        "push": "&#128170;",
        "pull": "&#129470;",
        "legs": "&#129461;",
    }

    for w in workouts:
        split = w.get("split_type", "push")
        color = split_colors.get(split, A["label_tertiary"])
        icon = split_icons.get(split, "&#127947;")
        avg_rpe = w.get("avg_rpe")
        rpe_str = f"RPE {avg_rpe:.1f}" if avg_rpe else "—"
        total_sets = w.get("total_sets", 0)
        exercises = w.get("exercises", 0)
        total_reps = w.get("total_reps", 0) or 0
        date_str = w.get("workout_date", "")

        html += (
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:10px;border-bottom:1px solid {A["separator"]}30">'
            f'<div style="font-size:20px">{icon}</div>'
            f'<div style="flex:1">'
            f'<div style="font-size:13px;font-weight:600;color:{color}">'
            f'{split.capitalize()} Day — Week {w.get("week_number", "?")}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">{date_str}</div>'
            f'</div>'
            f'<div style="text-align:right">'
            f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]}">'
            f'{total_sets} sets &middot; {int(total_reps)} reps</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'{exercises} exercises &middot; {rpe_str}</div>'
            f'</div>'
            f'</div>'
        )

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_exercise_progress(history: list[dict], exercise_name: str):
    """Render weight progression chart for a specific exercise."""
    if not history:
        return

    # Group by date, show latest weight per session
    sessions = {}
    for h in history:
        d = h["workout_date"]
        if d not in sessions or (h.get("weight_kg") and h["weight_kg"] > sessions[d].get("weight_kg", 0)):
            sessions[d] = h

    if not sessions:
        return

    dates = sorted(sessions.keys())
    max_weight = max(sessions[d].get("weight_kg", 0) for d in dates) or 1

    bars = ""
    for d in dates[-8:]:  # Last 8 sessions
        w = sessions[d].get("weight_kg", 0) or 0
        reps = sessions[d].get("actual_reps", 0) or 0
        pct = (w / max_weight * 100) if max_weight > 0 else 0
        bars += (
            f'<div style="display:flex;align-items:end;gap:2px;flex-direction:column;'
            f'min-width:40px;text-align:center">'
            f'<div style="font-size:10px;font-weight:600;color:{A["label_primary"]}">'
            f'{w:.0f}kg</div>'
            f'<div style="width:28px;height:{max(pct * 0.8, 4):.0f}px;'
            f'background:{A["blue"]};border-radius:4px 4px 0 0"></div>'
            f'<div style="font-size:9px;color:{A["label_tertiary"]}">'
            f'{d[-5:]}</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]};'
        f'margin-bottom:8px">{exercise_name} — Weight Progression</div>'
        f'<div style="display:flex;gap:6px;align-items:end;min-height:80px">'
        f'{bars}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_workout_log_form(day_data: dict, week_number: int, existing_log: list[dict] | None = None,
                            last_weights: dict | None = None):
    """Render the workout logging form for a specific training day.

    Returns list of set dicts if form is submitted, else None.
    """
    split = day_data.get("split", "push")
    split_colors = {"push": "#D93025", "pull": "#1A73E8", "legs": "#1E8E3E"}
    color = split_colors.get(split, A["label_tertiary"])

    # Build existing log lookup: {exercise_id: {set_number: row}}
    log_lookup: dict[str, dict[int, dict]] = {}
    if existing_log:
        for row in existing_log:
            eid = row.get("exercise_id", "")
            sn = row.get("set_number", 1)
            log_lookup.setdefault(eid, {})[sn] = row

    last_weights = last_weights or {}

    header_html = (
        f'<div style="background:{color}08;border:1px solid {color}25;'
        f'border-radius:{A["radius_lg"]};padding:14px;margin-bottom:16px">'
        f'<div style="font-size:15px;font-weight:700;color:{color}">'
        f'{day_data.get("icon", "")} {day_data.get("label", split.capitalize())} — '
        f'Week {week_number}</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};margin-top:4px">'
        f'Enter weight, reps completed, and RPE for each set. '
        f'Pre-filled with your last recorded weight where available.</div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    all_sets = []

    for ex in day_data.get("exercises", []):
        ex_id = ex["exercise_id"]
        ex_name = ex["exercise_name"]
        num_sets = ex["sets"]
        prescribed_reps = ex["reps"]
        ex_log = log_lookup.get(ex_id, {})
        default_weight = last_weights.get(ex_id, 0.0) or 0.0

        # Exercise type badge
        ex_type = ex.get("type", "compound")
        type_label = "Compound (Multi-joint)" if ex_type == "compound" else "Isolation (Single-joint)"
        type_color = A["blue"] if ex_type == "compound" else A["purple"]

        ex_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
            f'<div style="font-size:14px;font-weight:600;color:{A["label_primary"]}">'
            f'{ex_name}</div>'
            f'<div style="font-size:10px;font-weight:600;color:{type_color};'
            f'background:{type_color}12;padding:2px 6px;border-radius:4px">'
            f'{type_label}</div>'
            f'</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-bottom:6px">'
            f'{num_sets} sets &times; {prescribed_reps} reps &middot; '
            f'Target: RIR {ex.get("rir", 2)}</div>'
            f'</div>'
        )
        st.markdown(ex_html, unsafe_allow_html=True)

        # Column headers
        hdr_cols = st.columns([0.5, 1.5, 1.5, 1.5, 2])
        hdr_cols[0].markdown(f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">Set</div>', unsafe_allow_html=True)
        hdr_cols[1].markdown(f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">Weight (kg)</div>', unsafe_allow_html=True)
        hdr_cols[2].markdown(f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">Reps</div>', unsafe_allow_html=True)
        hdr_cols[3].markdown(f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">RPE (1-10)</div>', unsafe_allow_html=True)
        hdr_cols[4].markdown(f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">Notes</div>', unsafe_allow_html=True)

        for s in range(1, num_sets + 1):
            existing = ex_log.get(s, {})
            cols = st.columns([0.5, 1.5, 1.5, 1.5, 2])

            with cols[0]:
                st.markdown(f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]};padding-top:8px">{s}</div>', unsafe_allow_html=True)
            with cols[1]:
                w_val = existing.get("weight_kg") if existing.get("weight_kg") is not None else default_weight
                weight = st.number_input("w", min_value=0.0, max_value=500.0,
                                         value=float(w_val), step=2.5,
                                         key=f"wt_{ex_id}_{s}", label_visibility="collapsed")
            with cols[2]:
                r_val = existing.get("actual_reps", 0) or 0
                reps = st.number_input("r", min_value=0, max_value=100,
                                       value=int(r_val), step=1,
                                       key=f"rp_{ex_id}_{s}", label_visibility="collapsed")
            with cols[3]:
                rpe_val = existing.get("rpe", 0) or 0
                rpe = st.number_input("e", min_value=0, max_value=10,
                                      value=int(rpe_val), step=1,
                                      key=f"rpe_{ex_id}_{s}", label_visibility="collapsed")
            with cols[4]:
                notes = st.text_input("n", value=existing.get("notes", "") or "",
                                      key=f"nt_{ex_id}_{s}", label_visibility="collapsed")

            all_sets.append({
                "exercise_id": ex_id,
                "exercise_name": ex_name,
                "set_number": s,
                "prescribed_reps": prescribed_reps,
                "actual_reps": reps if reps > 0 else None,
                "weight_kg": weight if weight > 0 else None,
                "rpe": rpe if rpe > 0 else None,
                "notes": notes if notes else None,
            })

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    return all_sets
