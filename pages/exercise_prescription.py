"""Exercise Prescription — Science-based PPL training programs."""

import streamlit as st
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.exercise_prescription_display import (
    render_key_terms_guide,
    render_program_overview,
    render_week_header,
    render_day_card,
    render_volume_chart,
    render_rir_guide,
    render_volume_landmarks_table,
    render_mesocycle_timeline,
)
from config.exercise_prescription_data import (
    MESOCYCLE_TEMPLATES,
    SCHEDULE_TEMPLATES,
    PPL_SPLIT,
    RIR_GUIDE,
    VOLUME_LANDMARKS,
)
from services.exercise_prescription_service import (
    generate_program,
    get_week_volume_summary,
    save_program,
    get_saved_program,
    delete_program,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Exercise Prescription",
    "Science-based Push/Pull/Legs training programs with RP periodization, "
    "volume landmarks, and mesocycle progression.",
)

tab_program, tab_generate, tab_science, tab_reference = st.tabs([
    "My Program", "Generate Program", "Science", "Reference"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: My Program
# ══════════════════════════════════════════════════════════════════════════
with tab_program:
    saved = get_saved_program(user_id)

    if not saved:
        st.info("No program yet. Go to the **Generate Program** tab to create your training plan.")
    else:
        # Key terms guide (collapsible)
        with st.expander("New to training programs? Read this first", expanded=False):
            render_key_terms_guide()

        render_program_overview(saved)
        render_mesocycle_timeline(saved)

        # Week selector
        week_options = [f"Week {w['week']} — {w['label']}" for w in saved["weeks"]]
        selected_week_label = st.selectbox("Select Week", week_options)
        week_idx = week_options.index(selected_week_label)

        week = saved["weeks"][week_idx]
        render_week_header(week)

        # Volume chart for this week
        volume = get_week_volume_summary(saved, week_idx)
        render_volume_chart(volume, saved.get("level", "intermediate"))

        # Day-by-day exercises
        for day in week["days"]:
            render_day_card(day)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Delete program
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        col_spacer, col_delete = st.columns([3, 1])
        with col_delete:
            if st.button("Delete Program", type="secondary", use_container_width=True):
                delete_program(user_id, saved.get("_db_id", 0))
                st.toast("Program deleted.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Generate Program
# ══════════════════════════════════════════════════════════════════════════
with tab_generate:
    render_section_header(
        "Generate Training Program",
        "Choose your experience level and schedule"
    )

    with st.form("generate_program_form"):
        col_level, col_sched = st.columns(2)

        with col_level:
            level_options = list(MESOCYCLE_TEMPLATES.keys())
            level_labels = [MESOCYCLE_TEMPLATES[k]["label"] for k in level_options]
            level_choice = st.selectbox("Experience Level", level_labels)
            level_key = level_options[level_labels.index(level_choice)]

        with col_sched:
            sched_options = list(SCHEDULE_TEMPLATES.keys())
            sched_labels = [SCHEDULE_TEMPLATES[k]["label"] for k in sched_options]
            sched_choice = st.selectbox("Weekly Schedule", sched_labels)
            sched_key = sched_options[sched_labels.index(sched_choice)]

        # Show schedule info
        sched_info = SCHEDULE_TEMPLATES[sched_key]
        info_html = (
            f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_md"]};'
            f'padding:12px;margin:8px 0">'
            f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">'
            f'{sched_info["note"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:4px">'
            f'Days per week: {sched_info["days_per_week"]} &middot; '
            f'Best for: {sched_info["recommended_for"]}</div>'
            f'</div>'
        )
        st.markdown(info_html, unsafe_allow_html=True)

        # PPL split preview
        st.markdown("**Training Split Preview**")
        split_cols = st.columns(3)
        for idx, (split_key, split_data) in enumerate(PPL_SPLIT.items()):
            with split_cols[idx]:
                preview_html = (
                    f'<div style="background:{split_data["color"]}08;'
                    f'border:1px solid {split_data["color"]}20;'
                    f'border-radius:{A["radius_md"]};padding:12px;text-align:center">'
                    f'<div style="font-size:24px">{split_data["icon"]}</div>'
                    f'<div style="font-size:13px;font-weight:700;color:{split_data["color"]};'
                    f'margin:4px 0">{split_data["label"]}</div>'
                    f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                    f'{split_data["subtitle"]}</div>'
                    f'</div>'
                )
                st.markdown(preview_html, unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "Generate My Program",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            program = generate_program(
                level=level_key,
                schedule=sched_key,
                goal="hypertrophy",
            )
            save_program(user_id, program)
            st.toast("Training program generated and saved!")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Science
# ══════════════════════════════════════════════════════════════════════════
with tab_science:
    render_section_header("The Science Behind Your Program")

    # PPL Split evidence
    ppl_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:8px">Push / Pull / Legs Split</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:20px;'
        f'margin-bottom:8px">'
        f'The PPL split divides training into three movement patterns: '
        f'<strong>Push</strong> (chest, shoulders, triceps), '
        f'<strong>Pull</strong> (back, biceps, rear delts), and '
        f'<strong>Legs</strong> (quads, hamstrings, glutes, calves). '
        f'This allows each muscle group to be trained 2&times; per week on a 6-day '
        f'rotation, which meta-analyses show is superior for hypertrophy.</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:16px">'
        f'Schoenfeld et al. (2016) — "Effects of Resistance Training Frequency on '
        f'Measures of Muscle Hypertrophy: A Systematic Review and Meta-Analysis" '
        f'(PMID: 27102172). Training each muscle 2&times;/week produced significantly '
        f'greater hypertrophy compared to 1&times;/week.</div>'
        f'</div>'
    )
    st.markdown(ppl_html, unsafe_allow_html=True)

    # Volume landmarks
    vol_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:8px">Volume Landmarks (RP Model)</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:20px;'
        f'margin-bottom:8px">'
        f'Training volume (total hard sets per muscle per week) is the primary driver '
        f'of hypertrophy. Renaissance Periodization defines four volume landmarks:</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:22px">'
        f'<strong>MV</strong> — Maintenance Volume: minimum to avoid losing muscle<br>'
        f'<strong>MEV</strong> — Minimum Effective Volume: minimum to stimulate growth<br>'
        f'<strong>MAV</strong> — Maximum Adaptive Volume: the sweet spot for most lifters<br>'
        f'<strong>MRV</strong> — Maximum Recoverable Volume: exceeding this leads to overtraining</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:8px;line-height:16px">'
        f'Schoenfeld &amp; Krieger (2017) — "Dose-response relationship between weekly '
        f'resistance training volume and increases in muscle mass" (PMID: 28032998). '
        f'10+ sets/week per muscle produced significantly greater hypertrophy than &lt;10.</div>'
        f'</div>'
    )
    st.markdown(vol_html, unsafe_allow_html=True)

    # Periodization
    period_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:8px">Mesocycle Periodization</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:20px;'
        f'margin-bottom:8px">'
        f'Each mesocycle (4-6 weeks) begins at MEV to resensitize muscles to volume, '
        f'progressively increases through MAV for maximal stimulus, then deloads to allow '
        f'recovery and supercompensation. This prevents stagnation and reduces injury risk.</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:16px">'
        f'Ogasawara et al. (2013) — "Comparison of muscle hypertrophy following 6-month '
        f'of continuous and periodic strength training" (PMID: 23604232). Periodic training '
        f'with deloads produced similar hypertrophy to continuous training, with less fatigue.</div>'
        f'</div>'
    )
    st.markdown(period_html, unsafe_allow_html=True)

    # RIR
    rir_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:16px">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};'
        f'margin-bottom:8px">RIR-Based Autoregulation</div>'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:20px;'
        f'margin-bottom:8px">'
        f'Reps In Reserve (RIR) is the estimated number of reps you could still perform '
        f'before failure. Training at RIR 1-3 for most sets provides an optimal stimulus '
        f'while managing fatigue. Going to failure (RIR 0) should be reserved for isolation '
        f'exercises and the final week before deload.</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:16px">'
        f'Helms et al. (2016) — "Application of the Repetitions in Reserve-Based Rating '
        f'of Perceived Exertion Scale for Resistance Training" (PMID: 27834585). '
        f'RIR-based prescription allows individualized intensity management.</div>'
        f'</div>'
    )
    st.markdown(rir_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Reference
# ══════════════════════════════════════════════════════════════════════════
with tab_reference:
    render_section_header("Training Reference", "Volume landmarks and RIR guide")

    render_volume_landmarks_table()
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_rir_guide()
