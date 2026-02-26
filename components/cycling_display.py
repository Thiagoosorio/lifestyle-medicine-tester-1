"""Display components for the Cycling Training prescription page."""

from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from components.custom_theme import APPLE
from config.cycling_data import POWER_ZONES, WORKOUT_TYPES, DIFFICULTY_SURVEY_OPTIONS

A = APPLE


# ── Zone Color Helper ──────────────────────────────────────────────────────

def _pct_to_zone_color(power_pct: float) -> str:
    """Map a power fraction (e.g. 0.92) to the corresponding zone color."""
    pct_int = int(power_pct * 100)
    for zone in POWER_ZONES.values():
        if zone["min_pct"] <= pct_int <= zone["max_pct"]:
            return zone["color"]
    return "#9E9E9E"


# ── FTP Card ───────────────────────────────────────────────────────────────

def render_ftp_card(profile: dict | None) -> None:
    """Render a prominent FTP display card."""
    if not profile:
        html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:4px solid {A["label_tertiary"]};border-radius:{A["radius_xl"]};'
            f'padding:20px;text-align:center">'
            f'<div style="font-size:13px;color:{A["label_tertiary"]}">FTP not set</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:4px">'
            f'Go to Settings to enter your FTP</div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    ftp = profile.get("ftp_watts", 200)
    tested = profile.get("ftp_tested_date", "")
    athlete = profile.get("athlete_type", "All-Around")
    wkg = ""
    if profile.get("weight_kg"):
        wkg_val = ftp / profile["weight_kg"]
        wkg = f" &middot; {wkg_val:.2f} W/kg"

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:4px solid {A["blue"]};border-radius:{A["radius_xl"]};'
        f'padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.06)">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["blue"]};margin-bottom:6px">'
        f'Functional Threshold Power</div>'
        f'<div style="font-size:40px;font-weight:800;color:{A["label_primary"]};'
        f'line-height:1;margin-bottom:4px">{ftp}<span style="font-size:16px;'
        f'font-weight:400;color:{A["label_secondary"]}"> W</span></div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]}">'
        f'<span style="background:{A["blue"]}15;color:{A["blue"]};padding:2px 8px;'
        f'border-radius:20px;font-weight:600;font-size:11px">{athlete}</span>'
        f'<span style="color:{A["label_tertiary"]};margin-left:8px">'
        f'{("Tested " + tested) if tested else "Enter FTP in Settings"}{wkg}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Power Zones Table ──────────────────────────────────────────────────────

def render_zones_table(zones: dict) -> None:
    """Render a 7-row power zone reference table."""
    rows = ""
    for key, zone in zones.items():
        min_w = zone.get("min_watts", 0)
        max_w = zone.get("max_watts", 0)
        color = zone["color"]
        bar_width = min((zone["max_pct"] - zone["min_pct"]) * 1.8, 100)
        rows += (
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:9px 0;border-bottom:1px solid {A["separator"]}30">'
            f'<div style="min-width:28px;height:20px;background:{color};'
            f'border-radius:4px;display:flex;align-items:center;justify-content:center;'
            f'font-size:10px;font-weight:700;color:#fff">{key.upper()}</div>'
            f'<div style="flex:1.5;font-size:12px;font-weight:600;color:{A["label_primary"]}">'
            f'{zone["name"]}</div>'
            f'<div style="flex:1;font-size:12px;color:{A["label_secondary"]};text-align:right">'
            f'{min_w}–{max_w} W</div>'
            f'<div style="flex:2;margin-left:8px">'
            f'<div style="background:rgba(0,0,0,0.06);border-radius:999px;height:6px">'
            f'<div style="width:{bar_width:.0f}%;background:{color};height:6px;border-radius:999px"></div>'
            f'</div></div>'
            f'<div style="flex:3;font-size:11px;color:{A["label_tertiary"]};line-height:14px">'
            f'{zone["description"][:60]}{"…" if len(zone["description"])>60 else ""}</div>'
            f'</div>'
        )
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:10px">'
        f'Power Zones</div>'
        f'{rows}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── PMC Chart ──────────────────────────────────────────────────────────────

