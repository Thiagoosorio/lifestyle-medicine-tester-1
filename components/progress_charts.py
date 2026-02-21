import plotly.graph_objects as go
import streamlit as st


def render_mood_energy_chart(checkins: list, height: int = 350):
    """Line chart of mood and energy over time."""
    if not checkins:
        st.caption("No check-in data to display.")
        return

    dates = [c["checkin_date"] for c in checkins]
    moods = [c.get("mood") for c in checkins]
    energies = [c.get("energy") for c in checkins]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=moods, mode="lines+markers",
        name="Mood", line=dict(color="#FF9800", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=energies, mode="lines+markers",
        name="Energy", line=dict(color="#2196F3", width=2),
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 10.5], dtick=2, title="Rating"),
        xaxis_title="Date",
        title="Mood & Energy Over Time",
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=60, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_habit_completion_chart(daily_rates: dict, height: int = 300):
    """Bar chart of daily habit completion rates. daily_rates = {date_str: float}."""
    if not daily_rates:
        st.caption("No habit data to display.")
        return

    dates = sorted(daily_rates.keys())
    values = [daily_rates[d] for d in dates]
    colors = ["#4CAF50" if v >= 0.7 else "#FFC107" if v >= 0.4 else "#F44336" for v in values]

    fig = go.Figure(data=go.Bar(
        x=dates, y=values,
        marker_color=colors,
        hovertemplate="%{x}<br>%{y:.0%}<extra></extra>",
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 1.05], tickformat=".0%", title="Completion Rate"),
        xaxis_title="Date",
        title="Daily Habit Completion",
        height=height,
        margin=dict(t=40, b=40, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_pillar_trends(checkins: list, height: int = 400):
    """Line chart of daily pillar ratings over time."""
    if not checkins:
        st.caption("No pillar rating data to display.")
        return

    from config.settings import PILLARS
    pillar_fields = [
        (1, "nutrition_rating"), (2, "activity_rating"), (3, "sleep_rating"),
        (4, "stress_rating"), (5, "connection_rating"), (6, "substance_rating"),
    ]

    fig = go.Figure()
    dates = [c["checkin_date"] for c in checkins]

    for pid, field in pillar_fields:
        values = [c.get(field) for c in checkins]
        fig.add_trace(go.Scatter(
            x=dates, y=values, mode="lines+markers",
            name=PILLARS[pid]["display_name"],
            line=dict(color=PILLARS[pid]["color"], width=2),
            marker=dict(size=5),
        ))

    fig.update_layout(
        yaxis=dict(range=[0, 10.5], dtick=2, title="Rating"),
        xaxis_title="Date",
        title="Daily Pillar Ratings Over Time",
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(t=40, b=80, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)
