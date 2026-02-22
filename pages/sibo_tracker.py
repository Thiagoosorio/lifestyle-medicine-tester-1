"""SIBO & FODMAP Tracker — Symptom logging, food diary, phases, correlations, evidence."""

import streamlit as st
import json
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.sibo_display import (
    render_sibo_disclaimer,
    render_symptom_summary,
    render_symptom_chart,
    render_fodmap_badge,
    render_food_log_row,
    render_fodmap_exposure_bar,
    render_phase_indicator,
    render_tolerance_summary,
    render_reintro_timeline,
    render_correlation_disclaimer,
    render_correlation_table,
    render_evidence_coverage_box,
    render_diet_confidence_table,
)
from components.evidence_display import render_evidence_card
from config.sibo_data import (
    GI_SYMPTOMS, FODMAP_GROUPS, FODMAP_FOODS, FODMAP_FOOD_CATEGORIES,
    FODMAP_PHASES, SIBO_EVIDENCE,
)
from services.sibo_service import (
    log_symptoms, get_symptom_log, get_symptom_history, get_symptom_averages,
    log_fodmap_food, get_food_log, get_food_history, search_fodmap_foods,
    get_daily_fodmap_exposure,
    start_fodmap_phase, get_current_phase, end_fodmap_phase, is_in_washout,
    start_reintro_challenge, log_challenge_day, complete_challenge,
    get_active_challenge, get_challenge_history, get_tolerance_summary as svc_tolerance_summary,
    compute_correlations,
    get_or_create_state,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "SIBO & FODMAP Tracker",
    "Track GI symptoms and FODMAP intake patterns. This is a personal tracking tool, not a diagnostic device."
)

