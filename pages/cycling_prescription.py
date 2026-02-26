"""Cycling Training — TrainerRoad-style power-based training prescription."""

import streamlit as st
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.cycling_display import (
    render_ftp_card,
    render_zones_table,
    render_pmc_chart,
    render_workout_card,
    render_interval_diagram,
    render_weekly_plan,
    render_progression_levels,
    render_ramp_test_guide,
    render_ride_summary_card,
)
from config.cycling_data import (
    WORKOUT_LIBRARY,
    WORKOUT_LIBRARY_BY_ID,
    WORKOUT_TYPES,
    TRAINING_PHASES,
    DIFFICULTY_SURVEY_OPTIONS,
    ATHLETE_TYPES,
    WATT_KG_CATEGORIES,
)
from services.cycling_service import (
    get_cycling_profile,
    save_cycling_profile,
    get_zones,
    calculate_if,
    calculate_tss,
    log_ride,
    get_ride_history,
    get_pmc_data,
    get_progression_levels,
    update_progression_levels,
    generate_training_plan,
    save_training_plan,
    get_active_plan,
    get_this_week_workouts,
    complete_workout,
    reschedule_workout,
    suggest_todays_workout,
    calculate_weekly_tss,
    get_adaptive_suggestions,
    get_wkg_category,
)
from db.database import get_connection

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Cycling Training",
    "Power-based training with FTP zones, TSS, Performance Management Chart, and adaptive prescription.",
)