def render_pmc_chart(pmc_data: list[dict]) -> None:
    """Render the Performance Management Chart (CTL/ATL/TSB + daily TSS)."""
    if not pmc_data:
        st.caption("No ride data yet. Log rides to see your PMC chart.")
        return

    dates = [d["date"] for d in pmc_data]
    ctl_vals = [d["ctl"] for d in pmc_data]
    atl_vals = [d["atl"] for d in pmc_data]
    tsb_vals = [d["tsb"] for d in pmc_data]
    tss_vals = [d["tss"] for d in pmc_data]

    fig = go.Figure()

    # Daily TSS bars (background, secondary y-axis)
    fig.add_trace(go.Bar(
        x=dates, y=tss_vals,
        name="Daily TSS",
        marker_color="rgba(0,0,0,0.10)",
        yaxis="y2",
        hovertemplate="%{x}<br>TSS: %{y:.0f}<extra></extra>",
    ))

    # CTL — Fitness (blue)
    fig.add_trace(go.Scatter(
        x=dates, y=ctl_vals,
        name="CTL — Fitness",
        line=dict(color=A["blue"], width=2.5),
        hovertemplate="%{x}<br>CTL: %{y:.1f}<extra></extra>",
    ))

    # ATL — Fatigue (orange)
    fig.add_trace(go.Scatter(
        x=dates, y=atl_vals,
        name="ATL — Fatigue",
        line=dict(color=A["orange"], width=2, dash="dot"),
        hovertemplate="%{x}<br>ATL: %{y:.1f}<extra></extra>",
    ))

    # TSB — Form (green fill above zero, red below)
    fig.add_trace(go.Scatter(
        x=dates, y=tsb_vals,
        name="TSB — Form",
        line=dict(color=A["green"], width=1.5),
        fill="tozeroy",
        fillcolor="rgba(30,142,62,0.10)",
        hovertemplate="%{x}<br>TSB: %{y:+.1f}<extra></extra>",
    ))

    fig.update_layout(
        height=360,
        plot_bgcolor=A["chart_bg"],
        paper_bgcolor=A["chart_bg"],
        font=dict(family=A["font_text"], color=A["chart_text"], size=11),
        legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5),
        margin=dict(t=20, b=70, l=50, r=50),
        xaxis=dict(gridcolor=A["chart_grid"], showgrid=True),
        yaxis=dict(
            title="CTL / ATL / TSB",
            gridcolor=A["chart_grid"],
            zeroline=True,
            zerolinecolor="rgba(0,0,0,0.15)",
        ),
        yaxis2=dict(
            title="Daily TSS",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, max(tss_vals) * 4 if any(v > 0 for v in tss_vals) else 100],
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Interval Diagram ───────────────────────────────────────────────────────

