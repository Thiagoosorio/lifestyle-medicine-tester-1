import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from models.checkin import get_checkins_for_range, get_recent_checkins
from models.assessment import get_assessment_history
from models.goal import get_goals, get_goal_progress_history
from models.habit import get_all_habits, get_habit_log_for_range, get_habit_streak
from services.export_service import export_checkins_csv, export_goals_csv, export_assessments_csv, export_all_json
from components.progress_charts import render_mood_energy_chart, render_pillar_trends, render_habit_completion_chart
from components.wheel_chart import create_wheel_chart, create_trend_chart
from services.habit_service import get_day_completion_rate

user_id = st.session_state.user_id

st.title("Progress Register")
st.markdown("Your complete tracking history across all areas of lifestyle medicine.")

tab_checkins, tab_assessments, tab_goals, tab_habits, tab_insights, tab_export = st.tabs(
    ["Check-in History", "Assessments", "Goals", "Habits", "Insights", "Export"]
)

# ── Check-in History ────────────────────────────────────────────────────────
with tab_checkins:
    st.markdown("### Check-in History")
    range_col1, range_col2 = st.columns(2)
    with range_col1:
        start = st.date_input("From", value=date.today() - timedelta(days=30), key="ci_start")
    with range_col2:
        end = st.date_input("To", value=date.today(), key="ci_end")

    checkins = get_checkins_for_range(user_id, start.isoformat(), end.isoformat())

    if checkins:
        tab_charts, tab_table = st.tabs(["Charts", "Table"])
        with tab_charts:
            render_mood_energy_chart(checkins)
            render_pillar_trends(checkins)
        with tab_table:
            import pandas as pd
            df = pd.DataFrame(checkins)
            display_cols = ["checkin_date", "mood", "energy", "nutrition_rating", "activity_rating",
                           "sleep_rating", "stress_rating", "connection_rating", "substance_rating"]
            available = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available], use_container_width=True, hide_index=True)
    else:
        st.info("No check-in data for this period.")

# ── Assessments ─────────────────────────────────────────────────────────────
with tab_assessments:
    st.markdown("### Wheel Assessment History")
    history = get_assessment_history(user_id)

    if history:
        st.plotly_chart(create_trend_chart(history), use_container_width=True)

        st.markdown("### All Assessments")
        for h in history:
            with st.expander(f"{h['assessed_at'][:10]} — Total: {h['total']}/60"):
                st.plotly_chart(create_wheel_chart(h["scores"], title=h["assessed_at"][:10]), use_container_width=True)
    else:
        st.info("No assessments yet.")