tab_dash, tab_plan, tab_log, tab_workouts, tab_settings = st.tabs([
    "Dashboard", "Training Plan", "Log Ride", "Workout Library", "Settings"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dash:
    profile = get_cycling_profile(user_id)
    ftp = profile["ftp_watts"] if profile else 200

    # Top row: FTP card + quick metrics
    col_ftp, col_metrics = st.columns([1, 2])
    with col_ftp:
        render_ftp_card(profile)

    with col_metrics:
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        week_tss = calculate_weekly_tss(user_id, week_start)
        pmc = get_pmc_data(user_id, days=7)
        ctl = pmc[-1]["ctl"] if pmc else 0.0
        atl = pmc[-1]["atl"] if pmc else 0.0
        tsb = pmc[-1]["tsb"] if pmc else 0.0
        rides_this_week = len([r for r in get_ride_history(user_id, days=7)])

        tsb_color = A["green"] if tsb >= 0 else A["orange"]
        stat_html = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center">'
            f'<div style="font-size:24px;font-weight:800;color:{A["orange"]}">{week_tss:.0f}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">TSS This Week</div>'
            f'</div>'
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center">'
            f'<div style="font-size:24px;font-weight:800;color:{A["blue"]}">{rides_this_week}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">Rides This Week</div>'
            f'</div>'
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center">'
            f'<div style="font-size:24px;font-weight:800;color:{A["green"]}">{ctl:.0f}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">CTL — Fitness</div>'
            f'</div>'
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;text-align:center">'
            f'<div style="font-size:24px;font-weight:800;color:{tsb_color}">{tsb:+.0f}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">TSB — Form</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(stat_html, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # PMC Chart
    render_section_header(
        "Performance Management Chart",
        "CTL=Fitness (42-day load) · ATL=Fatigue (7-day load) · TSB=Form (CTL−ATL)"
    )
    pmc_90 = get_pmc_data(user_id, days=90)
    render_pmc_chart(pmc_90)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Zones in expander
    with st.expander("Power Zones (based on your FTP)", expanded=False):
        zones = get_zones(ftp)
        render_zones_table(zones)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Progression Levels
    render_section_header("Progression Levels", "Your current level per training energy system")
    levels = get_progression_levels(user_id)
    render_progression_levels(levels)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Today's suggested workout
    render_section_header("Today's Suggested Workout")
    suggested = suggest_todays_workout(user_id)
    if suggested:
        render_workout_card(suggested, ftp)
        if st.button("Start This Workout", type="primary", key="dash_start"):
            st.session_state["prefill_workout_id"] = suggested["id"]
            st.rerun()
    else:
        st.info("Set your FTP in Settings and log a few rides to get personalised suggestions.")

    # Adaptive suggestions
    suggestions = get_adaptive_suggestions(user_id)
    if suggestions:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_section_header("Adaptive Recommendations")
        for sug in suggestions:
            if sug["type"] == "upgrade":
                st.warning(f"&#9650; {sug['message']}")
            elif sug["type"] == "downgrade":
                st.info(f"&#8595; {sug['message']}")
            elif sug["type"] == "recovery_day":
                st.warning(f"&#128164; {sug['message']}")
            else:
                st.caption(f"&#8680; {sug['message']}")

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Training Plan
# ══════════════════════════════════════════════════════════════════════════
with tab_plan:
    active_plan = get_active_plan(user_id)

    if active_plan:
        phase_info = TRAINING_PHASES.get(active_plan["phase"], {})
        today = date.today()
        start = date.fromisoformat(active_plan["start_date"])
        current_week_num = min((today - start).days // 7 + 1, active_plan["weeks"])

        render_section_header(
            phase_info.get("label", active_plan["phase"]),
            f"Week {current_week_num} of {active_plan['weeks']} · Started {active_plan['start_date']}"
        )

        # Phase description card
        phase_html = (
            f'<div style="background:{phase_info.get("color","#2196F3")}08;'
            f'border:1px solid {phase_info.get("color","#2196F3")}25;'
            f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:16px">'
            f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">'
            f'{phase_info.get("description","")}</div>'
            f'</div>'
        )
        st.markdown(phase_html, unsafe_allow_html=True)

        # Weekly TSS progress bar
        week_start_str = (today - timedelta(days=today.weekday())).isoformat()
        week_tss = calculate_weekly_tss(user_id, week_start_str)
        target_tss = active_plan.get("avg_weekly_tss") or 400
        tss_pct = min(week_tss / target_tss * 100, 100) if target_tss > 0 else 0
        tss_color = A["green"] if tss_pct >= 80 else A["orange"] if tss_pct >= 50 else A["label_tertiary"]
        tss_bar_html = (
            f'<div style="margin-bottom:16px">'
            f'<div style="display:flex;justify-content:space-between;font-size:12px;'
            f'font-weight:600;color:{A["label_secondary"]};margin-bottom:6px">'
            f'<span>Weekly TSS Progress</span>'
            f'<span style="color:{tss_color}">{week_tss:.0f} / {target_tss} TSS ({tss_pct:.0f}%)</span>'
            f'</div>'
            f'<div style="background:rgba(0,0,0,0.06);border-radius:999px;height:8px">'
            f'<div style="width:{tss_pct:.1f}%;background:{tss_color};'
            f'border-radius:999px;height:8px"></div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(tss_bar_html, unsafe_allow_html=True)

        # Weekly calendar
        week_workouts = get_this_week_workouts(user_id)
        render_weekly_plan(week_workouts, today)

        # Adaptive suggestions
        suggestions = get_adaptive_suggestions(user_id)
        if suggestions:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            for sug in suggestions:
                if sug["type"] == "reschedule" and sug.get("workout_id"):
                    col_msg, col_act = st.columns([3, 1])
                    with col_msg:
                        st.warning(f"&#8680; {sug['message']}")
                    with col_act:
                        new_date = st.date_input(
                            "Move to", value=date.today(),
                            key=f"rs_date_{sug['workout_id']}"
                        )
                        if st.button("Reschedule", key=f"rs_btn_{sug['workout_id']}"):
                            reschedule_workout(user_id, sug["workout_id"], new_date.isoformat())
                            st.toast("Workout rescheduled!")
                            st.rerun()
                elif sug["type"] in ("upgrade", "downgrade", "recovery_day"):
                    st.info(f"&#128161; {sug['message']}")

        # Complete workout section
        if week_workouts:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.expander("Mark Workout as Complete", expanded=False):
                scheduled = [w for w in week_workouts if w.get("status") == "scheduled"]
                if scheduled:
                    options = [
                        f"{w['date']} — {WORKOUT_LIBRARY_BY_ID.get(w['workout_id'], {}).get('name', w['workout_id'])}"
                        for w in scheduled
                    ]
                    choice = st.selectbox("Workout", options, key="complete_sel")
                    idx = options.index(choice)
                    plan_wid = scheduled[idx]["plan_workout_id"]
                    survey_opts = [f"{k} — {v['label']} {v['emoji']}" for k, v in DIFFICULTY_SURVEY_OPTIONS.items()]
                    survey_choice = st.selectbox("How hard was it?", survey_opts, index=2, key="complete_survey")
                    survey_val = int(survey_choice.split(" — ")[0])
                    if st.button("Mark Complete", type="primary", key="complete_btn"):
                        complete_workout(user_id, plan_wid, survey_val)
                        st.toast("Workout marked complete! Progression levels updated.")
                        st.rerun()
                else:
                    st.caption("All workouts this week are completed or rescheduled.")

        # Delete plan
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        _, col_del = st.columns([4, 1])
        with col_del:
            if st.button("Delete Plan", type="secondary", use_container_width=True):
                conn = get_connection()
                conn.execute("UPDATE cycling_plan SET active = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                st.toast("Training plan removed.")
                st.rerun()

    else:
        render_section_header("Generate Training Plan", "Choose your phase, duration, and weekly availability")

        with st.form("cycling_plan_form"):
            col_phase, col_weeks, col_days = st.columns(3)

            with col_phase:
                phase_options = list(TRAINING_PHASES.keys())
                phase_labels = [TRAINING_PHASES[p]["label"] for p in phase_options]
                phase_choice = st.selectbox("Training Phase", phase_labels)
                phase_key = phase_options[phase_labels.index(phase_choice)]

            with col_weeks:
                default_weeks = TRAINING_PHASES[phase_key]["weeks"]
                weeks = st.number_input("Weeks", min_value=4, max_value=default_weeks, value=default_weeks, step=1)

            with col_days:
                days_per_week = st.selectbox("Days / Week", [3, 4, 5, 6], index=1)

            # Phase info card
            phase_data = TRAINING_PHASES[phase_key]
            phase_info_html = (
                f'<div style="background:{phase_data["color"]}08;'
                f'border-left:3px solid {phase_data["color"]};'
                f'padding:10px 12px;border-radius:0 {A["radius_md"]} {A["radius_md"]} 0;'
                f'margin:8px 0">'
                f'<div style="font-size:12px;font-weight:600;color:{phase_data["color"]};'
                f'margin-bottom:4px">{phase_data["label"]}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">'
                f'{phase_data["description"]}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:6px">'
                f'Target TSS: {phase_data["tss_range"][0]}–{phase_data["tss_range"][1]} / week &middot; '
                f'Focus: {", ".join(phase_data["primary_types"])}</div>'
                f'</div>'
            )
            st.markdown(phase_info_html, unsafe_allow_html=True)

            submitted = st.form_submit_button("Generate Plan", type="primary", use_container_width=True)
            if submitted:
                if not get_cycling_profile(user_id):
                    st.error("Please set your FTP in the Settings tab first.")
                else:
                    plan = generate_training_plan(user_id, phase_key, int(weeks), days_per_week)
                    save_training_plan(user_id, plan)
                    st.toast(f"{phase_data['label']} generated — {int(weeks)} weeks, {days_per_week} days/week!")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Log Ride
# ══════════════════════════════════════════════════════════════════════════
with tab_log:
    render_section_header("Log a Ride", "Record power data to update your PMC and progression levels")

    profile = get_cycling_profile(user_id)
    ftp = profile["ftp_watts"] if profile else 200

    # Pre-fill workout from Dashboard "Start" button
    prefill_id = st.session_state.pop("prefill_workout_id", None)

    # TSS live calculator (outside form for live preview)
    with st.expander("&#128293; Quick TSS Calculator", expanded=False):
        qcol1, qcol2, qcol3 = st.columns(3)
        with qcol1:
            q_dur = st.number_input("Duration (min)", min_value=5, max_value=600, value=60, key="q_dur")
        with qcol2:
            q_power = st.number_input("Avg Power (W)", min_value=0, max_value=1000, value=200, key="q_power")
        with qcol3:
            q_ftp = st.number_input("FTP (W)", min_value=50, max_value=600, value=ftp, key="q_ftp")
        if q_power > 0 and q_ftp > 0:
            q_if = calculate_if(q_power, q_ftp)
            q_tss = calculate_tss(q_dur, q_power, q_ftp)
            q_html = (
                f'<div style="display:flex;gap:20px;padding:10px;'
                f'background:{A["bg_secondary"]};border-radius:{A["radius_md"]};margin-top:8px">'
                f'<div><div style="font-size:20px;font-weight:800;color:{A["blue"]}">{q_if:.3f}</div>'
                f'<div style="font-size:10px;color:{A["label_tertiary"]}">Intensity Factor (IF)</div></div>'
                f'<div><div style="font-size:20px;font-weight:800;color:{A["orange"]}">{q_tss:.0f}</div>'
                f'<div style="font-size:10px;color:{A["label_tertiary"]}">Training Stress Score (TSS)</div></div>'
                f'</div>'
            )
            st.markdown(q_html, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.form("log_ride_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ride_date = st.date_input("Ride Date", value=date.today())
        with col2:
            duration_min = st.number_input("Duration (min)", min_value=5, max_value=600, value=60)
        with col3:
            avg_power = st.number_input("Avg Power (W)", min_value=0, max_value=1000, value=0)

        col4, col5, col6 = st.columns(3)
        with col4:
            norm_power = st.number_input("Normalized Power (W, optional)", min_value=0, max_value=1000, value=0)
        with col5:
            elevation_m = st.number_input("Elevation (m, optional)", min_value=0, max_value=10000, value=0)
        with col6:
            survey_opts = [f"{k} — {v['label']} {v['emoji']}" for k, v in DIFFICULTY_SURVEY_OPTIONS.items()]
            survey_choice = st.selectbox("How was it?", survey_opts, index=2)
            difficulty_survey = int(survey_choice.split(" — ")[0])

        # Workout link (optional)
        workout_id_list = [None] + [w["id"] for w in WORKOUT_LIBRARY]
        workout_label_list = ["None — free ride"] + [
            f"{w['name']} ({WORKOUT_TYPES.get(w['type'], {}).get('label', w['type'])})"
            for w in WORKOUT_LIBRARY
        ]
        default_idx = workout_id_list.index(prefill_id) if prefill_id in workout_id_list else 0
        workout_choice = st.selectbox("Workout (optional)", workout_label_list, index=default_idx)
        selected_wid = workout_id_list[workout_label_list.index(workout_choice)]

        notes = st.text_area("Notes", placeholder="Conditions, how you felt, terrain...", height=70)

        submitted = st.form_submit_button("Save Ride", type="primary", use_container_width=True)
        if submitted:
            if avg_power > 0 and duration_min > 0:
                if_score = calculate_if(avg_power, ftp)
                tss = calculate_tss(duration_min, avg_power, ftp)
                ride_data = {
                    "ride_date": ride_date.isoformat(),
                    "duration_min": duration_min,
                    "avg_power": avg_power,
                    "normalized_power": norm_power if norm_power > 0 else None,
                    "if_score": if_score,
                    "tss": tss,
                    "elevation_m": elevation_m if elevation_m > 0 else None,
                    "difficulty_survey": difficulty_survey,
                    "workout_id": selected_wid,
                    "notes": notes if notes else None,
                    "source": "manual",
                }
                log_ride(user_id, ride_data)
                if selected_wid:
                    workout = WORKOUT_LIBRARY_BY_ID.get(selected_wid, {})
                    if workout.get("type"):
                        update_progression_levels(user_id, workout["type"], difficulty_survey)
                st.toast(f"Ride saved! TSS: {tss:.0f} · IF: {if_score:.3f}")
                st.rerun()
            else:
                st.warning("Enter a valid average power and duration to log the ride.")

    # Recent rides
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Recent Rides")
    recent = get_ride_history(user_id, days=30)
    if recent:
        for ride in recent[:10]:
            render_ride_summary_card(ride)
    else:
        st.caption("No rides logged yet. Log your first ride above.")

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Workout Library
# ══════════════════════════════════════════════════════════════════════════
with tab_workouts:
    render_section_header("Workout Library", "Browse 20+ structured power-based workouts")

    profile = get_cycling_profile(user_id)
    ftp = profile["ftp_watts"] if profile else 200

    # Filters
    col_type, col_dur, col_level = st.columns(3)
    with col_type:
        type_keys = list(WORKOUT_TYPES.keys())
        type_labels_all = ["All Types"] + [WORKOUT_TYPES[t]["label"] for t in type_keys]
        type_choice = st.selectbox("Type", type_labels_all, key="lib_type")
        type_filter = None if type_choice == "All Types" else type_keys[type_labels_all.index(type_choice) - 1]

    with col_dur:
        dur_choice = st.selectbox("Duration", ["Any", "< 45 min", "45–60 min", "60–90 min", "> 90 min"], key="lib_dur")

    with col_level:
        level_choice = st.selectbox("Difficulty", ["Any Level", "1–3 (Beginner)", "4–6 (Intermediate)", "7–10 (Advanced)"], key="lib_lvl")

    # Apply filters
    filtered = list(WORKOUT_LIBRARY)
    if type_filter:
        filtered = [w for w in filtered if w["type"] == type_filter]
    if dur_choice == "< 45 min":
        filtered = [w for w in filtered if w["duration_min"] < 45]
    elif dur_choice == "45–60 min":
        filtered = [w for w in filtered if 45 <= w["duration_min"] <= 60]
    elif dur_choice == "60–90 min":
        filtered = [w for w in filtered if 60 < w["duration_min"] <= 90]
    elif dur_choice == "> 90 min":
        filtered = [w for w in filtered if w["duration_min"] > 90]
    if level_choice == "1–3 (Beginner)":
        filtered = [w for w in filtered if w["difficulty_level"] <= 3.0]
    elif level_choice == "4–6 (Intermediate)":
        filtered = [w for w in filtered if 3.0 < w["difficulty_level"] <= 6.0]
    elif level_choice == "7–10 (Advanced)":
        filtered = [w for w in filtered if w["difficulty_level"] > 6.0]

    if not filtered:
        st.info("No workouts match the selected filters.")
    else:
        st.caption(f"Showing {len(filtered)} workout{'s' if len(filtered) != 1 else ''} · FTP: {ftp}W")
        for workout in filtered:
            type_info = WORKOUT_TYPES.get(workout["type"], {})
            with st.expander(
                f"{workout['name']} — {type_info.get('label', workout['type'])} | "
                f"{workout['duration_min']} min | ~{workout['tss_estimate']} TSS | "
                f"Level {workout['difficulty_level']:.1f}",
                expanded=False,
            ):
                render_workout_card(workout, ftp)

# ══════════════════════════════════════════════════════════════════════════
# Tab 5: Settings
# ══════════════════════════════════════════════════════════════════════════
with tab_settings:
    render_section_header("Cycling Settings", "FTP, profile, and ramp test guide")

    profile = get_cycling_profile(user_id)

    with st.expander("FTP & Athlete Profile", expanded=not bool(profile)):
        with st.form("ftp_form"):
            col_ftp, col_wt, col_type = st.columns(3)
            with col_ftp:
                current_ftp = profile["ftp_watts"] if profile else 200
                new_ftp = st.number_input(
                    "FTP (watts)", min_value=50, max_value=600, value=current_ftp, step=5,
                    help="Your 1-hour maximal power output. All zones are calculated from this."
                )
            with col_wt:
                current_wt = profile.get("weight_kg") if profile else None
                weight_kg = st.number_input(
                    "Body Weight (kg)", min_value=30.0, max_value=200.0,
                    value=float(current_wt) if current_wt else 70.0, step=0.5,
                )
            with col_type:
                current_type = profile.get("athlete_type", "All-Around") if profile else "All-Around"
                athlete_type = st.selectbox(
                    "Athlete Type", ATHLETE_TYPES,
                    index=ATHLETE_TYPES.index(current_type) if current_type in ATHLETE_TYPES else 0,
                )

            col_event, col_date = st.columns(2)
            with col_event:
                goal_event = st.text_input(
                    "Goal Event (optional)", value=profile.get("goal_event", "") if profile else "",
                    placeholder="e.g. Gran Fondo, local crit, triathlon..."
                )
            with col_date:
                goal_date_val = None
                if profile and profile.get("goal_date"):
                    try:
                        goal_date_val = date.fromisoformat(profile["goal_date"])
                    except Exception:
                        pass
                goal_date = st.date_input("Goal Date (optional)", value=goal_date_val)

            save_btn = st.form_submit_button("Save Profile", type="primary", use_container_width=True)
            if save_btn:
                save_cycling_profile(
                    user_id, int(new_ftp), float(weight_kg), athlete_type,
                    goal_event if goal_event else None,
                    goal_date.isoformat() if goal_date else None,
                )
                st.toast(f"FTP saved: {new_ftp}W")
                st.rerun()

    # W/kg display
    if profile:
        wkg_val = profile["ftp_watts"] / profile["weight_kg"] if profile.get("weight_kg") else None
        if wkg_val:
            cat = get_wkg_category(profile["ftp_watts"], profile["weight_kg"])
            # Find category color
            cat_color = A["blue"]
            for c in WATT_KG_CATEGORIES:
                if c["label"] == cat:
                    cat_color = c["color"]
                    break
            wkg_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:14px;margin:8px 0;'
                f'display:flex;align-items:center;gap:16px">'
                f'<div><div style="font-size:28px;font-weight:800;color:{cat_color}">'
                f'{wkg_val:.2f}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">W / kg</div></div>'
                f'<div><div style="font-size:14px;font-weight:700;color:{cat_color}">'
                f'{cat}</div>'
                f'<div style="font-size:11px;color:{A["label_secondary"]}">Based on FTP {profile["ftp_watts"]}W · {profile["weight_kg"]}kg</div></div>'
                f'</div>'
            )
            st.markdown(wkg_html, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.expander("FTP Ramp Test Protocol", expanded=False):
        render_ramp_test_guide()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Zones preview
    if profile:
        render_section_header("Your Power Zones", f"Based on FTP: {profile['ftp_watts']}W")
        zones = get_zones(profile["ftp_watts"])
        render_zones_table(zones)

    # Zone legend info
    zone_legend_html = (
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_md"]};'
        f'padding:12px;margin-top:12px">'
        f'<div style="font-size:11px;font-weight:600;color:{A["label_secondary"]};margin-bottom:6px">'
        f'About Power Zones</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:17px">'
        f'Based on the Coggan 7-zone model. TSS (Training Stress Score) quantifies workout load — '
        f'100 TSS = 1 hour at exactly FTP. CTL (Chronic Training Load) is your fitness, '
        f'calculated as a 42-day rolling average of TSS. ATL (Acute Training Load) is 7-day '
        f'fatigue. TSB (Training Stress Balance) is Form = CTL − ATL. '
        f'Positive TSB = fresh; negative = fatigued.</div>'
        f'</div>'
    )
    st.markdown(zone_legend_html, unsafe_allow_html=True)
