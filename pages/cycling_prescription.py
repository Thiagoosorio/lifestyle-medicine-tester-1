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
from db.database import get_connection
import plotly.graph_objects as go

A = APPLE
user_id = st.session_state.user_id

_CYCLING_IMPORT_ERROR = None
try:
    import services.cycling_service as _cycling_service
except Exception as exc:
    _cycling_service = None
    _CYCLING_IMPORT_ERROR = exc


def _fallback_get_wkg(ftp_watts: int, weight_kg: float) -> float:
    if not weight_kg or weight_kg <= 0 or not ftp_watts or ftp_watts <= 0:
        return 0.0
    return round(float(ftp_watts) / float(weight_kg), 2)


def _fallback_get_wkg_category(ftp_watts: int, weight_kg: float) -> str:
    if not weight_kg or weight_kg <= 0 or not ftp_watts or ftp_watts <= 0:
        return "Unknown"
    wkg = float(ftp_watts) / float(weight_kg)
    for cat in WATT_KG_CATEGORIES:
        if cat["min_wkg"] <= wkg < cat["max_wkg"]:
            return cat["label"]
    return WATT_KG_CATEGORIES[-1]["label"] if WATT_KG_CATEGORIES else "Unknown"


def _fallback_get_power_bests(user_id: int, days: int = 90) -> dict:
    _ = (user_id, days)
    return {}


def _fallback_get_power_curve_data(user_id: int) -> list[dict]:
    _ = user_id
    return []


def _fallback_calculate_ftp_from_test(
    test_type: str,
    power_20min: float | None = None,
    power_8min: float | None = None,
    ramp_max: float | None = None,
) -> dict:
    if test_type == "20min" and power_20min and power_20min > 0:
        ftp = round(power_20min * 0.95)
        return {
            "ftp": ftp,
            "test_type": "20-Minute Test",
            "confidence": "high",
            "notes": f"FTP estimated as {power_20min:.0f}W x 0.95 = {ftp}W.",
        }
    if test_type == "8min" and power_8min and power_8min > 0:
        ftp = round(power_8min * 0.90)
        return {
            "ftp": ftp,
            "test_type": "8-Minute Test",
            "confidence": "moderate",
            "notes": f"FTP estimated as {power_8min:.0f}W x 0.90 = {ftp}W.",
        }
    if test_type == "ramp" and ramp_max and ramp_max > 0:
        ftp = round(ramp_max * 0.75)
        return {
            "ftp": ftp,
            "test_type": "Ramp Test",
            "confidence": "moderate",
            "notes": f"FTP estimated as {ramp_max:.0f}W x 0.75 = {ftp}W.",
        }
    return {
        "ftp": 0,
        "test_type": test_type,
        "confidence": "none",
        "notes": "Invalid input - provide a positive power value.",
    }


_missing_cycling_functions: list[str] = []


def _resolve_cycling_fn(name, fallback=None):
    if _cycling_service is not None and hasattr(_cycling_service, name):
        return getattr(_cycling_service, name)
    if fallback is not None:
        _missing_cycling_functions.append(name)
        return fallback

    def _missing(*args, **kwargs):
        raise RuntimeError(
            f"Cycling service function unavailable: {name}. "
            f"Underlying import error: {_CYCLING_IMPORT_ERROR}"
        )

    return _missing


