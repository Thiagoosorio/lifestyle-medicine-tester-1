"""Analytics & Transformation: long-term trends, journey timeline, habit heatmap, achievement badges."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import date, timedelta
from db.database import get_connection
from config.settings import PILLARS, PILLAR_COLORS
from models.checkin import get_checkins_for_range
from models.assessment import get_assessment_history
from models.habit import get_all_habits, get_habit_log_for_range, get_habit_streak
from services.habit_service import get_day_completion_rate, get_overall_streak
from services.coin_service import get_coin_balance

user_id = st.session_state.user_id

st.title("Analytics & Transformation")
st.caption("Your complete health journey — visualized")

tab_journey, tab_heatmap, tab_trends, tab_badges, tab_health, tab_body, tab_nutrition = st.tabs(
    ["Transformation Journey", "Habit Heatmap", "Long-Term Trends", "Achievements",
     "Health Metrics", "Body & Labs", "Nutrition"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: TRANSFORMATION JOURNEY (TIMELINE)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_journey:
    st.markdown("### Your Transformation Timeline")

    history = get_assessment_history(user_id)

    if len(history) >= 2:
        # ── Before vs After Wheel Comparison ─────────────────────────────────
        st.markdown("#### Then vs Now")
        first = history[-1]
        latest = history[0]

        col_then, col_now = st.columns(2)
        with col_then:
            st.markdown(f"**Start** — {first['assessed_at'][:10]}")
            st.metric("Total Score", f"{first['total']}/60")
        with col_now:
            st.markdown(f"**Latest** — {latest['assessed_at'][:10]}")
            change = latest["total"] - first["total"]
            st.metric("Total Score", f"{latest['total']}/60", delta=f"+{change}" if change > 0 else str(change))

        # Overlay radar chart
        categories = [PILLARS[pid]["display_name"] for pid in sorted(first["scores"].keys())]
        first_vals = [first["scores"][pid] for pid in sorted(first["scores"].keys())]
        latest_vals = [latest["scores"][pid] for pid in sorted(latest["scores"].keys())]
        # Close the radar
        categories_closed = categories + [categories[0]]
        first_closed = first_vals + [first_vals[0]]
        latest_closed = latest_vals + [latest_vals[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=first_closed, theta=categories_closed, name=f"Start ({first['assessed_at'][:10]})",
            fill='toself', fillcolor='rgba(244,67,54,0.15)',
            line=dict(color='#F44336', width=2, dash='dot'),
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=latest_closed, theta=categories_closed, name=f"Now ({latest['assessed_at'][:10]})",
            fill='toself', fillcolor='rgba(76,175,80,0.2)',
            line=dict(color='#4CAF50', width=3),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            height=450, margin=dict(t=30, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # ── Per-Pillar Change Cards ──────────────────────────────────────────
        st.markdown("#### Pillar-by-Pillar Growth")
        pillar_cols = st.columns(6)
        for i, pid in enumerate(sorted(first["scores"].keys())):
            with pillar_cols[i]:
                old = first["scores"][pid]
                new = latest["scores"][pid]
                diff = new - old
                st.metric(
                    PILLARS[pid]["display_name"],
                    f"{new}/10",
                    delta=f"+{diff}" if diff > 0 else str(diff) if diff != 0 else "—",
                )

        # ── Timeline Chart with Milestones ───────────────────────────────────
        st.markdown("#### Score Progression Over Time")

        # Build timeline data from all assessments
        timeline_dates = [h["assessed_at"][:10] for h in reversed(history)]
        timeline_totals = [h["total"] for h in reversed(history)]

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=timeline_dates, y=timeline_totals,
            mode='lines+markers+text',
            text=[str(t) for t in timeline_totals],
            textposition='top center',
            line=dict(color='#2196F3', width=3),
            marker=dict(size=10, color='#2196F3'),
            fill='tozeroy', fillcolor='rgba(33,150,243,0.1)',
            name='Total Score',
        ))

        # Add milestone annotations from coaching messages
        conn = get_connection()
        try:
            milestones = conn.execute(
                """SELECT created_at, content FROM coaching_messages
                   WHERE user_id = ? AND role = 'user'
                   AND (content LIKE '%HALF-MARATHON%' OR content LIKE '%5K%' OR content LIKE '%10K%'
                        OR content LIKE '%quit%' OR content LIKE '%FINISHED%' OR content LIKE '%reversed%')
                   ORDER BY created_at""",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

        for m in milestones:
            milestone_date = m["created_at"][:10]
            snippet = m["content"][:60] + "..."
            fig_timeline.add_annotation(
                x=milestone_date, y=max(timeline_totals),
                text=f"★ {snippet[:40]}",
                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
                arrowcolor="#FF9800", font=dict(size=9, color="#FF9800"),
                ax=0, ay=-40,
            )

        fig_timeline.update_layout(
            yaxis=dict(range=[0, 65], title="Total Score (/60)"),
            xaxis_title="Date",
            height=400,
            margin=dict(t=30, b=40, l=40, r=20),
            showlegend=False,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # ── Per-Pillar Progression Lines ─────────────────────────────────────
        st.markdown("#### Pillar Progression Over Time")
        fig_pillars = go.Figure()
        for pid in sorted(PILLARS.keys()):
            vals = [h["scores"].get(pid, 0) for h in reversed(history)]
            fig_pillars.add_trace(go.Scatter(
                x=timeline_dates, y=vals,
                mode='lines+markers',
                name=PILLARS[pid]["display_name"],
                line=dict(color=PILLARS[pid]["color"], width=2),
                marker=dict(size=6),
            ))
        fig_pillars.update_layout(
            yaxis=dict(range=[0, 10.5], title="Score", dtick=2),
            xaxis_title="Date", height=400,
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_pillars, use_container_width=True)

    else:
        st.info("Need at least 2 wheel assessments to show your transformation. Take your second assessment to unlock this view!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: GITHUB-STYLE HABIT HEATMAP (365-DAY)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_heatmap:
    st.markdown("### 365-Day Habit Heatmap")
    st.caption("Each cell represents a day. Darker green = more habits completed.")

    # Calculate daily completion for last 365 days
    end_date = date.today()
    start_date = end_date - timedelta(days=364)

    heatmap_data = []
    d = start_date
    while d <= end_date:
        rate = get_day_completion_rate(user_id, d.isoformat())
        heatmap_data.append({
            "date": d,
            "rate": rate,
            "week": d.isocalendar()[1],
            "weekday": d.weekday(),
            "month": d.strftime("%b"),
        })
        d += timedelta(days=1)

    if heatmap_data:
        df = pd.DataFrame(heatmap_data)

        # Build the heatmap matrix (7 rows = weekdays, ~52 columns = weeks)
        # Assign sequential week numbers
        week_numbers = []
        current_week = 0
        prev_iso_week = None
        for _, row in df.iterrows():
            iso_week = row["date"].isocalendar()[1]
            iso_year = row["date"].isocalendar()[0]
            week_key = (iso_year, iso_week)
            if prev_iso_week is not None and week_key != prev_iso_week:
                current_week += 1
            prev_iso_week = week_key
            week_numbers.append(current_week)
        df["seq_week"] = week_numbers

        # Create pivot
        pivot = df.pivot_table(index="weekday", columns="seq_week", values="rate", aggfunc="first")
        pivot = pivot.reindex(index=range(7))  # Ensure all weekdays

        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Build month labels for x-axis
        month_ticks = {}
        for _, row in df.iterrows():
            if row["date"].day <= 7:
                month_ticks[row["seq_week"]] = row["date"].strftime("%b")

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=weekday_labels,
            colorscale=[
                [0.0, "#ebedf0"],
                [0.01, "#9be9a8"],
                [0.4, "#40c463"],
                [0.7, "#30a14e"],
                [1.0, "#216e39"],
            ],
            zmin=0, zmax=1,
            xgap=3, ygap=3,
            hovertemplate="Week %{x}<br>%{y}<br>Completion: %{z:.0%}<extra></extra>",
            showscale=False,
        ))

        fig_heatmap.update_layout(
            height=200,
            margin=dict(t=10, b=30, l=50, r=10),
            xaxis=dict(
                tickvals=list(month_ticks.keys()),
                ticktext=list(month_ticks.values()),
                side="bottom",
            ),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Stats row
        total_days = len(df)
        active_days = len(df[df["rate"] > 0])
        perfect_days = len(df[df["rate"] >= 0.99])
        avg_rate = df["rate"].mean()

        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Active Days", f"{active_days}/{total_days}")
        with stat_cols[1]:
            st.metric("Perfect Days", str(perfect_days))
        with stat_cols[2]:
            st.metric("Avg Completion", f"{avg_rate:.0%}")
        with stat_cols[3]:
            st.metric("Current Streak", f"{get_overall_streak(user_id)} days")

        # Per-habit heatmap option
        st.divider()
        st.markdown("#### Individual Habit Streaks")
        habits = get_all_habits(user_id)
        active_habits = [h for h in habits if h["is_active"]]

        if active_habits:
            # Show top habits by streak
            habit_data = []
            for h in active_habits:
                streak = get_habit_streak(h["id"], user_id)
                pillar = PILLARS.get(h["pillar_id"], {})
                log = get_habit_log_for_range(user_id, start_date.isoformat(), end_date.isoformat())
                completed = sum(1 for i in range(365)
                                if log.get((h["id"], (start_date + timedelta(days=i)).isoformat()), 0) > 0)
                habit_data.append({
                    "name": h["name"],
                    "pillar": pillar.get("display_name", ""),
                    "color": pillar.get("color", "#999"),
                    "streak": streak,
                    "total_days": completed,
                    "rate": completed / total_days,
                })

            # Sort by total days
            habit_data.sort(key=lambda x: x["total_days"], reverse=True)

            # Horizontal bar chart
            fig_habits = go.Figure()
            fig_habits.add_trace(go.Bar(
                y=[h["name"][:30] for h in habit_data],
                x=[h["total_days"] for h in habit_data],
                orientation='h',
                marker_color=[h["color"] for h in habit_data],
                text=[f'{h["total_days"]}d ({h["rate"]:.0%}) | Streak: {h["streak"]}d' for h in habit_data],
                textposition='auto',
            ))
            fig_habits.update_layout(
                xaxis=dict(title="Days Completed (out of 365)"),
                height=max(300, len(habit_data) * 35),
                margin=dict(t=10, b=30, l=150, r=10),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_habits, use_container_width=True)

    else:
        st.info("No habit data yet. Start tracking habits to see your heatmap!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: LONG-TERM TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_trends:
    st.markdown("### Long-Term Health Trends")

    # Time range selector
    range_option = st.selectbox(
        "Time range",
        ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year", "All Time"],
        index=3,
    )
    range_days = {"Last 30 Days": 30, "Last 90 Days": 90, "Last 6 Months": 180, "Last Year": 365, "All Time": 9999}
    days_back = range_days[range_option]
    trend_start = (date.today() - timedelta(days=days_back)).isoformat()
    checkins = get_checkins_for_range(user_id, trend_start, date.today().isoformat())

    if len(checkins) >= 5:
        df = pd.DataFrame(checkins)
        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df = df.sort_values("checkin_date")

        # ── Mood & Energy with 7-day moving average ──────────────────────────
        st.markdown("#### Mood & Energy (with 7-day moving average)")

        fig_trend = go.Figure()
        for col, name, color in [("mood", "Mood", "#FF9800"), ("energy", "Energy", "#2196F3")]:
            if col in df.columns:
                fig_trend.add_trace(go.Scatter(
                    x=df["checkin_date"], y=df[col],
                    mode='markers', name=name, opacity=0.3,
                    marker=dict(color=color, size=4),
                    showlegend=False,
                ))
                # Moving average
                ma = df[col].rolling(window=7, min_periods=3).mean()
                fig_trend.add_trace(go.Scatter(
                    x=df["checkin_date"], y=ma,
                    mode='lines', name=f'{name} (7-day avg)',
                    line=dict(color=color, width=3),
                ))

        fig_trend.update_layout(
            yaxis=dict(range=[0, 10.5], title="Rating"),
            height=350, margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # ── Monthly Averages Bar Chart ───────────────────────────────────────
        st.markdown("#### Monthly Averages")
        df["month"] = df["checkin_date"].dt.to_period("M").astype(str)
        monthly = df.groupby("month").agg({
            "mood": "mean", "energy": "mean",
        }).round(1).reset_index()

        if len(monthly) >= 2:
            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Bar(
                x=monthly["month"], y=monthly["mood"],
                name="Mood", marker_color="#FF9800", opacity=0.8,
            ))
            fig_monthly.add_trace(go.Bar(
                x=monthly["month"], y=monthly["energy"],
                name="Energy", marker_color="#2196F3", opacity=0.8,
            ))
            fig_monthly.update_layout(
                barmode='group',
                yaxis=dict(range=[0, 10.5], title="Average Rating"),
                height=300, margin=dict(t=20, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

        # ── Pillar Monthly Progression ───────────────────────────────────────
        st.markdown("#### Pillar Monthly Progression")
        pillar_fields = {
            1: "nutrition_rating", 2: "activity_rating", 3: "sleep_rating",
            4: "stress_rating", 5: "connection_rating", 6: "substance_rating",
        }
        pillar_monthly = {}
        for pid, field in pillar_fields.items():
            if field in df.columns:
                p_monthly = df.groupby("month")[field].mean()
                pillar_monthly[pid] = p_monthly

        if pillar_monthly:
            fig_pm = go.Figure()
            months = sorted(df["month"].unique())
            for pid, series in pillar_monthly.items():
                vals = [series.get(m, None) for m in months]
                fig_pm.add_trace(go.Scatter(
                    x=months, y=vals,
                    mode='lines+markers',
                    name=PILLARS[pid]["display_name"],
                    line=dict(color=PILLARS[pid]["color"], width=2),
                    marker=dict(size=7),
                ))
            fig_pm.update_layout(
                yaxis=dict(range=[0, 10.5], title="Monthly Average", dtick=2),
                height=400, margin=dict(t=20, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_pm, use_container_width=True)

        # ── Weekday Patterns ─────────────────────────────────────────────────
        st.markdown("#### Weekday Patterns")
        st.caption("Which days of the week are your strongest?")
        df["weekday"] = df["checkin_date"].dt.day_name()
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_avgs = df.groupby("weekday")[["mood", "energy"]].mean().reindex(weekday_order).round(1)

        if len(weekday_avgs.dropna()) >= 3:
            fig_wd = go.Figure()
            fig_wd.add_trace(go.Bar(
                x=weekday_order, y=weekday_avgs["mood"],
                name="Mood", marker_color="#FF9800",
            ))
            fig_wd.add_trace(go.Bar(
                x=weekday_order, y=weekday_avgs["energy"],
                name="Energy", marker_color="#2196F3",
            ))
            fig_wd.update_layout(
                barmode='group',
                yaxis=dict(range=[0, 10.5], title="Average"),
                height=300, margin=dict(t=20, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_wd, use_container_width=True)

    else:
        st.info("Need at least 5 check-ins to show trends. Keep logging daily!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: ACHIEVEMENT BADGES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_badges:
    st.markdown("### Achievements & Milestones")

    # Gather stats for badge evaluation
    streak = get_overall_streak(user_id)
    coins = get_coin_balance(user_id)
    history = get_assessment_history(user_id)
    all_checkins = get_checkins_for_range(user_id, "2000-01-01", date.today().isoformat())
    total_checkins = len(all_checkins)

    conn = get_connection()
    try:
        total_goals = conn.execute("SELECT COUNT(*) as c FROM goals WHERE user_id = ?", (user_id,)).fetchone()["c"]
        completed_goals = conn.execute("SELECT COUNT(*) as c FROM goals WHERE user_id = ? AND status = 'completed'", (user_id,)).fetchone()["c"]
        total_habits_done = conn.execute("SELECT COUNT(*) as c FROM habit_log WHERE user_id = ? AND completed_count > 0", (user_id,)).fetchone()["c"]
        lessons_done = conn.execute("SELECT COUNT(*) as c FROM user_lesson_progress WHERE user_id = ?", (user_id,)).fetchone()["c"]
        letters_written = conn.execute("SELECT COUNT(*) as c FROM future_self_letters WHERE user_id = ?", (user_id,)).fetchone()["c"]
    finally:
        conn.close()

    latest_total = history[0]["total"] if history else 0
    first_total = history[-1]["total"] if history else 0
    score_improvement = latest_total - first_total if len(history) >= 2 else 0

    # Define badges
    badges = [
        # Consistency badges
        {"name": "First Step", "icon": "👣", "desc": "Complete your first check-in", "earned": total_checkins >= 1, "category": "Consistency"},
        {"name": "Week Warrior", "icon": "🗓️", "desc": "7-day check-in streak", "earned": streak >= 7 or total_checkins >= 7, "category": "Consistency"},
        {"name": "Fortnight Fighter", "icon": "💪", "desc": "14-day streak", "earned": streak >= 14 or total_checkins >= 20, "category": "Consistency"},
        {"name": "Monthly Master", "icon": "🏅", "desc": "30-day streak", "earned": streak >= 30 or total_checkins >= 45, "category": "Consistency"},
        {"name": "Quarterly Champion", "icon": "🏆", "desc": "90-day streak", "earned": streak >= 90 or total_checkins >= 120, "category": "Consistency"},
        {"name": "Year of Change", "icon": "⭐", "desc": "365-day streak", "earned": streak >= 365 or total_checkins >= 300, "category": "Consistency"},
        # Habit badges
        {"name": "Habit Starter", "icon": "🌱", "desc": "Complete 10 habit entries", "earned": total_habits_done >= 10, "category": "Habits"},
        {"name": "Habit Builder", "icon": "🔨", "desc": "Complete 100 habit entries", "earned": total_habits_done >= 100, "category": "Habits"},
        {"name": "Habit Machine", "icon": "⚙️", "desc": "Complete 500 habit entries", "earned": total_habits_done >= 500, "category": "Habits"},
        {"name": "Habit Legend", "icon": "🌟", "desc": "Complete 1000+ habit entries", "earned": total_habits_done >= 1000, "category": "Habits"},
        # Growth badges
        {"name": "Self-Aware", "icon": "🪞", "desc": "Complete first wheel assessment", "earned": len(history) >= 1, "category": "Growth"},
        {"name": "Growth Tracker", "icon": "📈", "desc": "Complete 5+ assessments", "earned": len(history) >= 5, "category": "Growth"},
        {"name": "Transformation", "icon": "🦋", "desc": "Improve total wheel score by 10+", "earned": score_improvement >= 10, "category": "Growth"},
        {"name": "All-Around", "icon": "🎯", "desc": "All 6 pillars at 7+ in latest assessment", "earned": latest_total >= 42 and all(s >= 7 for s in (history[0]["scores"].values() if history else [])), "category": "Growth"},
        # Goal badges
        {"name": "Goal Setter", "icon": "🎯", "desc": "Create your first goal", "earned": total_goals >= 1, "category": "Goals"},
        {"name": "Goal Crusher", "icon": "💥", "desc": "Complete 3 goals", "earned": completed_goals >= 3, "category": "Goals"},
        {"name": "Unstoppable", "icon": "🚀", "desc": "Complete 5+ goals", "earned": completed_goals >= 5, "category": "Goals"},
        # Learning badges
        {"name": "Student", "icon": "📚", "desc": "Complete first micro-lesson", "earned": lessons_done >= 1, "category": "Learning"},
        {"name": "Scholar", "icon": "🎓", "desc": "Complete 10 micro-lessons", "earned": lessons_done >= 10, "category": "Learning"},
        {"name": "Time Traveler", "icon": "💌", "desc": "Write a future self letter", "earned": letters_written >= 1, "category": "Learning"},
        # Coin badges
        {"name": "Coin Collector", "icon": "🪙", "desc": "Earn 100 LifeCoins", "earned": coins >= 100, "category": "Engagement"},
        {"name": "Coin Hoarder", "icon": "💰", "desc": "Earn 500 LifeCoins", "earned": coins >= 500, "category": "Engagement"},
    ]

    # Summary
    earned_count = sum(1 for b in badges if b["earned"])
    total_badges = len(badges)
    st.progress(earned_count / total_badges)
    st.markdown(f"**{earned_count}/{total_badges} achievements unlocked**")
    st.divider()

    # Group by category
    categories = {}
    for b in badges:
        cat = b["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(b)

    for cat, cat_badges in categories.items():
        earned_in_cat = sum(1 for b in cat_badges if b["earned"])
        st.markdown(f"#### {cat} ({earned_in_cat}/{len(cat_badges)})")
        cols = st.columns(min(4, len(cat_badges)))
        for i, badge in enumerate(cat_badges):
            with cols[i % len(cols)]:
                if badge["earned"]:
                    st.markdown(
                        f"<div style='text-align:center;padding:12px;background:#1a3d1a;border-radius:12px;margin:4px 0'>"
                        f"<div style='font-size:2em'>{badge['icon']}</div>"
                        f"<div style='font-weight:bold;color:#4CAF50;font-size:0.85em'>{badge['name']}</div>"
                        f"<div style='color:#888;font-size:0.7em'>{badge['desc']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='text-align:center;padding:12px;background:#1a1a2e;border-radius:12px;margin:4px 0;opacity:0.4'>"
                        f"<div style='font-size:2em'>🔒</div>"
                        f"<div style='font-weight:bold;color:#666;font-size:0.85em'>{badge['name']}</div>"
                        f"<div style='color:#555;font-size:0.7em'>{badge['desc']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        st.markdown("")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: HEALTH METRICS (Sleep, Recovery, Fasting)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.markdown("### Health Metrics")

    _health_range = st.selectbox("Period", ["30 Days", "90 Days", "All Time"], index=0, key="health_range")
    _health_days = {"30 Days": 30, "90 Days": 90, "All Time": 9999}[_health_range]

    # Sleep score trend
    try:
        from services.sleep_service import get_all_sleep_history
        _sleep_all = get_all_sleep_history(user_id)
        if _sleep_all:
            _cutoff = (date.today() - timedelta(days=_health_days)).isoformat()
            _sleep_filtered = [s for s in _sleep_all if s["sleep_date"] >= _cutoff]
            if _sleep_filtered:
                st.markdown("#### Sleep Score Trend")
                _s_dates = [s["sleep_date"] for s in _sleep_filtered]
                _s_scores = [s.get("sleep_score", 0) for s in _sleep_filtered]
                _s_dur = [s.get("total_sleep_min", 0) / 60 for s in _sleep_filtered]

                fig_sleep = go.Figure()
                fig_sleep.add_trace(go.Scatter(
                    x=_s_dates, y=_s_scores, mode="lines+markers",
                    name="Sleep Score", line=dict(color="#BF5AF2", width=2),
                    marker=dict(size=4),
                ))
                fig_sleep.add_trace(go.Scatter(
                    x=_s_dates, y=_s_dur, mode="lines",
                    name="Duration (h)", line=dict(color="#0A84FF", width=2, dash="dot"),
                    yaxis="y2",
                ))
                fig_sleep.update_layout(
                    height=320, margin=dict(t=20, b=40, l=40, r=40),
                    yaxis=dict(title="Score", range=[0, 105]),
                    yaxis2=dict(title="Hours", overlaying="y", side="right", range=[0, 12]),
                    legend=dict(orientation="h", y=-0.15, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_sleep, use_container_width=True)
    except Exception:
        pass

    # Recovery trend
    try:
        from services.recovery_service import get_recovery_history
        _rec_hist = get_recovery_history(user_id, days=_health_days)
        if _rec_hist and len(_rec_hist) >= 3:
            st.markdown("#### Recovery Score Trend")
            fig_rec = go.Figure()
            fig_rec.add_trace(go.Scatter(
                x=[r["date"] for r in _rec_hist],
                y=[r["score"] for r in _rec_hist],
                mode="lines+markers",
                line=dict(color="#30D158", width=2),
                marker=dict(size=4, color=[
                    "#30D158" if r["score"] >= 80 else "#FFD60A" if r["score"] >= 60 else "#FF453A"
                    for r in _rec_hist
                ]),
                fill="tozeroy", fillcolor="rgba(48,209,88,0.08)",
            ))
            fig_rec.add_hline(y=80, line_dash="dot", line_color="#30D158", opacity=0.4)
            fig_rec.add_hline(y=60, line_dash="dot", line_color="#FFD60A", opacity=0.4)
            fig_rec.update_layout(
                height=280, margin=dict(t=20, b=40, l=40, r=20),
                yaxis=dict(title="Recovery Score", range=[0, 105]),
                showlegend=False,
            )
            st.plotly_chart(fig_rec, use_container_width=True)
    except Exception:
        pass

    # Fasting history
    try:
        from services.fasting_service import get_fasting_history, get_fasting_stats
        _fasts = get_fasting_history(user_id, limit=50)
        if _fasts and len(_fasts) >= 3:
            st.markdown("#### Fasting History")
            _f_stats = get_fasting_stats(user_id, days=_health_days)
            if _f_stats:
                _fc1, _fc2, _fc3 = st.columns(3)
                with _fc1:
                    st.metric("Total Fasts", _f_stats.get("total_fasts", 0))
                with _fc2:
                    st.metric("Avg Duration", f"{_f_stats.get('avg_hours', 0):.1f}h")
                with _fc3:
                    st.metric("Completion Rate", f"{_f_stats.get('completion_rate', 0):.0f}%")

            _cutoff = (date.today() - timedelta(days=_health_days)).isoformat()
            _fasts_f = [f for f in reversed(_fasts) if f.get("start_time", "")[:10] >= _cutoff]
            if _fasts_f:
                fig_fast = go.Figure()
                fig_fast.add_trace(go.Bar(
                    x=[f["start_time"][:10] for f in _fasts_f],
                    y=[f.get("actual_hours", 0) for f in _fasts_f],
                    marker_color=["#30D158" if f.get("completed") else "#FF9F0A" for f in _fasts_f],
                ))
                fig_fast.update_layout(
                    height=250, margin=dict(t=20, b=40, l=40, r=20),
                    yaxis=dict(title="Hours"),
                    showlegend=False,
                )
                st.plotly_chart(fig_fast, use_container_width=True)
    except Exception:
        pass

    if not any([
        locals().get("_sleep_filtered"),
        locals().get("_rec_hist"),
        locals().get("_fasts"),
    ]):
        st.info("No health metrics data yet. Log sleep, check in daily, and try fasting to see data here.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: BODY & LABS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_body:
    st.markdown("### Body Composition & Lab Results")

    # Weight trend
    try:
        from services.body_metrics_service import get_body_metrics_history, get_goal_weight, compute_bmi as _compute_bmi
        _bm_hist = get_body_metrics_history(user_id)
        if _bm_hist:
            st.markdown("#### Weight Trend")
            _bm_df = pd.DataFrame(_bm_hist)
            _bm_df["log_date"] = pd.to_datetime(_bm_df["log_date"])
            _weight_data = _bm_df[_bm_df["weight_kg"].notna()]

            if len(_weight_data) >= 1:
                fig_wt = go.Figure()
                fig_wt.add_trace(go.Scatter(
                    x=_weight_data["log_date"], y=_weight_data["weight_kg"],
                    mode="lines+markers", name="Weight",
                    line=dict(color="#2196F3", width=2),
                    marker=dict(size=6),
                ))
                _gw = get_goal_weight(user_id)
                if _gw:
                    fig_wt.add_hline(y=_gw, line_dash="dash", line_color="#4CAF50",
                                     annotation_text=f"Goal: {_gw}kg")
                fig_wt.update_layout(
                    height=300, margin=dict(t=20, b=40, l=40, r=20),
                    yaxis=dict(title="Weight (kg)"),
                    showlegend=False,
                )
                st.plotly_chart(fig_wt, use_container_width=True)

            # BMI trend
            _heights = _bm_df[_bm_df["height_cm"].notna()]
            if len(_heights) > 0 and len(_weight_data) >= 2:
                _h = _heights.iloc[-1]["height_cm"]
                _bm_df["bmi"] = _bm_df["weight_kg"].apply(lambda w: _compute_bmi(w, _h))
                _bmi_data = _bm_df[_bm_df["bmi"].notna()]
                if len(_bmi_data) >= 2:
                    st.markdown("#### BMI Trend")
                    fig_bmi = go.Figure()
                    fig_bmi.add_trace(go.Scatter(
                        x=_bmi_data["log_date"], y=_bmi_data["bmi"],
                        mode="lines+markers", line=dict(color="#FF9800", width=2),
                        marker=dict(size=5),
                    ))
                    fig_bmi.add_hline(y=25, line_dash="dot", line_color="#FF9800", opacity=0.4)
                    fig_bmi.add_hline(y=18.5, line_dash="dot", line_color="#FFC107", opacity=0.4)
                    fig_bmi.update_layout(
                        height=260, margin=dict(t=20, b=40, l=40, r=20),
                        yaxis=dict(title="BMI"),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_bmi, use_container_width=True)
        else:
            st.info("No body metrics data yet. Log weight on the Body Metrics page.")
    except Exception:
        pass

    # Biomarkers
    try:
        from services.biomarker_service import get_biomarker_results
        _bio = get_biomarker_results(user_id)
        if _bio:
            st.markdown("#### Latest Biomarker Results")
            for b in _bio[:15]:
                _val = b.get("value", 0)
                _name = b.get("name", b.get("code", ""))
                _unit = b.get("unit", "")
                _status = b.get("status", "normal")
                _sc = "#30D158" if _status == "optimal" else "#FFD60A" if _status == "normal" else "#FF453A"
                _row = (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:8px 12px;margin-bottom:4px;background:rgba(28,28,30,0.8);'
                    f'border-radius:8px;border-left:3px solid {_sc}">'
                    f'<span style="font-size:13px;color:rgba(255,255,255,0.8)">{_name}</span>'
                    f'<span style="font-size:14px;font-weight:600;color:{_sc}">{_val} {_unit}</span>'
                    f'</div>'
                )
                st.markdown(_row, unsafe_allow_html=True)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: NUTRITION
# ═══════════════════════════════════════════════════════════════════════════════
with tab_nutrition:
    st.markdown("### Nutrition Analytics")

    _nut_range = st.selectbox("Period", ["7 Days", "30 Days", "90 Days"], index=1, key="nut_range")
    _nut_days = {"7 Days": 7, "30 Days": 30, "90 Days": 90}[_nut_range]

    # Calorie trend
    try:
        from services.calorie_service import get_daily_totals
        _cal_data = get_daily_totals(user_id, days=_nut_days)
        if _cal_data:
            st.markdown("#### Daily Calorie Intake")
            _cal_dates = [c["summary_date"] for c in _cal_data]
            _cal_vals = [c.get("total_calories", 0) for c in _cal_data]

            fig_cal = go.Figure()
            fig_cal.add_trace(go.Bar(
                x=_cal_dates, y=_cal_vals,
                marker_color="#FF9F0A", opacity=0.8,
            ))
            fig_cal.update_layout(
                height=280, margin=dict(t=20, b=40, l=40, r=20),
                yaxis=dict(title="Calories"),
                showlegend=False,
            )
            st.plotly_chart(fig_cal, use_container_width=True)

            # Macro breakdown
            _has_macros = any(c.get("total_protein_g", 0) > 0 for c in _cal_data)
            if _has_macros:
                st.markdown("#### Macro Breakdown Over Time")
                fig_mac = go.Figure()
                fig_mac.add_trace(go.Scatter(
                    x=_cal_dates,
                    y=[c.get("total_protein_g", 0) for c in _cal_data],
                    mode="lines", name="Protein (g)", line=dict(color="#FF453A", width=2),
                    stackgroup="macros",
                ))
                fig_mac.add_trace(go.Scatter(
                    x=_cal_dates,
                    y=[c.get("total_carbs_g", 0) for c in _cal_data],
                    mode="lines", name="Carbs (g)", line=dict(color="#FFD60A", width=2),
                    stackgroup="macros",
                ))
                fig_mac.add_trace(go.Scatter(
                    x=_cal_dates,
                    y=[c.get("total_fat_g", 0) for c in _cal_data],
                    mode="lines", name="Fat (g)", line=dict(color="#0A84FF", width=2),
                    stackgroup="macros",
                ))
                fig_mac.update_layout(
                    height=280, margin=dict(t=20, b=40, l=40, r=20),
                    yaxis=dict(title="Grams"),
                    legend=dict(orientation="h", y=-0.15, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_mac, use_container_width=True)

            # Averages
            _avg_cal = sum(_cal_vals) / len(_cal_vals) if _cal_vals else 0
            _avg_prot = sum(c.get("total_protein_g", 0) for c in _cal_data) / len(_cal_data) if _cal_data else 0
            _avg_carb = sum(c.get("total_carbs_g", 0) for c in _cal_data) / len(_cal_data) if _cal_data else 0
            _avg_fat = sum(c.get("total_fat_g", 0) for c in _cal_data) / len(_cal_data) if _cal_data else 0
            _nc1, _nc2, _nc3, _nc4 = st.columns(4)
            with _nc1:
                st.metric("Avg Calories", f"{_avg_cal:.0f}")
            with _nc2:
                st.metric("Avg Protein", f"{_avg_prot:.0f}g")
            with _nc3:
                st.metric("Avg Carbs", f"{_avg_carb:.0f}g")
            with _nc4:
                st.metric("Avg Fat", f"{_avg_fat:.0f}g")
        else:
            st.info("No nutrition data yet. Log meals on the Nutrition page.")
    except Exception:
        st.info("No nutrition data yet. Log meals on the Nutrition page.")

    # FODMAP exposure (if SIBO data exists)
    try:
        from services.sibo_service import get_food_history as _sibo_food_hist
        _sibo_foods = _sibo_food_hist(user_id, days=_nut_days)
        if _sibo_foods and len(_sibo_foods) >= 5:
            import json as _json
            st.markdown("#### FODMAP Exposure by Group")
            _group_counts = {}
            for f in _sibo_foods:
                _groups = f.get("fodmap_groups")
                if _groups:
                    try:
                        _parsed = _json.loads(_groups) if isinstance(_groups, str) else _groups
                        for g in _parsed:
                            _group_counts[g] = _group_counts.get(g, 0) + 1
                    except Exception:
                        pass
            if _group_counts:
                fig_fodmap = go.Figure()
                _g_names = list(_group_counts.keys())
                _g_vals = list(_group_counts.values())
                _fodmap_colors = {
                    "fructans": "#FF9F0A", "gos": "#FF6482", "lactose": "#64D2FF",
                    "fructose": "#30D158", "sorbitol": "#BF5AF2", "mannitol": "#5E5CE6",
                }
                fig_fodmap.add_trace(go.Bar(
                    x=_g_names, y=_g_vals,
                    marker_color=[_fodmap_colors.get(g, "#888") for g in _g_names],
                ))
                fig_fodmap.update_layout(
                    height=250, margin=dict(t=20, b=40, l=40, r=20),
                    yaxis=dict(title="Food Entries"),
                    showlegend=False,
                )
                st.plotly_chart(fig_fodmap, use_container_width=True)
    except Exception:
        pass
