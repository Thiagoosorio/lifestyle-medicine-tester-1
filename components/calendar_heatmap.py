import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
import calendar


def render_calendar_heatmap(year: int, month: int, day_values: dict, height: int = 300):
    """Render a monthly calendar heatmap.
    day_values = {date_str: float} where float is 0.0-1.0 (completion rate).
    """
    cal = calendar.Calendar(firstweekday=0)  # Monday start
    month_days = list(cal.itermonthdates(year, month))

    # Build grid: weeks as rows, days as columns
    weeks = []
    week = []
    for d in month_days:
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []

    z_values = []
    hover_text = []
    for week in weeks:
        z_row = []
        hover_row = []
        for d in week:
            if d.month == month:
                val = day_values.get(d.isoformat(), 0)
                z_row.append(val)
                hover_row.append(f"{d.strftime('%b %d')}: {val:.0%}")
            else:
                z_row.append(None)
                hover_row.append("")
        z_values.append(z_row)
        hover_text.append(hover_row)

    # Annotate with day numbers
    annotations = []
    for wi, week in enumerate(weeks):
        for di, d in enumerate(week):
            if d.month == month:
                annotations.append(dict(
                    x=di, y=wi,
                    text=str(d.day),
                    showarrow=False,
                    font=dict(size=10, color="white" if day_values.get(d.isoformat(), 0) > 0.5 else "black"),
                ))

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        y=[f"Week {i+1}" for i in range(len(weeks))],
        hovertext=hover_text,
        hoverinfo="text",
        colorscale=[[0, "#f5f5f5"], [0.3, "#C8E6C9"], [0.6, "#66BB6A"], [1.0, "#2E7D32"]],
        zmin=0, zmax=1,
        showscale=True,
        colorbar=dict(title="Completion", tickformat=".0%"),
    ))

    fig.update_layout(
        title=f"{calendar.month_name[month]} {year}",
        height=height,
        yaxis=dict(autorange="reversed"),
        annotations=annotations,
        margin=dict(t=40, b=20, l=60, r=20),
    )

    st.plotly_chart(fig, use_container_width=True)