get_cycling_profile = _resolve_cycling_fn("get_cycling_profile")
save_cycling_profile = _resolve_cycling_fn("save_cycling_profile")
get_zones = _resolve_cycling_fn("get_zones")
calculate_if = _resolve_cycling_fn("calculate_if")
calculate_tss = _resolve_cycling_fn("calculate_tss")
estimate_np = _resolve_cycling_fn("estimate_np")
log_ride = _resolve_cycling_fn("log_ride")
get_ride_history = _resolve_cycling_fn("get_ride_history")
get_pmc_data = _resolve_cycling_fn("get_pmc_data")
get_progression_levels = _resolve_cycling_fn("get_progression_levels")
update_progression_levels = _resolve_cycling_fn("update_progression_levels")
generate_training_plan = _resolve_cycling_fn("generate_training_plan")
save_training_plan = _resolve_cycling_fn("save_training_plan")
get_active_plan = _resolve_cycling_fn("get_active_plan")
get_this_week_workouts = _resolve_cycling_fn("get_this_week_workouts")
complete_workout = _resolve_cycling_fn("complete_workout")
reschedule_workout = _resolve_cycling_fn("reschedule_workout")
suggest_todays_workout = _resolve_cycling_fn("suggest_todays_workout")
calculate_weekly_tss = _resolve_cycling_fn("calculate_weekly_tss")
get_adaptive_suggestions = _resolve_cycling_fn("get_adaptive_suggestions")
get_wkg = _resolve_cycling_fn("get_wkg", fallback=_fallback_get_wkg)
get_wkg_category = _resolve_cycling_fn("get_wkg_category", fallback=_fallback_get_wkg_category)
get_power_bests = _resolve_cycling_fn("get_power_bests", fallback=_fallback_get_power_bests)
get_power_curve_data = _resolve_cycling_fn("get_power_curve_data", fallback=_fallback_get_power_curve_data)
calculate_ftp_from_test = _resolve_cycling_fn("calculate_ftp_from_test", fallback=_fallback_calculate_ftp_from_test)

if _CYCLING_IMPORT_ERROR is not None:
    st.error(
        "Cycling module failed to load. Please update to the latest version or check server logs."
    )
    st.code(str(_CYCLING_IMPORT_ERROR))
    st.stop()
if _missing_cycling_functions:
    missing_list = ", ".join(sorted(set(_missing_cycling_functions)))
    st.caption(
        f"Compatibility mode active for cycling analytics: using fallback implementations for {missing_list}."
    )

render_hero_banner(
    "Cycling Training",
    "Power-based training with FTP zones, TSS, Performance Management Chart, and adaptive prescription.",
)

