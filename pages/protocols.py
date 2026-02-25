"""Daily Protocols — Science-backed daily routines with completion tracking."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header, render_hero_stats
from components.evidence_display import render_evidence_card
from config.settings import PILLARS
from services.protocol_service import (
    get_user_protocols,
    get_daily_protocol_status,
    log_protocol_completion,
    get_protocol_adherence,
    get_protocol_adherence_history,
    get_all_protocols,
    adopt_protocol,
    pause_protocol,
    abandon_protocol,
    is_protocol_adopted,
)
from services.evidence_service import get_evidence_for_entity

A = APPLE
user_id = st.session_state.user_id
today = date.today().isoformat()

render_hero_banner(
    "Daily Protocols",
    "Science-backed routines to optimize your health. Track your adherence and see the research behind each protocol."
)

# ── Fetch user's protocols ────────────────────────────────────────────────
user_protocols = get_user_protocols(user_id)

if not user_protocols:
    # Empty state
    cta_html = (
        f'<div style="border-radius:{A["radius_xl"]};padding:40px;text-align:center;'
        f'margin-bottom:24px;background:rgba(94,92,230,0.10);'
        f'border:1px solid rgba(94,92,230,0.20)">'
        f'<div style="font-size:2.5rem;margin-bottom:12px">&#128300;</div>'
        f'<div style="font-family:{A["font_display"]};font-size:20px;line-height:24px;'
        f'font-weight:600;color:{A["label_primary"]};margin-bottom:8px">'
        f'No Protocols Adopted Yet</div>'
        f'<div style="font-size:15px;line-height:20px;color:{A["label_secondary"]};'
        f'max-width:420px;margin:0 auto 20px auto">'
        f'Browse the Research Library to find science-backed daily protocols '
        f'tailored to each pillar of lifestyle medicine.</div>'
        f'</div>'
    )
    st.markdown(cta_html, unsafe_allow_html=True)
    if st.button("Browse Protocol Library", type="primary", use_container_width=True):
        st.switch_page("pages/research_library.py")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# HERO STATS
# ══════════════════════════════════════════════════════════════════════════
daily_status = get_daily_protocol_status(user_id, today)
total_protocols = len(daily_status)
completed_today = sum(1 for p in daily_status if p["completed"])
completion_pct = round(completed_today / total_protocols * 100) if total_protocols > 0 else 0

# Calculate avg adherence over 30 days
adherence_values = []
for up in user_protocols:
    adh = get_protocol_adherence(user_id, up["protocol_id"], days_back=30)
    adherence_values.append(adh)
avg_adherence = round(sum(adherence_values) / len(adherence_values)) if adherence_values else 0

render_hero_stats([
    {"label": "Today's Progress", "value": f"{completed_today}/{total_protocols}", "icon": "\u2705", "color": A["green"]},
    {"label": "Completion", "value": f"{completion_pct}%", "icon": "\U0001f4ca", "color": A["blue"]},
    {"label": "Active Protocols", "value": str(total_protocols), "icon": "\U0001f52c", "color": A["purple"]},
    {"label": "30-Day Adherence", "value": f"{avg_adherence}%", "icon": "\U0001f4c8", "color": A["teal"]},
])

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TODAY'S PROTOCOL CHECKLIST
# ══════════════════════════════════════════════════════════════════════════
render_section_header("Today's Checklist", today)

# Group by timing
time_groups = {"Morning": [], "Midday": [], "After Meals": [], "Evening": [], "Anytime": []}
for p in daily_status:
    timing = (p.get("timing") or "").lower()
    if "morning" in timing or "waking" in timing:
        time_groups["Morning"].append(p)
    elif "evening" in timing or "night" in timing or "bed" in timing:
        time_groups["Evening"].append(p)
    elif "meal" in timing:
        time_groups["After Meals"].append(p)
    elif "midday" in timing or "afternoon" in timing:
        time_groups["Midday"].append(p)
    else:
        time_groups["Anytime"].append(p)

for group_name, items in time_groups.items():
    if not items:
        continue
    time_label_html = (
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin:12px 0 6px 0">'
        f'{group_name}</div>'
    )
    st.markdown(time_label_html, unsafe_allow_html=True)

    for p in items:
        pillar = PILLARS.get(p["pillar_id"], {})
        pillar_color = pillar.get("color", A["blue"])
        is_done = bool(p["completed"])

        col_check, col_info = st.columns([1, 6])
        with col_check:
            new_state = st.checkbox(
                p["name"],
                value=is_done,
                key=f"proto_check_{p['protocol_id']}",
                label_visibility="collapsed",
            )
            if new_state != is_done:
                log_protocol_completion(user_id, p["protocol_id"], today, completed=new_state)
                st.rerun()
        with col_info:
            check_icon = "&#9989;" if is_done else "&#9744;"
            opacity = "0.5" if is_done else "1.0"
            text_decoration = "line-through" if is_done else "none"
            item_html = (
                f'<div style="opacity:{opacity};display:flex;align-items:center;gap:8px">'
                f'<span style="width:6px;height:6px;border-radius:50%;'
                f'background:{pillar_color};display:inline-block"></span>'
                f'<span style="font-size:14px;font-weight:500;'
                f'color:{A["label_primary"]};text-decoration:{text_decoration}">'
                f'{p["name"]}</span>'
                f'<span style="font-size:11px;color:{A["label_tertiary"]}">'
                f'{p.get("duration", "")}</span>'
                f'</div>'
            )
            st.markdown(item_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# PROTOCOL ADHERENCE (30-day sparklines)
# ══════════════════════════════════════════════════════════════════════════
st.divider()
render_section_header("30-Day Adherence", "Your consistency over the past month")

for up in user_protocols:
    pillar = PILLARS.get(up["pillar_id"], {})
    pillar_color = pillar.get("color", A["blue"])
    adherence = get_protocol_adherence(user_id, up["protocol_id"], days_back=30)
    history = get_protocol_adherence_history(user_id, up["protocol_id"], days_back=30)

    # Color based on adherence
    if adherence >= 80:
        adh_color = A["green"]
    elif adherence >= 50:
        adh_color = A["orange"]
    else:
        adh_color = A["red"]

    col_name, col_chart, col_pct = st.columns([2, 4, 1])

    with col_name:
        name_html = (
            f'<div style="display:flex;align-items:center;gap:6px;padding-top:8px">'
            f'<span style="width:8px;height:8px;border-radius:50%;'
            f'background:{pillar_color};display:inline-block"></span>'
            f'<span style="font-size:13px;font-weight:500;'
            f'color:{A["label_primary"]}">{up["name"]}</span>'
            f'</div>'
        )
        st.markdown(name_html, unsafe_allow_html=True)

    with col_chart:
        if history:
            dates = [r["log_date"] for r in history]
            values = [r["completed"] for r in history]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=values,
                marker_color=[A["green"] if v else "rgba(0,0,0,0.06)" for v in values],
                marker_line_width=0,
            ))
            fig.update_layout(
                height=40, margin=dict(t=0, b=0, l=0, r=0),
                yaxis=dict(visible=False, range=[0, 1.2]),
                xaxis=dict(visible=False),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False, bargap=0.2,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"adh_chart_{up['protocol_id']}")
        else:
            st.caption("No data yet")

    with col_pct:
        pct_html = (
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{adh_color};text-align:right;padding-top:4px">'
            f'{round(adherence)}%</div>'
        )
        st.markdown(pct_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# MANAGE PROTOCOLS
# ══════════════════════════════════════════════════════════════════════════
st.divider()
render_section_header("Manage Your Protocols")

for up in user_protocols:
    with st.expander(f"{up['name']}"):
        pillar = PILLARS.get(up["pillar_id"], {})
        st.markdown(f"**Pillar:** {pillar.get('display_name', '')}")
        st.markdown(f"**Description:** {up['description']}")
        if up.get("mechanism"):
            st.markdown(f"**How it works:** {up['mechanism']}")
        if up.get("expected_benefit"):
            st.markdown(f"**Expected benefit:** {up['expected_benefit']}")

        # Linked evidence
        linked = get_evidence_for_entity("protocol", up["protocol_id"])
        if linked:
            st.markdown("**Supporting Research:**")
            for ev in linked:
                render_evidence_card(ev, show_details=False)

        col_pause, col_abandon = st.columns(2)
        with col_pause:
            if st.button("Pause", key=f"pause_{up['protocol_id']}", use_container_width=True):
                pause_protocol(user_id, up["protocol_id"])
                st.toast(f"Protocol \"{up['name']}\" paused.")
                st.rerun()
        with col_abandon:
            if st.button("Remove", key=f"abandon_{up['protocol_id']}", use_container_width=True):
                abandon_protocol(user_id, up["protocol_id"])
                st.toast(f"Protocol \"{up['name']}\" removed.")
                st.rerun()

# Link to library
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
if st.button("Browse More Protocols", use_container_width=True):
    st.switch_page("pages/research_library.py")