tab_symptoms, tab_food, tab_phases, tab_correlations, tab_science = st.tabs([
    "Symptoms", "Food Diary", "FODMAP Phases", "Correlations", "Evidence & Safety"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Symptoms
# ══════════════════════════════════════════════════════════════════════════
with tab_symptoms:
    render_sibo_disclaimer()
    render_section_header("Daily GI Symptoms", "Track your symptoms to identify patterns over time")

    today_str = date.today().isoformat()
    existing_log = get_symptom_log(user_id, today_str)

    with st.form("sibo_symptom_form", clear_on_submit=False):
        st.markdown(
            f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-bottom:8px">'
            f'Rate your symptoms for today. All scales are 0 (none) to max.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            bloating = st.slider("Bloating (0-10)", 0, 10,
                                 value=existing_log["bloating"] if existing_log and existing_log["bloating"] is not None else 0)
            abdominal_pain = st.slider("Abdominal Pain (0-10)", 0, 10,
                                       value=existing_log["abdominal_pain"] if existing_log and existing_log["abdominal_pain"] is not None else 0)
            gas = st.slider("Gas / Flatulence (0-10)", 0, 10,
                            value=existing_log["gas"] if existing_log and existing_log["gas"] is not None else 0)
            nausea = st.slider("Nausea (0-10)", 0, 10,
                               value=existing_log["nausea"] if existing_log and existing_log["nausea"] is not None else 0)
        with col2:
            diarrhea = st.slider("Diarrhea (0=none, 3=severe)", 0, 3,
                                 value=existing_log["diarrhea"] if existing_log and existing_log["diarrhea"] is not None else 0)
            constipation = st.slider("Constipation (0=none, 3=severe)", 0, 3,
                                     value=existing_log["constipation"] if existing_log and existing_log["constipation"] is not None else 0)
            fatigue = st.slider("Fatigue (0-10)", 0, 10,
                                value=existing_log["fatigue"] if existing_log and existing_log["fatigue"] is not None else 0)

        notes = st.text_input("Notes (optional)", value=existing_log["notes"] if existing_log and existing_log.get("notes") else "",
                              placeholder="e.g., ate late last night, stressful day")

        submitted = st.form_submit_button("Save Symptoms", use_container_width=True, type="primary")
        if submitted:
            symptoms = {
                "bloating": bloating, "abdominal_pain": abdominal_pain,
                "gas": gas, "diarrhea": diarrhea, "constipation": constipation,
                "nausea": nausea, "fatigue": fatigue,
            }
            log_symptoms(user_id, today_str, symptoms, notes if notes else None)
            st.toast("Symptoms saved!")
            st.rerun()

    # 7-day summary
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    render_section_header("Last 7 Days", "Average symptom scores")
    avg_7d = get_symptom_averages(user_id, days=7)
    render_symptom_summary(avg_7d)

    # 30-day chart
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_section_header("30-Day Trend")
    history = get_symptom_history(user_id, days=30)
    render_symptom_chart(history)


# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Food Diary
# ══════════════════════════════════════════════════════════════════════════
with tab_food:
    render_sibo_disclaimer()
    render_section_header("FODMAP Food Diary", "Log foods with FODMAP categories")

    # Build food options for selectbox
    food_names = [f[0] for f in FODMAP_FOODS]

    with st.form("sibo_food_form", clear_on_submit=True):
        col_food, col_meal = st.columns([2, 1])
        with col_food:
            entry_mode = st.radio("Entry mode", ["Database", "Manual"], horizontal=True, label_visibility="collapsed")
        with col_meal:
            meal_type = st.selectbox("Meal", ["breakfast", "lunch", "dinner", "snack"])

        if entry_mode == "Database":
            selected_food = st.selectbox("Search food", food_names, index=None,
                                         placeholder="Type to search FODMAP foods...")
            manual_name = None
            manual_rating = None
            manual_groups = None
        else:
            selected_food = None
            manual_name = st.text_input("Food name", placeholder="e.g., Homemade granola")
            manual_rating = st.selectbox("FODMAP rating", ["low", "moderate", "high", "unknown"])
            manual_groups = st.multiselect("FODMAP groups (if known)", list(FODMAP_GROUPS.keys()),
                                           format_func=lambda g: FODMAP_GROUPS[g]["label"])

        food_notes = st.text_input("Notes (optional)", placeholder="e.g., large portion, spicy")

        food_submitted = st.form_submit_button("Log Food", use_container_width=True, type="primary")
        if food_submitted:
            if entry_mode == "Database" and selected_food:
                # Look up food data
                match = next((f for f in FODMAP_FOODS if f[0] == selected_food), None)
                if match:
                    name, cat, srv_size, srv_unit, rating, groups_json, alt = match
                    try:
                        groups = json.loads(groups_json)
                    except (json.JSONDecodeError, TypeError):
                        groups = []
                    log_fodmap_food(user_id, today_str, meal_type, name,
                                   food_category=cat, serving_size=srv_size,
                                   serving_unit=srv_unit, fodmap_rating=rating,
                                   fodmap_groups=groups, notes=food_notes if food_notes else None)
                    badge_text = f" ({rating} FODMAP)" if rating != "low" else ""
                    st.toast(f"Logged: {name}{badge_text}")
                    st.rerun()
            elif entry_mode == "Manual" and manual_name:
                groups = manual_groups if manual_groups else []
                rating = manual_rating if manual_rating != "unknown" else None
                log_fodmap_food(user_id, today_str, meal_type, manual_name,
                               fodmap_rating=rating, fodmap_groups=groups,
                               notes=food_notes if food_notes else None)
                st.toast(f"Logged: {manual_name}")
                st.rerun()
            else:
                st.warning("Please select or enter a food.")

    # Today's food log
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    render_section_header("Today's Log")
    today_foods = get_food_log(user_id, today_str)
    if today_foods:
        for entry in today_foods:
            render_food_log_row(entry)
    else:
        st.caption("No foods logged today.")

    # Daily FODMAP exposure
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    exposure = get_daily_fodmap_exposure(user_id, today_str)
    render_fodmap_exposure_bar(exposure)


# ══════════════════════════════════════════════════════════════════════════
# Tab 3: FODMAP Phases
# ══════════════════════════════════════════════════════════════════════════
with tab_phases:
    render_sibo_disclaimer()
    render_section_header("Low-FODMAP Protocol", "3-phase approach: Elimination, Reintroduction, Personalization")

    current_phase = get_current_phase(user_id)
    render_phase_indicator(current_phase)

    # Phase guidance
    if current_phase:
        phase_key = current_phase["phase"]
        phase_info = FODMAP_PHASES.get(phase_key, {})
        guidance_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
            f'<div style="font-size:12px;line-height:18px;color:{A["label_secondary"]}">'
            f'{phase_info.get("guidance", "")}</div>'
            f'</div>'
        )
        st.markdown(guidance_html, unsafe_allow_html=True)

    # Phase controls
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if not current_phase:
        render_section_header("Start a Phase")
        col_phase, col_start = st.columns([3, 1])
        with col_phase:
            phase_options = {v["label"]: k for k, v in FODMAP_PHASES.items()}
            selected_phase_label = st.selectbox("Select Phase", list(phase_options.keys()))
            selected_phase = phase_options[selected_phase_label]
        with col_start:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("Start Phase", use_container_width=True, type="primary"):
                start_fodmap_phase(user_id, selected_phase)
                st.toast(f"Started {selected_phase_label} phase!")
                st.rerun()
    else:
        if st.button("End Current Phase", use_container_width=True):
            end_fodmap_phase(user_id)
            st.toast("Phase ended.")
            st.rerun()

    # ── Reintroduction Section ──
    if current_phase and current_phase["phase"] == "reintroduction":
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        render_section_header("Reintroduction Challenges", "Test one FODMAP group at a time (3 days + 3-day washout)")

        washout = is_in_washout(user_id)
        active_challenge = get_active_challenge(user_id)

        if washout["in_washout"] and not active_challenge:
            washout_html = (
                f'<div style="background:rgba(255,159,10,0.08);border:1px solid rgba(255,159,10,0.3);'
                f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
                f'<div style="font-size:13px;color:{A["orange"]}">'
                f'&#9202; <strong>Washout Period</strong> — Return to low-FODMAP foods until '
                f'{washout["washout_end"]}. This ensures accurate results for the next challenge.</div>'
                f'</div>'
            )
            st.markdown(washout_html, unsafe_allow_html=True)

        elif active_challenge:
            # Show active challenge card
            ginfo = FODMAP_GROUPS.get(active_challenge["fodmap_group"], {})
            start_dt = date.fromisoformat(active_challenge["start_date"])
            day_num = (date.today() - start_dt).days + 1
            day_num = min(day_num, 3)

            challenge_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:4px solid {ginfo.get("color", A["teal"])};'
                f'border-radius:{A["radius_lg"]};padding:16px 20px;margin-bottom:12px">'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.05em;color:{ginfo.get("color", A["teal"])};margin-bottom:4px">'
                f'Active Challenge — Day {day_num}/3</div>'
                f'<div style="font-family:{A["font_display"]};font-size:18px;font-weight:700;'
                f'color:{A["label_primary"]}">{ginfo.get("label", active_challenge["fodmap_group"])}</div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-top:2px">'
                f'Food: {active_challenge["challenge_food"]} &middot; Started: {active_challenge["start_date"]}</div>'
                f'</div>'
            )
            st.markdown(challenge_html, unsafe_allow_html=True)

            # Log challenge day symptoms
            with st.form("challenge_day_form"):
                st.markdown(f"**Day {day_num} Symptoms**")
                ch_bloating = st.slider("Bloating", 0, 10, 0, key="ch_bloat")
                ch_pain = st.slider("Pain", 0, 10, 0, key="ch_pain")
                ch_gas = st.slider("Gas", 0, 10, 0, key="ch_gas")

                if st.form_submit_button(f"Save Day {day_num}", use_container_width=True):
                    symptoms = {"bloating": ch_bloating, "abdominal_pain": ch_pain, "gas": ch_gas}
                    log_challenge_day(user_id, active_challenge["id"], day_num, symptoms)
                    st.toast(f"Day {day_num} symptoms saved!")
                    st.rerun()

            # Complete challenge
            if day_num >= 3:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                tol_result = st.selectbox("Tolerance result", ["tolerated", "partial", "not_tolerated"],
                                          format_func=lambda x: x.replace("_", " ").title())
                if st.button("Complete Challenge", use_container_width=True, type="primary"):
                    complete_challenge(user_id, active_challenge["id"], tol_result)
                    st.toast(f"Challenge completed: {tol_result.replace('_', ' ')}")
                    st.rerun()

        else:
            # Start a new challenge
            with st.form("start_challenge_form"):
                col_grp, col_fd = st.columns(2)
                with col_grp:
                    group_options = {v["label"]: k for k, v in FODMAP_GROUPS.items()}
                    selected_group_label = st.selectbox("FODMAP Group", list(group_options.keys()))
                    selected_group = group_options[selected_group_label]
                with col_fd:
                    challenge_food = st.text_input("Challenge Food",
                                                   placeholder=f"e.g., {FODMAP_GROUPS[selected_group]['examples'].split(',')[0].strip()}")

                if st.form_submit_button("Start 3-Day Challenge", use_container_width=True, type="primary"):
                    if challenge_food:
                        cid = start_reintro_challenge(user_id, selected_group, challenge_food)
                        if cid:
                            st.toast(f"Challenge started: {selected_group_label} ({challenge_food})")
                            st.rerun()
                        else:
                            st.warning("Cannot start — still in washout period.")
                    else:
                        st.warning("Enter a challenge food.")

    # Tolerance results
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Tolerance Results")
    tolerance = svc_tolerance_summary(user_id)
    render_tolerance_summary(tolerance)

    # Challenge timeline
    challenges = get_challenge_history(user_id)
    render_reintro_timeline(challenges)


# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Correlations
# ══════════════════════════════════════════════════════════════════════════
with tab_correlations:
    render_sibo_disclaimer()
    render_correlation_disclaimer()
    render_section_header("FODMAP-Symptom Correlations", "Spearman rank correlations between food groups and symptoms")

    state = get_or_create_state(user_id)
    sym_count = state.get("total_symptom_logs", 0) if state else 0
    food_count = state.get("total_food_logs", 0) if state else 0

    if sym_count < 10 or food_count < 10:
        gate_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:16px;text-align:center;margin-bottom:12px">'
            f'<div style="font-size:14px;color:{A["label_secondary"]};margin-bottom:8px">'
            f'Log at least 10 days of both symptoms and food to see correlations.</div>'
            f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
            f'Symptom logs: {sym_count}/10 &middot; Food logs: {food_count}/10</div>'
            f'</div>'
        )
        st.markdown(gate_html, unsafe_allow_html=True)
    else:
        correlations = compute_correlations(user_id, days=90)
        render_correlation_table(correlations)

        # Interpretation guide
        with st.expander("How to interpret correlations"):
            interp_html = (
                f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:20px">'
                f'<strong>Spearman Rank Correlation (rho)</strong> measures the strength and direction '
                f'of association between your FODMAP group intake and symptom scores.<br><br>'
                f'<strong>Positive rho (+):</strong> Higher intake of this FODMAP group is associated with higher symptom scores.<br>'
                f'<strong>Negative rho (-):</strong> Higher intake is associated with lower symptom scores (uncommon).<br><br>'
                f'<strong>Strength guide:</strong><br>'
                f'&middot; 0.0 - 0.1: Negligible<br>'
                f'&middot; 0.1 - 0.3: Weak<br>'
                f'&middot; 0.3 - 0.5: Moderate — worth noting<br>'
                f'&middot; 0.5 - 0.7: Strong — discuss with your provider<br>'
                f'&middot; 0.7 - 1.0: Very Strong — likely a significant pattern<br><br>'
                f'<strong>p-value:</strong> Lower p-values (e.g., p&lt;0.05) suggest the correlation is '
                f'unlikely to be due to chance. However, with multiple comparisons, some false positives '
                f'are expected.<br><br>'
                f'<strong>n:</strong> The number of days with both food and symptom data. '
                f'Minimum 10 days required. More data = more reliable results.'
                f'</div>'
            )
            st.markdown(interp_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# Tab 5: Evidence & Safety
# ══════════════════════════════════════════════════════════════════════════
with tab_science:
    render_sibo_disclaimer()
    render_section_header("Scientific Evidence", "PubMed-verified references (Tier A & B only)")

    for ev in SIBO_EVIDENCE:
        render_evidence_card(ev)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_evidence_coverage_box()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    render_section_header("Dietary Approaches")
    render_diet_confidence_table()