tab_dash, tab_plan, tab_log, tab_workouts, tab_analytics, tab_settings, tab_coach = st.tabs([
    "Dashboard", "Training Plan", "Log Ride", "Workout Library", "Analytics", "Settings", "AI Coach"
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

        # Export panel
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("Export This Week's Workouts", expanded=False):
            col_garmin, col_tcx = st.columns(2)

            with col_garmin:
                garmin_hdr_html = (
                    f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]};'
                    f'margin-bottom:8px">Sync to Garmin Connect</div>'
                )
                st.markdown(garmin_hdr_html, unsafe_allow_html=True)
                try:
                    from services.garmin_service import get_garmin_connection
                    garmin_conn = get_garmin_connection(user_id)
                except Exception:
                    garmin_conn = None
                garmin_client = st.session_state.get("garmin_client")
                profile_g = get_cycling_profile(user_id)
                ftp_g = profile_g["ftp_watts"] if profile_g else 200

                if garmin_conn and garmin_client:
                    st.caption(f"Connected as {garmin_conn.get('garmin_email','')}")
                    if st.button("Push This Week to Garmin", type="primary",
                                 key="push_garmin_week", use_container_width=True):
                        from services.garmin_workout_service import push_week_to_garmin
                        result = push_week_to_garmin(user_id, week_workouts, ftp_g)
                        for detail in result["details"]:
                            if detail["success"]:
                                st.toast(f"✓ {detail['workout_name']} pushed")
                            else:
                                st.toast(f"✗ {detail['workout_name']}: {detail['message']}")
                        if result["pushed"] > 0:
                            st.success(f"Pushed {result['pushed']} workout(s) to Garmin Connect")
                        if result["failed"] > 0:
                            st.error(f"{result['failed']} workout(s) failed — check connection")
                elif garmin_conn:
                    st.caption(f"Email: {garmin_conn.get('garmin_email','')}")
                    st.info("Session expired — re-login on the Garmin Import page to push workouts.")
                else:
                    st.info("Connect Garmin in Settings or the Garmin Import page first.")

            with col_tcx:
                tcx_hdr_html = (
                    f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]};'
                    f'margin-bottom:8px">Download for TrainingPeaks</div>'
                )
                st.markdown(tcx_hdr_html, unsafe_allow_html=True)
                profile_t = get_cycling_profile(user_id)
                ftp_t = profile_t["ftp_watts"] if profile_t else 200
                if week_workouts:
                    try:
                        from services.garmin_workout_service import generate_tcx_plan
                        tcx_bytes = generate_tcx_plan(
                            week_workouts, ftp_t,
                            {"phase": active_plan.get("phase", ""), "week": current_week_num},
                        )
                        tcx_filename = f"cycling_week{current_week_num}_{date.today().isoformat()}.tcx"
                        st.download_button(
                            label="Download Week TCX",
                            data=tcx_bytes,
                            file_name=tcx_filename,
                            mime="application/vnd.garmin.tcx+xml",
                            use_container_width=True,
                        )
                        st.caption("Compatible with TrainingPeaks, Garmin Connect, and most training apps.")
                    except Exception as tcx_err:
                        st.error(f"TCX generation failed: {tcx_err}")
                else:
                    st.caption("No workouts scheduled this week.")

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
                np_val = norm_power if norm_power > 0 else None
                power_for_if = np_val if np_val else avg_power
                if_score = calculate_if(power_for_if, ftp)
                tss = calculate_tss(duration_min, avg_power, ftp, np_watts=np_val)
                ride_data = {
                    "ride_date": ride_date.isoformat(),
                    "duration_min": duration_min,
                    "avg_power": avg_power,
                    "normalized_power": np_val,
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
                np_label = f" · NP: {np_val}W" if np_val else ""
                st.toast(f"Ride saved! TSS: {tss:.0f} · IF: {if_score:.3f}{np_label}")
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
# Tab 5: Analytics
# ══════════════════════════════════════════════════════════════════════════
with tab_analytics:
    profile_a = get_cycling_profile(user_id)
    ftp_a = profile_a["ftp_watts"] if profile_a else 200
    weight_a = profile_a.get("weight_kg") if profile_a else None

    # ── W/kg Display ──────────────────────────────────────────────────────
    render_section_header("Power-to-Weight Ratio")
    if profile_a and weight_a and weight_a > 0:
        wkg_val_a = get_wkg(ftp_a, weight_a)
        cat_a = get_wkg_category(ftp_a, weight_a)
        cat_color_a = A["blue"]
        for c_item in WATT_KG_CATEGORIES:
            if c_item["label"] == cat_a:
                cat_color_a = c_item["color"]
                break
        wkg_display_html = (
            f'<div style="display:flex;gap:24px;align-items:center;margin-bottom:16px">'
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:18px 28px;text-align:center">'
            f'<div style="font-size:36px;font-weight:800;color:{cat_color_a}">{wkg_val_a:.2f}</div>'
            f'<div style="font-size:12px;color:{A["label_tertiary"]}">W / kg</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:16px;font-weight:700;color:{cat_color_a}">{cat_a}</div>'
            f'<div style="font-size:12px;color:{A["label_secondary"]};margin-top:4px">'
            f'FTP {ftp_a}W &middot; {weight_a}kg</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:6px;line-height:16px">'
            f'W/kg is the single most important metric for comparing cycling ability. '
            f'Higher W/kg = better climbing and sustained performance.</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(wkg_display_html, unsafe_allow_html=True)

        # W/kg scale bar
        scale_items_html = ""
        for c_item in WATT_KG_CATEGORIES:
            is_active = c_item["label"] == cat_a
            opacity = "1.0" if is_active else "0.5"
            border = f"2px solid {c_item['color']}" if is_active else f"1px solid {A['separator']}"
            scale_items_html += (
                f'<div style="flex:1;background:{c_item["color"]}15;border:{border};'
                f'border-radius:{A["radius_sm"]};padding:6px 4px;text-align:center;opacity:{opacity}">'
                f'<div style="font-size:10px;font-weight:700;color:{c_item["color"]}">'
                f'{c_item["min_wkg"]}–{c_item["max_wkg"] if c_item["max_wkg"] < 90 else "+"}</div>'
                f'<div style="font-size:9px;color:{A["label_tertiary"]}">{c_item["label"]}</div>'
                f'</div>'
            )
        scale_html = (
            f'<div style="display:flex;gap:4px;margin-bottom:16px">'
            f'{scale_items_html}'
            f'</div>'
        )
        st.markdown(scale_html, unsafe_allow_html=True)
    else:
        st.info("Set your FTP and body weight in Settings to see your W/kg ratio.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Power Curve Chart ─────────────────────────────────────────────────
    render_section_header("Power Curve", "Best power at standard durations (estimated from ride logs)")
    curve_data = get_power_curve_data(user_id)
    if curve_data:
        labels = [d["label"] for d in curve_data]
        watts = [d["watts"] for d in curve_data]
        seconds = [d["duration_s"] for d in curve_data]

        fig_pc = go.Figure()
        fig_pc.add_trace(go.Scatter(
            x=labels, y=watts,
            mode="lines+markers",
            name="Best Power",
            line=dict(color=A["blue"], width=3),
            marker=dict(size=10, color=A["blue"], line=dict(width=2, color=A["bg_elevated"])),
            hovertemplate="%{x}<br><b>%{y}W</b><extra></extra>",
        ))

        # Add zone reference lines if FTP is available
        if ftp_a:
            fig_pc.add_hline(
                y=ftp_a, line_dash="dash", line_color=A["orange"], line_width=1.5,
                annotation_text=f"FTP {ftp_a}W", annotation_position="top right",
                annotation_font=dict(size=10, color=A["orange"]),
            )

        fig_pc.update_layout(
            height=340,
            plot_bgcolor=A["chart_bg"],
            paper_bgcolor=A["chart_bg"],
            font=dict(family=A["font_text"], color=A["chart_text"], size=11),
            legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5),
            margin=dict(t=20, b=70, l=50, r=30),
            xaxis=dict(
                title="Duration",
                gridcolor=A["chart_grid"],
                showgrid=True,
            ),
            yaxis=dict(
                title="Watts",
                gridcolor=A["chart_grid"],
                zeroline=False,
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig_pc, use_container_width=True)

        # Power bests table
        bests_a = get_power_bests(user_id, days=90)
        if bests_a:
            bests_cells_html = ""
            for label_b, info_b in bests_a.items():
                bests_cells_html += (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_md"]};padding:12px;text-align:center">'
                    f'<div style="font-size:20px;font-weight:800;color:{A["blue"]}">{info_b["watts"]}W</div>'
                    f'<div style="font-size:11px;color:{A["label_tertiary"]}">{label_b}</div>'
                    f'</div>'
                )
            bests_html = (
                f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:8px">'
                f'{bests_cells_html}'
                f'</div>'
            )
            st.markdown(bests_html, unsafe_allow_html=True)
    else:
        st.caption("Log some rides with power data to see your power curve.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── FTP Test Calculator ───────────────────────────────────────────────
    render_section_header("FTP Test Calculator", "Estimate your FTP from a structured test protocol")

    ftp_test_info_html = (
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_md"]};'
        f'padding:12px;margin-bottom:12px">'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};line-height:17px">'
        f'FTP (Functional Threshold Power) is the maximum power you can sustain for ~1 hour. '
        f'It sets all your training zones. Choose a test protocol below and enter your result to '
        f'estimate your FTP. The 20-minute test is the gold standard.</div>'
        f'</div>'
    )
    st.markdown(ftp_test_info_html, unsafe_allow_html=True)

    with st.form("ftp_test_form"):
        test_type_labels = {
            "20min": "20-Minute Test (FTP = avg power × 0.95)",
            "8min": "8-Minute Test (FTP = avg power × 0.90)",
            "ramp": "Ramp Test (FTP = peak 1-min power × 0.75)",
        }
        test_choice = st.selectbox(
            "Test Protocol", list(test_type_labels.values()), key="ftp_test_type"
        )
        test_key = [k for k, v in test_type_labels.items() if v == test_choice][0]

        col_test_1, col_test_2 = st.columns(2)
        with col_test_1:
            if test_key == "20min":
                test_power = st.number_input(
                    "Average Power over 20 min (W)", min_value=0, max_value=1000, value=0,
                    key="ftp_test_power_20"
                )
            elif test_key == "8min":
                test_power = st.number_input(
                    "Average Power over 8 min (W)", min_value=0, max_value=1000, value=0,
                    key="ftp_test_power_8"
                )
            else:
                test_power = st.number_input(
                    "Peak 1-Minute Power from Ramp (W)", min_value=0, max_value=1500, value=0,
                    key="ftp_test_power_ramp"
                )
        with col_test_2:
            st.markdown(
                f'<div style="font-size:12px;color:{A["label_secondary"]};padding-top:28px">'
                f'Enter the power value from your test effort. '
                f'The calculator will apply the standard multiplier.</div>',
                unsafe_allow_html=True,
            )

        ftp_test_submitted = st.form_submit_button(
            "Calculate FTP", type="primary", use_container_width=True
        )
        if ftp_test_submitted and test_power > 0:
            result = calculate_ftp_from_test(
                test_key,
                power_20min=test_power if test_key == "20min" else None,
                power_8min=test_power if test_key == "8min" else None,
                ramp_max=test_power if test_key == "ramp" else None,
            )
            if result["ftp"] > 0:
                conf_color = A["green"] if result["confidence"] == "high" else A["orange"]
                result_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-left:4px solid {conf_color};'
                    f'border-radius:0 {A["radius_md"]} {A["radius_md"]} 0;padding:14px;margin-top:8px">'
                    f'<div style="display:flex;align-items:center;gap:16px">'
                    f'<div style="text-align:center">'
                    f'<div style="font-size:32px;font-weight:800;color:{A["blue"]}">{result["ftp"]}W</div>'
                    f'<div style="font-size:11px;color:{A["label_tertiary"]}">Estimated FTP</div>'
                    f'</div>'
                    f'<div>'
                    f'<div style="font-size:12px;font-weight:600;color:{conf_color}">'
                    f'{result["test_type"]} &middot; Confidence: {result["confidence"].title()}</div>'
                    f'<div style="font-size:11px;color:{A["label_secondary"]};margin-top:4px;'
                    f'line-height:16px">{result["notes"]}</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(result_html, unsafe_allow_html=True)
            else:
                st.warning(result["notes"])

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Normalized Power Explanation ──────────────────────────────────────
    render_section_header("About Normalized Power (NP)")
    np_explain_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px">'
        f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]};margin-bottom:8px">'
        f'Why NP matters more than Average Power</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px;margin-bottom:10px">'
        f'Average power understates the physiological cost of variable-intensity riding. '
        f'A ride with lots of surges (attacks, hills, wind) is harder than steady endurance '
        f'at the same average — NP captures this difference.</div>'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]};margin-bottom:6px">'
        f'How it works</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px;margin-bottom:10px">'
        f'NP uses a 30-second rolling average of power, raised to the 4th power, averaged, '
        f'then taken to the &frac14; root. This emphasizes high-power surges that cost more '
        f'metabolically (Coggan, 2003).</div>'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_primary"]};margin-bottom:6px">'
        f'Variability Index (VI)</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px;margin-bottom:10px">'
        f'VI = NP / Average Power. Tells you how variable the ride was:</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">'
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_sm"]};padding:8px;text-align:center">'
        f'<div style="font-size:14px;font-weight:700;color:{A["green"]}">1.02–1.06</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">Steady / TT</div>'
        f'</div>'
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_sm"]};padding:8px;text-align:center">'
        f'<div style="font-size:14px;font-weight:700;color:{A["orange"]}">1.06–1.13</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">Group Ride</div>'
        f'</div>'
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_sm"]};padding:8px;text-align:center">'
        f'<div style="font-size:14px;font-weight:700;color:{A["red"]}">1.13–1.25</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">Crit / Intervals</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:10px;line-height:16px">'
        f'When you log a ride with NP, TSS is calculated using NP instead of average power '
        f'for a more accurate training load estimate. If NP is not available, we estimate it '
        f'using a default variability index of 1.05.</div>'
        f'</div>'
    )
    st.markdown(np_explain_html, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── NP Estimator (quick tool) ─────────────────────────────────────────
    with st.expander("NP Estimator", expanded=False):
        col_np_1, col_np_2 = st.columns(2)
        with col_np_1:
            np_avg = st.number_input(
                "Average Power (W)", min_value=0, max_value=1000, value=200, key="np_est_avg"
            )
        with col_np_2:
            np_vi = st.number_input(
                "Variability Index", min_value=1.00, max_value=1.50, value=1.05,
                step=0.01, format="%.2f", key="np_est_vi",
                help="1.02–1.06 for steady rides, 1.06–1.13 for group rides, 1.13–1.25 for crits"
            )
        if np_avg > 0:
            np_result = estimate_np(np_avg, variability_index=np_vi)
            np_est_html = (
                f'<div style="display:flex;gap:20px;padding:10px;'
                f'background:{A["bg_secondary"]};border-radius:{A["radius_md"]};margin-top:8px">'
                f'<div><div style="font-size:20px;font-weight:800;color:{A["blue"]}">{np_result:.0f}W</div>'
                f'<div style="font-size:10px;color:{A["label_tertiary"]}">Estimated NP</div></div>'
                f'<div><div style="font-size:20px;font-weight:800;color:{A["orange"]}">{np_vi:.2f}</div>'
                f'<div style="font-size:10px;color:{A["label_tertiary"]}">Variability Index</div></div>'
                f'</div>'
            )
            st.markdown(np_est_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 6: Settings
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

# ══════════════════════════════════════════════════════════════════════════
# Tab 7: AI Coach
# ══════════════════════════════════════════════════════════════════════════
with tab_coach:
    from services.coaching_service import get_cycling_coaching_response

    render_section_header("AI Cycling Coach", "Power-based coaching from your live training data")

    profile_c = get_cycling_profile(user_id)

    if not profile_c:
        st.info("Set your FTP in the Settings tab first to enable personalised AI coaching.")
        st.stop()

    ftp_c = profile_c["ftp_watts"]
    pmc_c = get_pmc_data(user_id, days=7)
    ctl_c = pmc_c[-1]["ctl"] if pmc_c else 0.0
    atl_c = pmc_c[-1]["atl"] if pmc_c else 0.0
    tsb_c = pmc_c[-1]["tsb"] if pmc_c else 0.0

    # CTL 7-day trend
    pmc_c90 = get_pmc_data(user_id, days=90)
    ctl_trend_label = ""
    if len(pmc_c90) >= 8:
        ctl_trend_val = ctl_c - pmc_c90[-8]["ctl"]
        ctl_trend_label = f" ({ctl_trend_val:+.1f} 7d)"

    tsb_color_c = A["green"] if tsb_c >= 0 else (A["orange"] if tsb_c >= -20 else A["red"])

    # Last ride for the context card
    recent_rides_c = get_ride_history(user_id, days=7)
    last_ride_c = recent_rides_c[0] if recent_rides_c else None
    if last_ride_c:
        last_ride_text_c = (
            f"{last_ride_c['ride_date']} &middot; {last_ride_c['duration_min']}min"
            f" &middot; {last_ride_c.get('tss', 0):.0f} TSS"
        )
    else:
        last_ride_text_c = "No rides this week"

    # ── Context cards ──────────────────────────────────────────────────────
    cards_c_html = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px">'
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-top:3px solid {A["blue"]};border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-size:22px;font-weight:800;color:{A["blue"]}">{ctl_c:.0f}</div>'
        f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">CTL Fitness{ctl_trend_label}</div>'
        f'</div>'
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-top:3px solid {tsb_color_c};border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-size:22px;font-weight:800;color:{tsb_color_c}">{tsb_c:+.0f}</div>'
        f'<div style="font-size:10px;font-weight:600;color:{A["label_tertiary"]}">TSB Form</div>'
        f'</div>'
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-top:3px solid {A["orange"]};border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-size:11px;font-weight:600;color:{A["label_secondary"]};margin-bottom:4px">Last 7 Days</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">{last_ride_text_c}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(cards_c_html, unsafe_allow_html=True)

    # ── Quick-action buttons ───────────────────────────────────────────────
    _QUICK_ACTIONS = {
        "qa_7days": "Evaluate my training over the last 7 days and tell me how I'm progressing. Reference my CTL trend, TSB, and any ride difficulty surveys.",
        "qa_ftp":   "Based on my current CTL trend and how long it has been since my last FTP test, should I retest my FTP now? Give me specific criteria.",
        "qa_today": "What should I train today? Consider my TSB form value and which energy system progression level is lowest.",
        "qa_week":  "Plan my next 7 days of training — list specific workout names with target watts, duration, and estimated TSS per session.",
    }
    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    with qa_col1:
        if st.button("Evaluate last 7 days", key="qa_7days", use_container_width=True):
            st.session_state["cycling_coach_prefill"] = _QUICK_ACTIONS["qa_7days"]
            st.rerun()
    with qa_col2:
        if st.button("Should I raise FTP?", key="qa_ftp", use_container_width=True):
            st.session_state["cycling_coach_prefill"] = _QUICK_ACTIONS["qa_ftp"]
            st.rerun()
    with qa_col3:
        if st.button("What to train today?", key="qa_today", use_container_width=True):
            st.session_state["cycling_coach_prefill"] = _QUICK_ACTIONS["qa_today"]
            st.rerun()
    with qa_col4:
        if st.button("Plan next week", key="qa_week", use_container_width=True):
            st.session_state["cycling_coach_prefill"] = _QUICK_ACTIONS["qa_week"]
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Chat input (NOT inside st.form — required for prefill to work) ─────
    prefill_c = st.session_state.pop("cycling_coach_prefill", "")
    user_input_c = st.text_area(
        "Ask your cycling coach",
        value=prefill_c,
        placeholder="e.g. 'My last 3 rides felt very hard — am I overtraining?'",
        height=90,
        key="cycling_coach_input",
        label_visibility="collapsed",
    )

    if st.button("Ask Coach", type="primary", key="cycling_coach_submit"):
        if user_input_c.strip():
            if "cycling_chat_history" not in st.session_state:
                st.session_state["cycling_chat_history"] = []
            with st.spinner("Analysing your training data…"):
                ai_resp_c = get_cycling_coaching_response(user_id, user_input_c.strip())
            st.session_state["cycling_chat_history"].append(
                {"user": user_input_c.strip(), "assistant": ai_resp_c}
            )
            # Keep only last 3 exchanges
            if len(st.session_state["cycling_chat_history"]) > 3:
                st.session_state["cycling_chat_history"] = st.session_state["cycling_chat_history"][-3:]
            st.rerun()
        else:
            st.warning("Please enter a question.")

    # ── Response display (newest first) ───────────────────────────────────
    chat_history_c = st.session_state.get("cycling_chat_history", [])
    if chat_history_c:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_section_header("Coaching Responses")
        for exchange in reversed(chat_history_c):
            user_bubble_html = (
                f'<div style="background:{A["bg_secondary"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:6px">'
                f'<div style="font-size:11px;font-weight:700;color:{A["blue"]};margin-bottom:4px">You</div>'
                f'<div style="font-size:13px;color:{A["label_primary"]}">{exchange["user"]}</div>'
                f'</div>'
            )
            st.markdown(user_bubble_html, unsafe_allow_html=True)
            # Use st.container so the AI markdown (bullets, bold) renders correctly
            with st.container(border=True):
                st.caption("AI Coach")
                st.markdown(exchange["assistant"])
