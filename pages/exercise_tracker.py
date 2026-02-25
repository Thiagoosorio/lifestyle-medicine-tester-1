"""Exercise Tracker — Log workouts, track weekly volume, connect Strava."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.exercise_display import (
    render_exercise_score_gauge,
    render_weekly_progress_bar,
    render_exercise_summary_strip,
    render_exercise_card,
)
from config.exercise_data import (
    EXERCISE_TYPES,
    EXERCISE_TYPE_ORDER,
    INTENSITY_LEVELS,
    WEEKLY_TARGETS,
    EXERCISE_CATEGORIES,
)
from services.exercise_service import (
    log_exercise,
    get_exercise_history,
    get_weekly_stats,
    calculate_exercise_score,
    update_weekly_summary,
    get_weekly_history,
    get_exercise_type_distribution,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Exercise Tracker",
    "Track workouts, monitor weekly volume against WHO guidelines, and connect Strava."
)

tab_dashboard, tab_log, tab_strava, tab_trends = st.tabs([
    "Dashboard", "Log Workout", "Strava", "Trends"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    stats = get_weekly_stats(user_id)
    score = calculate_exercise_score(user_id)

    if stats["session_count"] == 0:
        st.info("No workouts logged this week. Go to the **Log Workout** tab to record your first session.")
    else:
        # Update weekly summary in DB
        update_weekly_summary(user_id)

        col_score, col_progress = st.columns([1, 2])
        with col_score:
            render_exercise_score_gauge(score)
        with col_progress:
            render_weekly_progress_bar(stats)

        render_exercise_summary_strip(stats)

    # Recent workouts
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Recent Workouts", "Last 7 days")

    recent = get_exercise_history(user_id, days=7)
    if recent:
        for ex in recent:
            render_exercise_card(ex)
    else:
        st.caption("No recent workouts. Start logging to see your activity here.")

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Log Workout
# ══════════════════════════════════════════════════════════════════════════
with tab_log:
    render_section_header("Log Workout", "Record a new exercise session")

    with st.form("log_exercise_form"):
        exercise_date = st.date_input("Date", value=date.today())

        # Exercise type selector with labels
        type_options = [
            f"{EXERCISE_TYPES[t]['icon']}  {EXERCISE_TYPES[t]['label']}"
            for t in EXERCISE_TYPE_ORDER
        ]
        type_labels_to_keys = {
            f"{EXERCISE_TYPES[t]['icon']}  {EXERCISE_TYPES[t]['label']}": t
            for t in EXERCISE_TYPE_ORDER
        }
        selected_type_label = st.selectbox("Exercise Type", type_options)
        selected_type = type_labels_to_keys[selected_type_label]

        col1, col2 = st.columns(2)
        with col1:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=600, value=30)
        with col2:
            intensity_options = ["Light", "Moderate", "Vigorous"]
            intensity_help = {
                "Light": "Easy effort, can hold a conversation",
                "Moderate": "Brisk effort, can talk in short sentences",
                "Vigorous": "Hard effort, difficult to talk",
            }
            selected_intensity_label = st.selectbox(
                "Intensity",
                intensity_options,
                index=1,
                help="Light: 50-63% max HR | Moderate: 64-76% max HR | Vigorous: 77-93% max HR",
            )
            selected_intensity = selected_intensity_label.lower()

        st.markdown("**Optional Details**")
        col3, col4 = st.columns(2)
        with col3:
            distance = st.number_input("Distance (km)", min_value=0.0, max_value=500.0, value=None, step=0.1)
            avg_hr = st.number_input("Avg Heart Rate (bpm)", min_value=0, max_value=250, value=None)
        with col4:
            calories = st.number_input("Calories burned", min_value=0, max_value=5000, value=None)
            max_hr = st.number_input("Max Heart Rate (bpm)", min_value=0, max_value=250, value=None)

        rpe = st.slider(
            "Rate of Perceived Exertion (RPE)",
            min_value=1, max_value=10, value=5,
            help="1=Very Easy, 5=Moderate, 7=Hard, 10=Maximal",
        )

        notes = st.text_area("Notes (optional)", placeholder="How did you feel? What did you do?")

        submitted = st.form_submit_button("Save Workout", use_container_width=True)
        if submitted:
            log_exercise(
                user_id=user_id,
                exercise_date=exercise_date.isoformat(),
                exercise_type=selected_type,
                duration_min=duration,
                intensity=selected_intensity,
                distance_km=distance if distance and distance > 0 else None,
                calories=calories if calories and calories > 0 else None,
                avg_hr=avg_hr if avg_hr and avg_hr > 0 else None,
                max_hr=max_hr if max_hr and max_hr > 0 else None,
                rpe=rpe,
                notes=notes if notes else None,
            )
            # Update weekly summary
            update_weekly_summary(user_id)
            st.toast("Workout saved!")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Strava
# ══════════════════════════════════════════════════════════════════════════
with tab_strava:
    render_section_header("Strava Connect", "Import workouts from Strava")

    from services.strava_service import (
        is_strava_configured,
        get_strava_connection,
        get_strava_auth_url,
        exchange_strava_code,
        disconnect_strava,
        import_strava_activities,
    )

    # Privacy notice
    privacy_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["teal"]}40;'
        f'border-left:3px solid {A["teal"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:16px">'
        f'<div style="font-size:12px;color:{A["label_secondary"]}">'
        f'&#128274; <strong>Privacy:</strong> We request read-only access to your Strava activities. '
        f'Your Strava credentials are never stored. You can disconnect at any time.</div></div>'
    )
    st.markdown(privacy_html, unsafe_allow_html=True)

    if not is_strava_configured():
        setup_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:16px">'
            f'<div style="font-size:14px;font-weight:600;color:{A["label_primary"]};margin-bottom:8px">'
            f'Strava Setup Required</div>'
            f'<div style="font-size:12px;color:{A["label_secondary"]}">'
            f'To enable Strava integration, set the following environment variables or '
            f'add them to <code>.streamlit/secrets.toml</code>:'
            f'<br><br>'
            f'<code>STRAVA_CLIENT_ID = "your_client_id"</code><br>'
            f'<code>STRAVA_CLIENT_SECRET = "your_client_secret"</code>'
            f'<br><br>'
            f'Get these from '
            f'<a href="https://www.strava.com/settings/api" style="color:{A["blue"]}">'
            f'strava.com/settings/api</a></div></div>'
        )
        st.markdown(setup_html, unsafe_allow_html=True)
    else:
        strava_conn = get_strava_connection(user_id)

        # Handle OAuth callback
        query_params = st.query_params
        if "code" in query_params and "scope" in query_params:
            code = query_params["code"]
            try:
                exchange_strava_code(user_id, code)
                st.query_params.clear()
                st.toast("Connected to Strava!")
                st.rerun()
            except Exception as e:
                st.error(f"Strava connection failed: {str(e)}")
                st.query_params.clear()

        if strava_conn and strava_conn.get("access_token"):
            # Connected state
            connected_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid #FC4C0240;'
                f'border-radius:{A["radius_md"]};padding:16px;text-align:center;margin-bottom:16px">'
                f'<div style="font-size:24px;margin-bottom:8px">&#9989;</div>'
                f'<div style="font-size:15px;font-weight:600;color:#FC4C02">'
                f'Connected to Strava</div>'
            )
            if strava_conn.get("last_sync"):
                connected_html += (
                    f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:4px">'
                    f'Last sync: {strava_conn["last_sync"]}</div>'
                )
            connected_html += '</div>'
            st.markdown(connected_html, unsafe_allow_html=True)

            # Import controls
            days = st.select_slider("Import range (days)", options=[7, 14, 30, 60, 90], value=30)

            if st.button("Import Activities", use_container_width=True, type="primary"):
                with st.spinner("Importing activities from Strava..."):
                    try:
                        count = import_strava_activities(user_id, days=days)
                        update_weekly_summary(user_id)
                        st.toast(f"Imported {count} activities from Strava!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Import failed: {str(e)}")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Disconnect Strava", use_container_width=True):
                disconnect_strava(user_id)
                st.toast("Disconnected from Strava.")
                st.rerun()
        else:
            # Not connected — show connect button
            redirect_uri = "http://localhost:8501/"
            auth_url = get_strava_auth_url(redirect_uri)

            if auth_url:
                connect_html = (
                    f'<div style="text-align:center;padding:20px">'
                    f'<div style="font-size:20px;margin-bottom:12px">&#127939;</div>'
                    f'<div style="font-size:14px;color:{A["label_secondary"]};margin-bottom:16px">'
                    f'Connect your Strava account to automatically import workouts.</div>'
                    f'<a href="{auth_url}" target="_self" style="'
                    f'display:inline-block;padding:10px 24px;background:#FC4C02;'
                    f'color:white;font-size:14px;font-weight:600;'
                    f'border-radius:8px;text-decoration:none">'
                    f'Connect with Strava</a></div>'
                )
                st.markdown(connect_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Trends
# ══════════════════════════════════════════════════════════════════════════
with tab_trends:
    render_section_header("Exercise Trends", "Your activity patterns over time")

    history = get_exercise_history(user_id, days=90)
    if not history:
        st.caption("Not enough data for trends yet. Keep logging workouts!")
    else:
        metric = st.selectbox("Metric", [
            "Weekly Volume (min)", "Exercise Score", "Session Count"
        ])

        # Get weekly history
        weekly = get_weekly_history(user_id, weeks=12)

        if not weekly:
            # Compute current week at minimum
            update_weekly_summary(user_id)
            weekly = get_weekly_history(user_id, weeks=12)

        if weekly:
            weeks = [w["week_start"] for w in weekly]

            if metric == "Weekly Volume (min)":
                y_data = [w.get("total_min", 0) for w in weekly]
                y_title = "Minutes"
                color = "#0A84FF"
                ref_line = WEEKLY_TARGETS["aerobic_moderate_min"]
                ref_label = "150 min target"
            elif metric == "Exercise Score":
                y_data = [w.get("exercise_score", 0) for w in weekly]
                y_title = "Score"
                color = "#30D158"
                ref_line = None
                ref_label = None
            else:
                y_data = [w.get("session_count", 0) for w in weekly]
                y_title = "Sessions"
                color = "#BF5AF2"
                ref_line = None
                ref_label = None

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=weeks, y=y_data,
                marker_color=color,
                marker_line_width=0,
                opacity=0.85,
                hovertemplate="%{y}<br>Week of %{x}<extra></extra>",
            ))

            if ref_line:
                fig.add_hline(
                    y=ref_line, line_dash="dash", line_color="#30D158",
                    opacity=0.6,
                    annotation_text=ref_label,
                    annotation_position="top left",
                    annotation=dict(font_color="#30D158", font_size=10),
                )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1C1C1E",
                font=dict(family=A["font_text"]),
                margin=dict(l=40, r=20, t=30, b=40),
                height=320,
                xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
                yaxis=dict(title=y_title, gridcolor="rgba(84,84,88,0.3)"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Log more workouts to see weekly trends.")

        # Exercise type distribution
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        render_section_header("Activity Breakdown", "Last 30 days")

        dist = get_exercise_type_distribution(user_id, days=30)
        if dist:
            labels = []
            values = []
            colors = []
            for d in dist:
                type_key = d["exercise_type"]
                type_info = EXERCISE_TYPES.get(type_key, EXERCISE_TYPES["other"])
                cat_info = EXERCISE_CATEGORIES.get(type_info["category"], {})
                labels.append(type_info["label"])
                values.append(d["total_min"])
                colors.append(cat_info.get("color", "#AEAEB2"))

            fig2 = go.Figure(data=[go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors),
                hole=0.45,
                textinfo="label+percent",
                textfont=dict(size=11, color="#FFFFFF"),
                hovertemplate="%{label}: %{value} min<extra></extra>",
            )])
            fig2.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1C1C1E",
                font=dict(family=A["font_text"]),
                margin=dict(l=20, r=20, t=20, b=20),
                height=280,
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
