"""Exercise Library — Browse strength training exercises with form guides."""

import streamlit as st
from components.custom_theme import (
    APPLE, render_hero_banner, render_section_header,
)
from config.exercise_library_data import (
    EXERCISE_LIBRARY, MUSCLE_GROUPS, EQUIPMENT_TYPES,
    DIFFICULTY_LEVELS, get_exercises_by_muscle,
    search_exercises,
)

A = APPLE


# ── Card Renderer (must be defined before use) ───────────────────────────────

def _render_exercise_library_card(exercise):
    """Render a detailed exercise card with form guide."""
    mg = MUSCLE_GROUPS.get(exercise["muscle_group"], {})
    diff = DIFFICULTY_LEVELS.get(exercise["difficulty"], {})
    equip = EQUIPMENT_TYPES.get(exercise["equipment"], {})

    # Type badge (compound vs isolation)
    type_color = A["blue"] if exercise["type"] == "compound" else A["purple"]
    type_label = exercise["type"].title()

    # Build the card
    with st.expander(f'{mg.get("icon", "")} **{exercise["name"]}** — {diff.get("label", "")} | {equip.get("label", "")}'):
        # Header badges
        badges_html = (
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">'
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:{mg.get("color", "#999")}15;'
            f'color:{mg.get("color", "#999")}">{mg.get("label", "")}</span>'
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:{diff.get("color", "#999")}15;'
            f'color:{diff.get("color", "#999")}">{diff.get("label", "")}</span>'
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:{type_color}15;'
            f'color:{type_color}">{type_label}</span>'
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:rgba(0,0,0,0.04);'
            f'color:{A["label_secondary"]}">{equip.get("icon", "")} {equip.get("label", "")}</span>'
            f'</div>'
        )
        st.markdown(badges_html, unsafe_allow_html=True)

        if exercise["secondary_muscles"]:
            sec_names = [MUSCLE_GROUPS.get(m, {}).get("label", m) for m in exercise["secondary_muscles"]]
            st.markdown(f'**Secondary muscles:** {", ".join(sec_names)}')

        # Description
        desc_html = (
            f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_md"]};'
            f'padding:14px;margin-bottom:12px">'
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:6px">'
            f'How to Perform</div>'
            f'<div style="font-size:14px;line-height:20px;color:{A["label_primary"]}">'
            f'{exercise["description"]}</div>'
            f'</div>'
        )
        st.markdown(desc_html, unsafe_allow_html=True)

        # Cues and mistakes side by side
        col_cues, col_mistakes = st.columns(2)
        with col_cues:
            cues_html = (
                f'<div style="background:#E8F5E915;border:1px solid #1E8E3E20;'
                f'border-radius:{A["radius_md"]};padding:12px">'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["green"]};margin-bottom:4px">'
                f'&#9989; Key Cues</div>'
                f'<div style="font-size:13px;line-height:18px;color:{A["label_primary"]}">'
                f'{exercise["cues"]}</div>'
                f'</div>'
            )
            st.markdown(cues_html, unsafe_allow_html=True)

        with col_mistakes:
            mistakes_html = (
                f'<div style="background:#FFEBEE15;border:1px solid #D9302520;'
                f'border-radius:{A["radius_md"]};padding:12px">'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["red"]};margin-bottom:4px">'
                f'&#9888; Common Mistakes</div>'
                f'<div style="font-size:13px;line-height:18px;color:{A["label_primary"]}">'
                f'{exercise["mistakes"]}</div>'
                f'</div>'
            )
            st.markdown(mistakes_html, unsafe_allow_html=True)

        # Sets/reps recommendation
        reps_html = (
            f'<div style="margin-top:10px;padding:10px 14px;background:{A["bg_elevated"]};'
            f'border:1px solid {A["separator"]};border-radius:{A["radius_md"]};'
            f'display:flex;align-items:center;gap:8px">'
            f'<span style="font-size:16px">&#128203;</span>'
            f'<div>'
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Recommended</div>'
            f'<div style="font-size:14px;font-weight:600;color:{A["label_primary"]}">'
            f'{exercise["sets_reps"]}</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(reps_html, unsafe_allow_html=True)

        # Video search link
        yt_query = exercise["video_search"].replace(" ", "+")
        video_html = (
            f'<div style="margin-top:8px;text-align:center">'
            f'<a href="https://www.youtube.com/results?search_query={yt_query}" '
            f'target="_blank" style="font-size:13px;color:{A["blue"]};'
            f'text-decoration:none;font-weight:600">'
            f'&#9654; Watch form videos on YouTube</a>'
            f'</div>'
        )
        st.markdown(video_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
render_hero_banner(
    "Strength Training Library",
    "50 exercises with proper form guides, cues, and common mistakes to avoid.",
    icon="&#127947;",
)

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
col_search, col_muscle, col_equip, col_diff = st.columns([3, 2, 2, 2])

with col_search:
    search_query = st.text_input(
        "Search exercises",
        placeholder="e.g. squat, curl, press...",
        label_visibility="collapsed",
    )

with col_muscle:
    muscle_options = ["All Muscles"] + [v["label"] for v in MUSCLE_GROUPS.values()]
    muscle_filter = st.selectbox("Muscle Group", muscle_options, label_visibility="collapsed")

with col_equip:
    equip_options = ["All Equipment"] + [v["label"] for v in EQUIPMENT_TYPES.values()]
    equip_filter = st.selectbox("Equipment", equip_options, label_visibility="collapsed")

with col_diff:
    diff_options = ["All Levels"] + [v["label"] for v in DIFFICULTY_LEVELS.values()]
    diff_filter = st.selectbox("Difficulty", diff_options, label_visibility="collapsed")

# ── Apply filters ─────────────────────────────────────────────────────────
exercises = list(EXERCISE_LIBRARY)

if search_query:
    exercises = search_exercises(search_query)

if muscle_filter != "All Muscles":
    muscle_key = next(k for k, v in MUSCLE_GROUPS.items() if v["label"] == muscle_filter)
    exercises = [e for e in exercises if e["muscle_group"] == muscle_key]

if equip_filter != "All Equipment":
    equip_key = next(k for k, v in EQUIPMENT_TYPES.items() if v["label"] == equip_filter)
    exercises = [e for e in exercises if e["equipment"] == equip_key]

if diff_filter != "All Levels":
    diff_key = next(k for k, v in DIFFICULTY_LEVELS.items() if v["label"] == diff_filter)
    exercises = [e for e in exercises if e["difficulty"] == diff_key]

# ── Results count ─────────────────────────────────────────────────────────
count_html = (
    f'<div style="font-size:13px;color:{A["label_tertiary"]};margin-bottom:12px">'
    f'Showing {len(exercises)} exercise{"s" if len(exercises) != 1 else ""}</div>'
)
st.markdown(count_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MUSCLE GROUP QUICK NAV (when no filters active)
# ══════════════════════════════════════════════════════════════════════════════
if not search_query and muscle_filter == "All Muscles" and equip_filter == "All Equipment" and diff_filter == "All Levels":
    nav_cards = ""
    for key, mg in MUSCLE_GROUPS.items():
        count = len(get_exercises_by_muscle(key))
        nav_cards += (
            f'<div style="text-align:center;padding:12px 8px;min-width:80px">'
            f'<div style="width:48px;height:48px;border-radius:50%;'
            f'background:{mg["color"]}15;display:flex;align-items:center;'
            f'justify-content:center;margin:0 auto 6px;font-size:22px">'
            f'{mg["icon"]}</div>'
            f'<div style="font-family:{A["font_display"]};font-size:13px;'
            f'font-weight:600;color:{A["label_primary"]}">{mg["label"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">{count} exercises</div>'
            f'</div>'
        )
    nav_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:12px;margin-bottom:20px">'
        f'<div style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:4px">'
        f'{nav_cards}</div></div>'
    )
    st.markdown(nav_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# EXERCISE CARDS
# ══════════════════════════════════════════════════════════════════════════════
if not exercises:
    st.caption("No exercises match your filters. Try broadening your search.")
else:
    # Group by muscle group for display
    if not search_query and muscle_filter == "All Muscles":
        current_group = None
        for ex in exercises:
            if ex["muscle_group"] != current_group:
                current_group = ex["muscle_group"]
                mg = MUSCLE_GROUPS[current_group]
                render_section_header(
                    f'{mg["icon"]} {mg["label"]}',
                    f'{len(get_exercises_by_muscle(current_group))} exercises'
                )
            _render_exercise_library_card(ex)
    else:
        for ex in exercises:
            _render_exercise_library_card(ex)
