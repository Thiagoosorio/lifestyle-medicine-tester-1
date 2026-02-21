import plotly.graph_objects as go
from config.settings import PILLARS, PILLAR_COLORS


def create_wheel_chart(scores: dict, title: str = "Wheel of Life", height: int = 450) -> go.Figure:
    """Create a radar chart for a single assessment. scores = {pillar_id: score}."""
    categories = [PILLARS[pid]["display_name"] for pid in sorted(scores.keys())]
    values = [scores[pid] for pid in sorted(scores.keys())]
    # Close the polygon
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(76, 175, 80, 0.2)",
        line=dict(color="#4CAF50", width=2),
        marker=dict(size=8, color="#4CAF50"),
        name="Current",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickvals=[2, 4, 6, 8, 10]),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=False,
        title=dict(text=title, x=0.5, font=dict(size=16)),
        height=height,
        margin=dict(t=60, b=20, l=60, r=60),
    )
    return fig


def create_comparison_chart(assessments: list, height: int = 500) -> go.Figure:
    """Overlay multiple assessments. assessments = [{scores: {pid: score}, label: str, color: str}]."""
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63"]
    opacities = [0.25, 0.15, 0.1, 0.08]

    fig = go.Figure()
    for i, assessment in enumerate(assessments):
        scores = assessment["scores"]
        label = assessment.get("label", f"Assessment {i+1}")
        color = colors[i % len(colors)]

        categories = [PILLARS[pid]["display_name"] for pid in sorted(scores.keys())]
        values = [scores[pid] for pid in sorted(scores.keys())]
        categories.append(categories[0])
        values.append(values[0])

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(color)}, {opacities[i % len(opacities)]})",
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            name=label,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickvals=[2, 4, 6, 8, 10]),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        title=dict(text="Wheel of Life Comparison", x=0.5, font=dict(size=16)),
        height=height,
        margin=dict(t=60, b=60, l=60, r=60),
    )
    return fig


def create_trend_chart(history: list, height: int = 400) -> go.Figure:
    """Line chart of pillar scores over time. history = [{assessed_at, scores}]."""
    if not history:
        return go.Figure()

    # Reverse to chronological order
    history = list(reversed(history))

    fig = go.Figure()
    for pid in sorted(PILLARS.keys()):
        dates = [h["assessed_at"][:10] for h in history if pid in h["scores"]]
        values = [h["scores"][pid] for h in history if pid in h["scores"]]
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode="lines+markers",
            name=PILLARS[pid]["display_name"],
            line=dict(color=PILLARS[pid]["color"], width=2),
            marker=dict(size=6),
        ))

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Score",
        yaxis=dict(range=[0, 10.5], dtick=2),
        title=dict(text="Pillar Scores Over Time", x=0.5, font=dict(size=16)),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(t=60, b=80, l=40, r=20),
    )
    return fig


def _hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"