# ── Goals ───────────────────────────────────────────────────────────────────
with tab_goals:
    st.markdown("### Goal History")
    all_goals = get_goals(user_id)

    if all_goals:
        from services.goal_service import get_goal_stats
        stats = get_goal_stats(user_id)
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Goals", stats["total"])
        with cols[1]:
            st.metric("Completed", stats["completed"])
        with cols[2]:
            st.metric("Active", stats["active"])
        with cols[3]:
            st.metric("Completion Rate", f"{stats['completion_rate']:.0%}")

        for goal in all_goals:
            pillar = PILLARS.get(goal["pillar_id"], {})
            status_emoji = {"active": "🟢", "completed": "✅", "abandoned": "❌", "paused": "⏸"}.get(goal["status"], "")
            with st.expander(f"{status_emoji} {goal['title']} — {pillar.get('display_name', '')}"):
                st.progress(goal["progress_pct"] / 100)
                st.caption(f"Progress: {goal['progress_pct']}% | Status: {goal['status']} | Due: {goal['target_date'][:10]}")

                progress_history = get_goal_progress_history(goal["id"])
                if progress_history:
                    import plotly.graph_objects as go
                    fig = go.Figure(data=go.Scatter(
                        x=[p["logged_at"][:10] for p in progress_history],
                        y=[p["progress_pct"] for p in progress_history],
                        mode="lines+markers",
                        line=dict(color=pillar.get("color", "#2196F3")),
                    ))
                    fig.update_layout(
                        yaxis=dict(range=[0, 105], title="Progress %"),
                        xaxis_title="Date", height=250,
                        margin=dict(t=20, b=40, l=40, r=20),
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No goals created yet.")

# ── Habits ──────────────────────────────────────────────────────────────────
with tab_habits:
    st.markdown("### Habit Statistics")
    habits = get_all_habits(user_id)

    if habits:
        # Daily completion rate chart for last 30 days
        st.markdown("#### Daily Completion Rate (Last 30 Days)")
        daily_rates = {}
        for i in range(30):
            d = (date.today() - timedelta(days=29 - i)).isoformat()
            daily_rates[d] = get_day_completion_rate(user_id, d)
        render_habit_completion_chart(daily_rates)

        # Per-habit stats
        st.markdown("#### Individual Habit Stats")
        for habit in habits:
            if not habit["is_active"]:
                continue
            pillar = PILLARS.get(habit["pillar_id"], {})
            streak = get_habit_streak(habit["id"], user_id)

            # 30-day completion count
            log = get_habit_log_for_range(
                user_id,
                (date.today() - timedelta(days=29)).isoformat(),
                date.today().isoformat(),
            )
            completed_days = sum(1 for d in range(30)
                                 if log.get((habit["id"], (date.today() - timedelta(days=29 - d)).isoformat()), 0) > 0)

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{pillar.get('icon', '')} {habit['name']}**")
            with col2:
                st.metric("Streak", f"{streak}d")
            with col3:
                st.metric("30-day", f"{completed_days}/30")
    else:
        st.info("No habits set up yet.")

# ── Insights (Pillar Correlation Dashboard) ────────────────────────────────
with tab_insights:
    st.markdown("### Pillar Correlations & Patterns")
    st.caption("Discover how your lifestyle pillars affect each other, based on your own check-in data.")

    import pandas as pd
    import plotly.express as px
    import numpy as np

    # Load all check-in data
    all_checkins = get_checkins_for_range(user_id, "2000-01-01", date.today().isoformat())

    if len(all_checkins) >= 7:
        df = pd.DataFrame(all_checkins)

        field_labels = {
            "mood": "Mood",
            "energy": "Energy",
            "nutrition_rating": "Nutrition",
            "activity_rating": "Activity",
            "sleep_rating": "Sleep",
            "stress_rating": "Stress Mgmt",
            "connection_rating": "Connection",
            "substance_rating": "Substance",
        }

        fields = list(field_labels.keys())
        available_fields = [f for f in fields if f in df.columns and df[f].notna().sum() >= 5]

        if len(available_fields) >= 3:
            corr_df = df[available_fields].corr()
            corr_df = corr_df.rename(index=field_labels, columns=field_labels)

            # Correlation heatmap
            st.markdown("#### Correlation Matrix")
            st.caption("Stronger colors = stronger relationship between pillars. Look for dark blue squares!")

            fig_corr = px.imshow(
                corr_df.values,
                x=list(corr_df.columns),
                y=list(corr_df.index),
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                text_auto=".2f",
                aspect="auto",
            )
            fig_corr.update_layout(
                height=400,
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            # Top correlations as plain-English insights
            st.markdown("#### Key Patterns From Your Data")

            insights = []
            for i, f1 in enumerate(available_fields):
                for f2 in available_fields[i+1:]:
                    corr_val = df[f1].corr(df[f2])
                    if abs(corr_val) >= 0.3 and not np.isnan(corr_val):
                        insights.append((field_labels[f1], field_labels[f2], corr_val, f1, f2))

            insights.sort(key=lambda x: abs(x[2]), reverse=True)

            if insights:
                for label1, label2, corr_val, f1, f2 in insights[:5]:
                    direction = "positively" if corr_val > 0 else "inversely"
                    strength = "strongly" if abs(corr_val) >= 0.6 else "moderately"

                    # Calculate conditional averages
                    high_mask = df[f1] >= 7
                    low_mask = df[f1] <= 4
                    high_avg = df.loc[high_mask, f2].mean() if high_mask.sum() >= 3 else None
                    low_avg = df.loc[low_mask, f2].mean() if low_mask.sum() >= 3 else None

                    if high_avg is not None and low_avg is not None:
                        diff = high_avg - low_avg
                        st.info(
                            f"**{label1} & {label2}** are {strength} {direction} correlated (r={corr_val:.2f}). "
                            f"On days you rate {label1} 7+, your avg {label2} is **{high_avg:.1f}** "
                            f"vs **{low_avg:.1f}** on days {label1} is 4 or below "
                            f"({'**+' + f'{diff:.1f}' + ' point difference!**' if diff > 0 else ''})"
                        )
                    else:
                        st.info(
                            f"**{label1} & {label2}** are {strength} {direction} correlated (r={corr_val:.2f})."
                        )

                if not insights:
                    st.caption("Not enough variation in your data yet to detect strong patterns. Keep checking in!")
            else:
                st.caption("No strong correlations found yet. Keep checking in daily — patterns emerge over time!")

            # Scatter plot explorer
            st.markdown("#### Explore Relationships")
            scatter_cols = st.columns(2)
            with scatter_cols[0]:
                x_field = st.selectbox("X axis", available_fields, format_func=lambda f: field_labels[f], key="scatter_x")
            with scatter_cols[1]:
                y_field = st.selectbox("Y axis", available_fields, index=min(1, len(available_fields)-1), format_func=lambda f: field_labels[f], key="scatter_y")

            if x_field != y_field:
                scatter_df = df[[x_field, y_field, "checkin_date"]].dropna()
                if len(scatter_df) >= 3:
                    fig_scatter = px.scatter(
                        scatter_df, x=x_field, y=y_field,
                        labels={x_field: field_labels[x_field], y_field: field_labels[y_field]},
                        trendline="ols",
                        hover_data=["checkin_date"],
                        color_discrete_sequence=["#2196F3"],
                    )
                    fig_scatter.update_layout(height=350, margin=dict(t=20, b=40, l=40, r=20))
                    st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Need at least 5 check-ins with pillar ratings to show correlations. Keep logging!")
    else:
        st.info("Need at least 7 check-ins to generate meaningful insights. Keep logging daily!")

# ── Export ──────────────────────────────────────────────────────────────────
with tab_export:
    st.markdown("### Export Your Data")

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        exp_start = st.date_input("From", value=date.today() - timedelta(days=90), key="exp_start")
    with exp_col2:
        exp_end = st.date_input("To", value=date.today(), key="exp_end")

    st.markdown("#### Individual Exports (CSV)")
    btn_cols = st.columns(3)
    with btn_cols[0]:
        csv_data = export_checkins_csv(user_id, exp_start.isoformat(), exp_end.isoformat())
        st.download_button("Download Check-ins CSV", csv_data, "checkins.csv", "text/csv", use_container_width=True)
    with btn_cols[1]:
        csv_data = export_goals_csv(user_id)
        st.download_button("Download Goals CSV", csv_data, "goals.csv", "text/csv", use_container_width=True)
    with btn_cols[2]:
        csv_data = export_assessments_csv(user_id)
        st.download_button("Download Assessments CSV", csv_data, "assessments.csv", "text/csv", use_container_width=True)

    st.markdown("#### Full Export (JSON)")
    json_data = export_all_json(user_id)
    st.download_button("Download All Data (JSON)", json_data, "lifestyle_medicine_data.json", "application/json", use_container_width=True)