def render_interval_diagram(intervals: list, ftp_watts: int) -> None:
    """Render a horizontal colour-coded bar showing workout intervals."""
    if not intervals:
        return
    total_sec = sum(iv.get("duration_sec", 0) for iv in intervals)
    if total_sec == 0:
        return

    blocks = ""
    for iv in intervals:
        dur = iv.get("duration_sec", 0)
        pct = iv.get("power_pct", 0.55)
        label = iv.get("label", "")
        watts = round(ftp_watts * pct)
        width = max(dur / total_sec * 100, 0.5)
        color = _pct_to_zone_color(pct)
        m, s = divmod(dur, 60)
        tooltip = f"{label} — {int(pct*100)}% FTP ({watts}W) — {m}:{s:02d}"
        blocks += (
            f'<div style="width:{width:.2f}%;height:32px;background:{color};'
            f'display:inline-block;vertical-align:top;'
            f'border-right:1px solid rgba(255,255,255,0.25)" '
            f'title="{tooltip}"></div>'
        )

    html = (
        f'<div style="width:100%;border-radius:{A["radius_sm"]};overflow:hidden;'
        f'display:flex;margin:8px 0 2px 0;box-shadow:0 1px 2px rgba(0,0,0,0.08)">'
        f'{blocks}'
        f'</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'Hover bars for interval details &middot; '
        f'Total: {total_sec//60} min</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Workout Card ───────────────────────────────────────────────────────────

def render_workout_card(workout: dict, ftp_watts: int) -> None:
    """Render a structured workout card with type badge, stats, and interval diagram."""
    wtype = workout.get("type", "endurance")
    type_info = WORKOUT_TYPES.get(wtype, WORKOUT_TYPES["endurance"])
    color = type_info["color"]
    icon = type_info["icon"]

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-top:3px solid {color};border-radius:{A["radius_lg"]};'
        f'padding:14px;margin-bottom:4px">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        f'margin-bottom:6px">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]}">'
        f'{workout.get("name","")}</div>'
        f'<span style="font-size:10px;font-weight:600;padding:3px 10px;'
        f'border-radius:20px;background:{color}18;color:{color};white-space:nowrap">'
        f'{icon} {type_info["label"]}</span>'
        f'</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-bottom:8px">'
        f'{workout.get("duration_min",0)} min &middot; '
        f'~{workout.get("tss_estimate",0)} TSS &middot; '
        f'Level {workout.get("difficulty_level",1.0):.1f} / 10</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px;'
        f'margin-bottom:10px">{workout.get("description","")}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    render_interval_diagram(workout.get("intervals", []), ftp_watts)


# ── Weekly Plan Calendar ───────────────────────────────────────────────────

def render_weekly_plan(week_workouts: list, today: date) -> None:
    """Render a 7-column weekly calendar with workout assignments."""
    # Build a dict keyed by date string
    by_date: dict[str, dict] = {}
    for w in week_workouts:
        by_date[w.get("date", "")] = w

    from config.cycling_data import WORKOUT_LIBRARY_BY_ID
    week_start = today - timedelta(days=today.weekday())  # Monday

    cols = st.columns(7)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, col in enumerate(cols):
        day = week_start + timedelta(days=i)
        d_str = day.isoformat()
        is_today = day == today
        workout_entry = by_date.get(d_str)

        with col:
            border = f"2px solid {A['blue']}" if is_today else f"1px solid {A['separator']}"
            bg = f"{A['blue']}08" if is_today else A["bg_elevated"]

            if workout_entry:
                workout = WORKOUT_LIBRARY_BY_ID.get(workout_entry.get("workout_id", ""), {})
                wtype = workout.get("type", "endurance")
                type_info = WORKOUT_TYPES.get(wtype, {})
                color = type_info.get("color", A["label_tertiary"])
                status = workout_entry.get("status", "scheduled")
                status_badge = "&#10003;" if status == "completed" else ("&#8680;" if status == "rescheduled" else "")
                st.markdown(
                    f'<div style="border:{border};background:{bg};'
                    f'border-radius:{A["radius_md"]};padding:8px 6px;text-align:center;'
                    f'min-height:80px">'
                    f'<div style="font-size:10px;font-weight:600;color:{A["label_secondary"]}">'
                    f'{"[TODAY] " if is_today else ""}{day_names[i]} {day.day}</div>'
                    f'<div style="font-size:9px;font-weight:700;color:{color};'
                    f'margin:4px 0;text-transform:uppercase">{type_info.get("label","")}</div>'
                    f'<div style="font-size:10px;color:{A["label_tertiary"]}">'
                    f'{workout.get("duration_min","?")} min</div>'
                    f'<div style="font-size:12px;color:{"#1E8E3E" if status=="completed" else A["label_tertiary"]}">'
                    f'{status_badge}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="border:{border};background:{bg};'
                    f'border-radius:{A["radius_md"]};padding:8px 6px;text-align:center;'
                    f'min-height:80px">'
                    f'<div style="font-size:10px;font-weight:600;color:{A["label_secondary"]}">'
                    f'{"[TODAY] " if is_today else ""}{day_names[i]} {day.day}</div>'
                    f'<div style="font-size:11px;color:{A["label_quaternary"]};margin-top:16px">Rest</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── Progression Levels ─────────────────────────────────────────────────────

def render_progression_levels(levels: dict) -> None:
    """Render horizontal progress bars for each energy system level (1–10)."""
    html_rows = ""
    for energy_type, level in levels.items():
        type_info = WORKOUT_TYPES.get(energy_type, {})
        color = type_info.get("color", A["blue"])
        label = type_info.get("label", energy_type.replace("_", " ").title())
        icon = type_info.get("icon", "&#127947;")
        bar_pct = max((level - 1.0) / 9.0 * 100, 2)
        html_rows += (
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'font-size:12px;margin-bottom:4px">'
            f'<span style="font-weight:600;color:{A["label_secondary"]}">'
            f'{icon} {label}</span>'
            f'<span style="font-weight:700;color:{color}">{level:.1f}</span>'
            f'</div>'
            f'<div style="background:rgba(0,0,0,0.06);border-radius:999px;height:7px">'
            f'<div style="width:{bar_pct:.1f}%;background:{color};'
            f'border-radius:999px;height:7px"></div>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:12px">'
        f'Progression Levels &nbsp;'
        f'<span style="font-size:10px;font-weight:400;color:{A["label_tertiary"]}">'
        f'1.0 = beginner · 10.0 = elite</span></div>'
        f'{html_rows}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Ramp Test Guide ────────────────────────────────────────────────────────

def render_ramp_test_guide() -> None:
    """Render step-by-step FTP Ramp Test protocol."""
    steps = [
        ("Set up", "Set your trainer to ERG mode (smart trainer) or use a flat resistance setting. Have a fan ready — it will get hot."),
        ("Warm up", "Pedal easy for 10 minutes at 50% of your current FTP. Get your legs spinning smoothly."),
        ("Start the ramp", "Begin at 46% of your current FTP (e.g. 115W for FTP=250). Increase power by approximately 6W every minute."),
        ("Keep going", "Maintain your cadence above 85 RPM. Continue increasing each minute until you cannot maintain power for 15 consecutive seconds."),
        ("Calculate FTP", "Your new FTP = the highest 1-minute power you fully completed × 0.75."),
        ("Recover", "Spin easy for 10+ minutes. Allow 48 hours of easy training before your next hard session."),
    ]
    step_html = ""
    for i, (title, desc) in enumerate(steps, 1):
        step_html += (
            f'<div style="display:flex;gap:12px;margin-bottom:12px">'
            f'<div style="min-width:28px;height:28px;background:{A["blue"]};'
            f'border-radius:50%;display:flex;align-items:center;justify-content:center;'
            f'font-size:12px;font-weight:700;color:#fff;flex-shrink:0">{i}</div>'
            f'<div>'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]};'
            f'margin-bottom:2px">{title}</div>'
            f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">{desc}</div>'
            f'</div>'
            f'</div>'
        )
    tip_html = (
        f'<div style="background:{A["blue"]}08;border-left:3px solid {A["blue"]};'
        f'padding:10px 12px;border-radius:0 {A["radius_sm"]} {A["radius_sm"]} 0;margin-top:4px">'
        f'<div style="font-size:11px;font-weight:600;color:{A["blue"]};margin-bottom:2px">&#128161; Pro Tip</div>'
        f'<div style="font-size:11px;color:{A["label_secondary"]};line-height:16px">'
        f'Retest every 6–8 weeks or after a significant jump in training load. '
        f'An accurate FTP ensures all your zones are correct — everything depends on it.</div>'
        f'</div>'
    )
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px">'
        f'<div style="font-size:14px;font-weight:700;color:{A["label_primary"]};margin-bottom:12px">'
        f'FTP Ramp Test Protocol</div>'
        f'{step_html}'
        f'{tip_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Ride Summary Card ──────────────────────────────────────────────────────

def render_ride_summary_card(ride: dict) -> None:
    """Render a compact summary card for a completed ride."""
    avg_power = ride.get("avg_power") or 0
    if_score = ride.get("if_score") or 0
    tss = ride.get("tss") or 0
    dur = ride.get("duration_min", 0)
    survey = ride.get("difficulty_survey")
    survey_emoji = DIFFICULTY_SURVEY_OPTIONS.get(survey, {}).get("emoji", "") if survey else ""

    # IF color coding
    if if_score >= 1.0:
        if_color = A["red"]
    elif if_score >= 0.90:
        if_color = A["orange"]
    elif if_score >= 0.75:
        if_color = A["yellow"]
    else:
        if_color = A["green"]

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 14px;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:12px">'
        f'<div style="flex:1">'
        f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
        f'&#128690; {ride.get("ride_date","")}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:2px">'
        f'{dur} min'
        f'{(" &middot; " + ride.get("notes","")[:40]) if ride.get("notes") else ""}'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;gap:14px;align-items:center">'
        f'<div style="text-align:center">'
        f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]}">'
        f'{avg_power}W</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">Avg Power</div>'
        f'</div>'
        f'<div style="text-align:center">'
        f'<div style="font-size:15px;font-weight:700;color:{if_color}">'
        f'{if_score:.3f}</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">IF</div>'
        f'</div>'
        f'<div style="text-align:center">'
        f'<div style="font-size:15px;font-weight:700;color:{A["orange"]}">'
        f'{tss:.0f}</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">TSS</div>'
        f'</div>'
        f'{("<div style='font-size:18px'>" + survey_emoji + "</div>") if survey_emoji else ""}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
