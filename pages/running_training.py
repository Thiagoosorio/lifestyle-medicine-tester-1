"""Running Training — VDOT pace zones, race predictor, training load, training plans."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from config.running_data import RACE_DISTANCES, PACE_ZONE_DEFINITIONS
from services.running_service import (
    estimate_vdot,
    get_pace_zones,
    predict_race_times,
    get_running_stats,
    get_running_history,
    calculate_training_load,
    get_training_plan,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Running Training",
    "Pace zones, race predictions, training load monitoring, and structured training plans."
)

tab_dashboard, tab_zones, tab_predictor, tab_load, tab_plan = st.tabs([
    "Dashboard", "Pace Zones", "Race Predictor", "Training Load", "Training Plan"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    stats_30 = get_running_stats(user_id, days=30)

    if stats_30["total_runs"] == 0:
        st.info("No running data yet. Log runs in the **Exercise Tracker** or import from Strava to see your running dashboard.")
    else:
        # Key metrics strip
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Weekly Avg</div>'
                f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                f'color:{A["label_primary"]}">{stats_30["weekly_avg_km"]}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">km/week</div></div>'
            )
            st.markdown(metric_html, unsafe_allow_html=True)
        with c2:
            metric_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Avg Pace</div>'
                f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                f'color:{A["label_primary"]}">{stats_30["avg_pace_fmt"]}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">min/km</div></div>'
            )
            st.markdown(metric_html, unsafe_allow_html=True)
        with c3:
            metric_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Total Runs</div>'
                f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                f'color:{A["label_primary"]}">{stats_30["total_runs"]}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">last 30 days</div></div>'
            )
            st.markdown(metric_html, unsafe_allow_html=True)
        with c4:
            metric_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Longest Run</div>'
                f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                f'color:{A["label_primary"]}">{stats_30["longest_run_km"]}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">km</div></div>'
            )
            st.markdown(metric_html, unsafe_allow_html=True)

        # Weekly mileage chart
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        render_section_header("Weekly Mileage", "Last 12 weeks")

        history = get_running_history(user_id, days=84)
        if history:
            from collections import defaultdict
            from datetime import timedelta as td
            weekly_km = defaultdict(float)
            for r in history:
                d = date.fromisoformat(r["exercise_date"])
                week_start = (d - td(days=d.weekday())).isoformat()
                weekly_km[week_start] += r.get("distance_km") or 0.0

            if weekly_km:
                weeks_sorted = sorted(weekly_km.keys())
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=weeks_sorted,
                    y=[round(weekly_km[w], 1) for w in weeks_sorted],
                    marker_color="#1A73E8",
                    marker_line_width=0,
                    opacity=0.85,
                    hovertemplate="%{y} km<br>Week of %{x}<extra></extra>",
                ))
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor=A["chart_bg"],
                    font=dict(family=A["font_text"], color=A["chart_text"]),
                    margin=dict(l=40, r=20, t=20, b=40),
                    height=300,
                    xaxis=dict(gridcolor=A["chart_grid"]),
                    yaxis=dict(title="km", gridcolor=A["chart_grid"]),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        # Recent runs list
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        render_section_header("Recent Runs", "Last 10 runs")
        recent = get_running_history(user_id, days=60)[:10]
        for r in recent:
            dist = r.get("distance_km") or 0
            dur = r.get("duration_min") or 0
            pace_fmt = "—"
            if dist and dist > 0 and dur > 0:
                pace = dur / dist
                mins = int(pace)
                secs = int(round((pace - mins) * 60))
                pace_fmt = f"{mins}:{secs:02d}"
            intensity = r.get("intensity", "moderate")
            int_color = {"light": "#30D158", "moderate": "#FFD60A", "vigorous": "#FF453A"}.get(intensity, "#FFD60A")
            row_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:8px;'
                f'display:flex;align-items:center;gap:12px">'
                f'<div style="font-size:20px">&#127939;</div>'
                f'<div style="flex:1">'
                f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
                f'{r["exercise_date"]} &middot; {dist} km &middot; {dur} min</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                f'Pace: {pace_fmt}/km'
                f'{" &middot; " + r["notes"] if r.get("notes") else ""}</div></div>'
                f'<div style="background:{int_color}20;color:{int_color};font-size:11px;'
                f'font-weight:600;padding:4px 8px;border-radius:6px">{intensity.title()}</div></div>'
            )
            st.markdown(row_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Pace Zones
# ══════════════════════════════════════════════════════════════════════════
with tab_zones:
    render_section_header("VDOT Pace Zones", "Based on Jack Daniels' Running Formula")

    st.markdown(
        f'<div style="font-size:13px;color:{A["label_secondary"]};margin-bottom:16px">'
        f'Enter a recent race result or time trial to calculate your VDOT and training pace zones.</div>',
        unsafe_allow_html=True,
    )

    col_dist, col_time = st.columns(2)
    with col_dist:
        race_options = {v["label"]: k for k, v in RACE_DISTANCES.items()}
        race_options["Custom"] = "custom"
        selected_race = st.selectbox("Race Distance", list(race_options.keys()), index=0)
        if race_options[selected_race] == "custom":
            race_km = st.number_input("Distance (km)", min_value=0.5, max_value=100.0, value=5.0, step=0.1)
        else:
            race_km = RACE_DISTANCES[race_options[selected_race]]["km"]
            _lt = A["label_tertiary"]
            st.markdown(f"<div style='font-size:12px;color:{_lt};padding:8px 0'>{race_km} km</div>", unsafe_allow_html=True)

    with col_time:
        _lt = A["label_tertiary"]
        st.markdown(f"<div style='font-size:12px;color:{_lt};margin-bottom:4px'>Finish Time</div>", unsafe_allow_html=True)
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            hours = st.number_input("Hours", min_value=0, max_value=10, value=0, key="vdot_h")
        with tc2:
            minutes = st.number_input("Min", min_value=0, max_value=59, value=25, key="vdot_m")
        with tc3:
            seconds = st.number_input("Sec", min_value=0, max_value=59, value=0, key="vdot_s")

    total_min = hours * 60 + minutes + seconds / 60.0

    if total_min > 0 and race_km > 0:
        vdot = estimate_vdot(race_km, total_min)

        if vdot > 0:
            # VDOT result
            vdot_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["blue"]}40;'
                f'border-left:3px solid {A["blue"]};border-radius:{A["radius_lg"]};'
                f'padding:16px;margin:16px 0;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Your VDOT</div>'
                f'<div style="font-family:{A["font_display"]};font-size:42px;font-weight:700;'
                f'color:{A["blue"]}">{vdot}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]};margin-top:4px">'
                f'Higher VDOT = better fitness. Elite runners: 70+, Recreational: 30-50</div></div>'
            )
            st.markdown(vdot_html, unsafe_allow_html=True)

            # Pace zones
            zones = get_pace_zones(vdot)
            if zones:
                zones_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_lg"]};padding:16px;margin-top:12px">'
                    f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                    f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:12px">'
                    f'Training Pace Zones</div>'
                )
                for key in ("z1", "z2", "z3", "z4", "z5"):
                    z = zones.get(key)
                    if z:
                        zones_html += (
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:10px 0;border-bottom:1px solid {A["separator"]}">'
                            f'<div style="width:8px;height:32px;border-radius:4px;'
                            f'background:{z["color"]}"></div>'
                            f'<div style="flex:1">'
                            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
                            f'{z["name"]}</div>'
                            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                            f'{z["description"][:80]}...</div></div>'
                            f'<div style="font-family:{A["font_display"]};font-size:15px;'
                            f'font-weight:700;color:{z["color"]};min-width:110px;text-align:right">'
                            f'{z["min_pace_fmt"]} – {z["max_pace_fmt"]}</div>'
                            f'<div style="font-size:11px;color:{A["label_tertiary"]};min-width:40px">'
                            f'/km</div></div>'
                        )
                zones_html += '</div>'
                st.markdown(zones_html, unsafe_allow_html=True)

            # Science note
            st.markdown(
                f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:12px;padding:8px">'
                f'Based on Daniels &amp; Gilbert oxygen-cost model. VDOT is a measure of '
                f'running fitness that accounts for both VO2max and running economy. '
                f'Ref: Daniels, J. (2022) "Daniels\' Running Formula", 4th ed.</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Race Predictor
# ══════════════════════════════════════════════════════════════════════════
with tab_predictor:
    render_section_header("Race Time Predictor", "Riegel formula (T2 = T1 x (D2/D1)^1.06)")

    st.markdown(
        f'<div style="font-size:13px;color:{A["label_secondary"]};margin-bottom:16px">'
        f'Enter a known race result to predict your times at other distances.</div>',
        unsafe_allow_html=True,
    )

    with st.form("race_predictor_form"):
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            pred_dist_options = {v["label"]: v["km"] for k, v in RACE_DISTANCES.items()}
            pred_dist_options["Custom"] = 0.0
            sel_pred = st.selectbox("Known Race Distance", list(pred_dist_options.keys()))
            if sel_pred == "Custom":
                pred_km = st.number_input("Distance (km)", min_value=0.5, max_value=100.0, value=5.0, step=0.1, key="pred_km")
            else:
                pred_km = pred_dist_options[sel_pred]
        with pcol2:
            _lt = A["label_tertiary"]
            st.markdown(f"<div style='font-size:12px;color:{_lt}'>&nbsp;</div>", unsafe_allow_html=True)
            ptc1, ptc2, ptc3 = st.columns(3)
            with ptc1:
                ph = st.number_input("Hours", min_value=0, max_value=10, value=0, key="pred_h")
            with ptc2:
                pm = st.number_input("Min", min_value=0, max_value=59, value=25, key="pred_m")
            with ptc3:
                ps = st.number_input("Sec", min_value=0, max_value=59, value=0, key="pred_s")

        pred_submitted = st.form_submit_button("Predict Race Times", use_container_width=True)

    if pred_submitted:
        pred_total_min = ph * 60 + pm + ps / 60.0
        if pred_total_min > 0 and pred_km > 0:
            predictions = predict_race_times(pred_km, pred_total_min)
            if predictions:
                cards_html = '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:12px">'
                for race_key, pred in predictions.items():
                    cards_html += (
                        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                        f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                        f'color:{A["label_tertiary"]};margin-bottom:6px">{pred["label"]}</div>'
                        f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
                        f'color:{A["label_primary"]}">{pred["predicted_time_fmt"]}</div>'
                        f'<div style="font-size:12px;color:{A["label_secondary"]};margin-top:4px">'
                        f'{pred["predicted_pace_fmt"]} /km</div></div>'
                    )
                cards_html += '</div>'
                st.markdown(cards_html, unsafe_allow_html=True)

                st.markdown(
                    f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:12px;padding:8px">'
                    f'Based on Riegel formula (1981). Predictions assume equivalent training '
                    f'and appropriate race-day conditions. Accuracy decreases for distances '
                    f'much longer or shorter than the reference race.</div>',
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Training Load
# ══════════════════════════════════════════════════════════════════════════
with tab_load:
    render_section_header("Training Load Monitor", "Acute:Chronic Workload Ratio (Gabbett, 2016)")

    load_data = calculate_training_load(user_id, days=42)

    if load_data["atl"] == 0 and load_data["ctl"] == 0:
        st.info("Not enough running data to calculate training load. Log at least a few weeks of runs with RPE.")
    else:
        acwr = load_data["acwr"]
        if acwr < 0.8:
            acwr_color = A["blue"]
            acwr_zone = "Under-training"
        elif acwr <= 1.3:
            acwr_color = "#30D158"
            acwr_zone = "Sweet Spot"
        elif acwr <= 1.5:
            acwr_color = "#FFD60A"
            acwr_zone = "Caution"
        else:
            acwr_color = "#FF453A"
            acwr_zone = "Danger"

        # ACWR gauge
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            gauge_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">ACWR</div>'
                f'<div style="font-family:{A["font_display"]};font-size:36px;font-weight:700;'
                f'color:{acwr_color}">{acwr:.2f}</div>'
                f'<div style="font-size:12px;font-weight:600;color:{acwr_color};margin-top:4px">'
                f'{acwr_zone}</div></div>'
            )
            st.markdown(gauge_html, unsafe_allow_html=True)
        with lc2:
            atl_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Acute Load (7d)</div>'
                f'<div style="font-family:{A["font_display"]};font-size:36px;font-weight:700;'
                f'color:{A["label_primary"]}">{load_data["atl"]:.0f}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">session RPE units</div></div>'
            )
            st.markdown(atl_html, unsafe_allow_html=True)
        with lc3:
            ctl_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:20px;text-align:center">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
                f'color:{A["label_tertiary"]};margin-bottom:4px">Chronic Load (42d)</div>'
                f'<div style="font-family:{A["font_display"]};font-size:36px;font-weight:700;'
                f'color:{A["label_primary"]}">{load_data["ctl"]:.0f}</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">weekly avg</div></div>'
            )
            st.markdown(ctl_html, unsafe_allow_html=True)

        # Load advice
        advice_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {acwr_color}40;'
            f'border-left:3px solid {acwr_color};border-radius:{A["radius_lg"]};'
            f'padding:16px;margin:16px 0">'
            f'<div style="font-size:13px;color:{A["label_primary"]}">'
            f'{load_data["acwr_label"]}</div></div>'
        )
        st.markdown(advice_html, unsafe_allow_html=True)

        # Daily load chart
        render_section_header("Daily Training Load", "Last 42 days")
        daily = load_data["daily_loads"]
        if daily:
            dates = [d["date"] for d in daily]
            loads = [d["load"] for d in daily]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=loads,
                marker_color=A["blue"],
                opacity=0.7,
                hovertemplate="Load: %{y:.0f}<br>%{x}<extra></extra>",
            ))
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=A["chart_bg"],
                font=dict(family=A["font_text"], color=A["chart_text"]),
                margin=dict(l=40, r=20, t=20, b=40),
                height=280,
                xaxis=dict(gridcolor=A["chart_grid"]),
                yaxis=dict(title="Session Load (RPE x min)", gridcolor=A["chart_grid"]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        # ACWR zones explanation
        with st.expander("Understanding ACWR"):
            explain_html = (
                f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:1.6">'
                f'<strong>Acute:Chronic Workload Ratio (ACWR)</strong> compares your recent '
                f'training load (last 7 days) to your long-term baseline (42-day average).'
                f'<br><br>'
                f'<span style="color:{A["blue"]}">&#9679; &lt; 0.8</span> — Under-training. '
                f'You may be losing fitness. Consider gradually increasing volume.<br>'
                f'<span style="color:#30D158">&#9679; 0.8–1.3</span> — Sweet spot. '
                f'Good balance of stimulus and recovery. Optimal injury prevention zone.<br>'
                f'<span style="color:#FFD60A">&#9679; 1.3–1.5</span> — Caution. '
                f'Training spike detected. Monitor for signs of overreaching.<br>'
                f'<span style="color:#FF453A">&#9679; &gt; 1.5</span> — Danger. '
                f'High injury risk. Reduce training volume and prioritize recovery.'
                f'<br><br>'
                f'Ref: Gabbett (2016) Br J Sports Med. PMID: 26758673</div>'
            )
            st.markdown(explain_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 5: Training Plan
# ══════════════════════════════════════════════════════════════════════════
with tab_plan:
    render_section_header("Training Plan Generator", "Structured plans for race goals")

    with st.form("running_plan_form"):
        fpc1, fpc2, fpc3 = st.columns(3)
        with fpc1:
            goal = st.selectbox("Goal Race", ["5K", "10K", "Half Marathon", "Marathon"])
            goal_map = {"5K": "5k", "10K": "10k", "Half Marathon": "half_marathon", "Marathon": "marathon"}
            goal_key = goal_map[goal]
        with fpc2:
            current_km = st.number_input("Current Weekly km", min_value=5.0, max_value=200.0, value=20.0, step=5.0)
        with fpc3:
            weeks = st.number_input("Weeks", min_value=6, max_value=20, value=12)

        plan_submitted = st.form_submit_button("Generate Plan", use_container_width=True)

    if plan_submitted:
        plan = get_training_plan(goal_key, current_km, weeks)
        if "error" in plan:
            st.error(plan["error"])
        else:
            # Plan overview
            overview_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;margin:16px 0">'
                f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};margin-bottom:8px">'
                f'{plan["goal_label"]}</div>'
                f'<div style="font-size:13px;color:{A["label_secondary"]};margin-bottom:12px">'
                f'{plan["description"]}</div>'
                f'<div style="display:flex;gap:16px;flex-wrap:wrap">'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'Start: <strong style="color:{A["label_primary"]}">{plan["start_date"]}</strong></div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'Duration: <strong style="color:{A["label_primary"]}">{plan["weeks"]} weeks</strong></div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'Peak: <strong style="color:{A["label_primary"]}">{plan["peak_weekly_km"]} km/week</strong></div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'Sessions: <strong style="color:{A["label_primary"]}">{plan["sessions_per_week"]}/week</strong></div></div></div>'
            )
            st.markdown(overview_html, unsafe_allow_html=True)

            # Volume progression chart
            week_nums = [w["week"] for w in plan["plan_weeks"]]
            week_kms = [w["total_km"] for w in plan["plan_weeks"]]
            week_colors = [
                "#FF453A" if w["is_taper"] else "#FFD60A" if w["is_deload"] else A["blue"]
                for w in plan["plan_weeks"]
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"W{n}" for n in week_nums],
                y=week_kms,
                marker_color=week_colors,
                hovertemplate="Week %{x}: %{y} km<extra></extra>",
            ))
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=A["chart_bg"],
                font=dict(family=A["font_text"], color=A["chart_text"]),
                margin=dict(l=40, r=20, t=20, b=40),
                height=250,
                xaxis=dict(gridcolor=A["chart_grid"]),
                yaxis=dict(title="Weekly km", gridcolor=A["chart_grid"]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            legend_html = (
                f'<div style="display:flex;gap:16px;font-size:11px;color:{A["label_tertiary"]};margin-bottom:16px">'
                f'<span><span style="color:{A["blue"]}">&#9679;</span> Build</span>'
                f'<span><span style="color:#FFD60A">&#9679;</span> Deload</span>'
                f'<span><span style="color:#FF453A">&#9679;</span> Taper</span></div>'
            )
            st.markdown(legend_html, unsafe_allow_html=True)

            # Week-by-week sessions
            type_colors = {
                "easy": "#30D158", "long": A["blue"], "tempo": "#FFD60A",
                "interval": "#FF9F0A", "recovery": "#BF5AF2", "rest": A["label_tertiary"],
            }

            for pw in plan["plan_weeks"]:
                with st.expander(f"Week {pw['week']} — {pw['label']} ({pw['total_km']} km)"):
                    for sess in pw["sessions"]:
                        tc = type_colors.get(sess["type"], A["label_secondary"])
                        sess_html = (
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:8px 0;border-bottom:1px solid {A["separator"]}">'
                            f'<div style="font-size:12px;color:{A["label_tertiary"]};min-width:32px">'
                            f'{sess["day"]}</div>'
                            f'<div style="background:{tc}20;color:{tc};font-size:11px;'
                            f'font-weight:600;padding:3px 8px;border-radius:6px;min-width:60px;'
                            f'text-align:center">{sess["type"].title()}</div>'
                            f'<div style="font-size:13px;color:{A["label_primary"]};flex:1">'
                            f'{sess["description"]}</div>'
                            f'<div style="font-family:{A["font_display"]};font-size:13px;'
                            f'font-weight:600;color:{A["label_primary"]}">'
                            f'{sess["target_km"]} km</div></div>'
                        )
                        st.markdown(sess_html, unsafe_allow_html=True)
