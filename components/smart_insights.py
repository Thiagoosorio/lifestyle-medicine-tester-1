"""Smart Insights UI component.

Renders personalized correlation insights, mood-booster charts, and pillar
correlation heatmaps using Streamlit + Plotly.

All HTML uses inline styles (no custom CSS classes) for Streamlit compatibility.
"""

import streamlit as st
import plotly.graph_objects as go
from services.correlation_engine import (
    get_pattern_insights,
    get_habit_mood_correlations,
    get_pillar_correlations,
    get_weekly_digest,
)
from config.settings import PILLARS, PILLAR_COLORS

# ── Styling constants ──────────────────────────────────────────────────────

INSIGHT_ICONS = {
    "mood": "&#127774;",      # sun
    "sleep": "&#128164;",     # zzz
    "trend": "&#128200;",     # chart up
    "habit": "&#9989;",       # check mark
    "streak": "&#128293;",    # fire
    "pillar": "&#128204;",    # pin
    "weekend": "&#127749;",   # sunset
    "default": "&#128161;",   # light bulb
}

# Inline style strings for reuse
_CARD_STYLE = (
    "border-radius:10px;padding:16px 20px;margin-bottom:12px;"
    "color:#e0e0e0;font-size:0.95rem;line-height:1.5;"
    "box-shadow:0 2px 8px rgba(0,0,0,0.25)"
)

_DIGEST_CARD_STYLE = (
    "background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);"
    "border-radius:12px;padding:20px 24px;margin-bottom:16px;"
    "color:#e0e0e0;box-shadow:0 4px 12px rgba(0,0,0,0.3)"
)

_DIGEST_STAT_STYLE = (
    "display:inline-block;text-align:center;padding:8px 16px;margin:4px;"
    "border-radius:8px;background:rgba(255,255,255,0.06);min-width:120px"
)

# ── Color palette for cards ────────────────────────────────────────────────

CARD_COLORS = [
    "#42a5f5", "#66bb6a", "#ffa726", "#ab47bc",
    "#ef5350", "#26c6da", "#ec407a", "#8d6e63",
]


def _pick_icon(text: str) -> str:
    """Choose an icon based on keywords in the insight text."""
    lower = text.lower()
    if "mood" in lower and ("booster" in lower or "top" in lower):
        return INSIGHT_ICONS["habit"]
    if "streak" in lower:
        return INSIGHT_ICONS["streak"]
    if "sleep" in lower:
        return INSIGHT_ICONS["sleep"]
    if "weekend" in lower or "weekday" in lower:
        return INSIGHT_ICONS["weekend"]
    if "trend" in lower or "upward" in lower or "downward" in lower:
        return INSIGHT_ICONS["trend"]
    if "correlated" in lower or "correlation" in lower:
        return INSIGHT_ICONS["pillar"]
    if "mood" in lower:
        return INSIGHT_ICONS["mood"]
    return INSIGHT_ICONS["default"]


def _trend_badge(trend: str) -> str:
    """Return an HTML badge for a trend value using inline styles."""
    if trend == "improving":
        return '<span style="color:#66bb6a">&#9650; Improving</span>'
    elif trend == "declining":
        return '<span style="color:#ef5350">&#9660; Declining</span>'
    return '<span style="color:#ffca28">&#9644; Stable</span>'


# ── Main render function ───────────────────────────────────────────────────

def render_smart_insights(user_id: int):
    """Render the full Smart Insights section for a user."""

    # ── Weekly Digest ──────────────────────────────────────────────────────
    digest = get_weekly_digest(user_id)
    _render_weekly_digest(digest)

    st.markdown("---")

    # ── Pattern Insights ───────────────────────────────────────────────────
    st.subheader("Pattern Insights")

    insights = get_pattern_insights(user_id)
    if insights:
        for idx, text in enumerate(insights):
            color = CARD_COLORS[idx % len(CARD_COLORS)]
            icon = _pick_icon(text)
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1e1e2f 0%,#2a2a40 100%);'
                f'border-left:4px solid {color};{_CARD_STYLE}">'
                f'<span style="font-size:1.3rem;margin-right:8px;vertical-align:middle">{icon}</span>{text}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "Not enough data to generate insights yet. "
            "Keep logging your daily check-ins and habits!"
        )

    st.markdown("---")

    # ── Charts ─────────────────────────────────────────────────────────────
    correlations = get_habit_mood_correlations(user_id)

    col1, col2 = st.columns(2)
    with col1:
        _render_mood_booster_chart(correlations)
    with col2:
        _render_pillar_heatmap(user_id)


# ── Weekly Digest card ─────────────────────────────────────────────────────

def _render_weekly_digest(digest: dict):
    """Render the weekly digest as a styled card with inline styles."""
    st.subheader("Weekly Digest")

    mood_badge = _trend_badge(digest["mood_trend"])
    energy_badge = _trend_badge(digest["energy_trend"])

    stats_html = ""

    if digest["strongest_pillar"]:
        stats_html += (
            f'<div style="{_DIGEST_STAT_STYLE}">'
            f'<div style="font-size:0.75rem;color:rgba(235,235,245,0.78);text-transform:uppercase;letter-spacing:0.5px">Strongest Pillar</div>'
            f'<div style="font-size:1.1rem;font-weight:600;margin-top:2px;color:#66bb6a">{digest["strongest_pillar"]}</div>'
            f'</div>'
        )
    if digest["weakest_pillar"]:
        stats_html += (
            f'<div style="{_DIGEST_STAT_STYLE}">'
            f'<div style="font-size:0.75rem;color:rgba(235,235,245,0.78);text-transform:uppercase;letter-spacing:0.5px">Needs Attention</div>'
            f'<div style="font-size:1.1rem;font-weight:600;margin-top:2px;color:#ef5350">{digest["weakest_pillar"]}</div>'
            f'</div>'
        )
    if digest["top_habit"]:
        stats_html += (
            f'<div style="{_DIGEST_STAT_STYLE}">'
            f'<div style="font-size:0.75rem;color:rgba(235,235,245,0.78);text-transform:uppercase;letter-spacing:0.5px">Top Habit</div>'
            f'<div style="font-size:1.1rem;font-weight:600;margin-top:2px;color:#42a5f5">{digest["top_habit"]}</div>'
            f'</div>'
        )

    stats_html += (
        f'<div style="{_DIGEST_STAT_STYLE}">'
        f'<div style="font-size:0.75rem;color:rgba(235,235,245,0.78);text-transform:uppercase;letter-spacing:0.5px">Mood Trend</div>'
        f'<div style="font-size:1.1rem;font-weight:600;margin-top:2px">{mood_badge}</div>'
        f'</div>'
    )
    stats_html += (
        f'<div style="{_DIGEST_STAT_STYLE}">'
        f'<div style="font-size:0.75rem;color:rgba(235,235,245,0.78);text-transform:uppercase;letter-spacing:0.5px">Energy Trend</div>'
        f'<div style="font-size:1.1rem;font-weight:600;margin-top:2px">{energy_badge}</div>'
        f'</div>'
    )

    st.markdown(
        f'<div style="{_DIGEST_CARD_STYLE}">'
        f'<h4 style="margin:0 0 12px 0;color:#90caf9">&#128202; This Week at a Glance</h4>'
        f'{stats_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Insight + recommendation as info/success boxes
    if digest.get("insight"):
        st.info(f"**Insight:** {digest['insight']}")
    if digest.get("recommendation"):
        st.success(f"**Recommendation:** {digest['recommendation']}")


# ── Top Mood Boosters horizontal bar chart ─────────────────────────────────

def _render_mood_booster_chart(correlations: list[dict]):
    """Horizontal bar chart showing mood difference for each habit."""
    st.markdown("##### Top Mood Boosters")

    # Filter to habits with positive mood diff and take top 10
    positive = [c for c in correlations if c["mood_diff"] > 0]
    if not positive:
        st.caption("No mood-boosting habits detected yet. Keep tracking!")
        return

    data = positive[:10]
    # Reverse so highest is at top in horizontal bar chart
    data = list(reversed(data))

    names = [d["habit_name"] for d in data]
    mood_diffs = [d["mood_diff"] for d in data]

    # Color by correlation strength
    colors = []
    for d in data:
        if d["correlation_strength"] == "strong":
            colors.append("#66bb6a")
        elif d["correlation_strength"] == "moderate":
            colors.append("#ffa726")
        else:
            colors.append("#90a4ae")

    fig = go.Figure(data=go.Bar(
        x=mood_diffs,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"+{v:.1f}" for v in mood_diffs],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Mood boost: +%{x:.2f} points<br>"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        xaxis_title="Mood Difference (points)",
        yaxis_title="",
        height=max(250, len(data) * 40 + 80),
        margin=dict(t=10, b=40, l=10, r=40),
        xaxis=dict(range=[0, max(mood_diffs) * 1.3 if mood_diffs else 3]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend
    st.caption(
        "Color key: "
        ":green[Strong (>1.5)] | "
        ":orange[Moderate (>0.8)] | "
        "Weak"
    )


# ── Pillar Correlation Heatmap ─────────────────────────────────────────────

def _render_pillar_heatmap(user_id: int):
    """Render a Plotly heatmap of pairwise pillar correlations."""
    st.markdown("##### Pillar Correlations")

    corrs = get_pillar_correlations(user_id)
    pillar_ids = sorted(PILLARS.keys())
    pillar_names = [PILLARS[pid]["display_name"] for pid in pillar_ids]
    n = len(pillar_ids)

    if not corrs:
        st.caption(
            "Not enough data for pillar correlations. "
            "Log at least 5 check-ins to see this chart."
        )
        return

    # Build NxN matrix (only upper triangle has data; mirror it)
    z = [[0.0] * n for _ in range(n)]
    annotations = []

    for i in range(n):
        for j in range(n):
            if i == j:
                z[i][j] = 1.0
                annotations.append(dict(
                    x=j, y=i, text="1.0",
                    showarrow=False, font=dict(size=11, color="white"),
                ))
            else:
                pid_a = pillar_ids[min(i, j)]
                pid_b = pillar_ids[max(i, j)]
                r_val = corrs.get((pid_a, pid_b), 0.0)
                z[i][j] = r_val
                if r_val != 0.0:
                    text_color = "white" if abs(r_val) > 0.5 else "#ccc"
                    annotations.append(dict(
                        x=j, y=i, text=f"{r_val:.2f}",
                        showarrow=False,
                        font=dict(size=10, color=text_color),
                    ))

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=pillar_names,
        y=pillar_names,
        colorscale=[
            [0.0, "#ef5350"],
            [0.25, "#ffcdd2"],
            [0.5, "#fafafa"],
            [0.75, "#c8e6c9"],
            [1.0, "#66bb6a"],
        ],
        zmin=-1,
        zmax=1,
        colorbar=dict(
            title="r",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1", "-0.5", "0", "0.5", "1"],
        ),
        hovertemplate=(
            "%{y} vs %{x}<br>"
            "r = %{z:.2f}<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=400,
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(side="bottom", tickangle=-45),
        yaxis=dict(autorange="reversed"),
        annotations=annotations,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Shows Pearson correlations between your daily pillar ratings. "
        "Only pairs with |r| > 0.3 are highlighted."
    )
