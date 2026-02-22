"""Fasting Tracker — Start/end fasts, track metabolic zones, view history."""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.fasting_display import (
    render_fasting_timer,
    render_zone_indicator,
    render_zone_progress_bar,
    render_fasting_stat_cards,
)
from config.fasting_data import FASTING_TYPES, FASTING_ZONES, FASTING_SAFETY
from services.fasting_service import (
    start_fast,
    end_fast,
    get_active_fast,
    get_fasting_history,
    get_fasting_stats,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Fasting Tracker",
    "Time-restricted eating backed by science. Track your fasting windows and metabolic zones."
)

tab_timer, tab_history, tab_zones, tab_info = st.tabs([
    "Active Fast", "History", "Metabolic Zones", "Science & Safety"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Active Fast
# ══════════════════════════════════════════════════════════════════════════
with tab_timer:
    active = get_active_fast(user_id)

    if active:
        render_section_header("Fast In Progress")
        col_timer, col_zone = st.columns([1, 1])
        with col_timer:
            render_fasting_timer(active)
        with col_zone:
            render_zone_indicator(active)

        render_zone_progress_bar(active.get("elapsed_hours", 0))

        # Fast details
        ft = FASTING_TYPES.get(active.get("fasting_type", ""), {})
        detail_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:12px">'
            f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
            f'Protocol: <span style="color:{A["label_secondary"]};font-weight:600">'
            f'{ft.get("label", active.get("fasting_type", ""))}</span>'
            f' &middot; Started: <span style="color:{A["label_secondary"]}">'
            f'{active["start_time"]}</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(detail_html, unsafe_allow_html=True)

        if st.button("End Fast", use_container_width=True, type="primary"):
            result = end_fast(user_id, active["id"])
            if result:
                status = "completed" if result["completed"] else "ended early"
                st.toast(f"Fast {status}! Duration: {result['actual_hours']}h")
            st.rerun()

    else:
        render_section_header("Start a Fast", "Choose your protocol")

        # Protocol cards
        for ftype_key, ftype in FASTING_TYPES.items():
            if ftype_key == "custom":
                continue
            diff_stars = "&#9733;" * ftype.get("difficulty", 1) + "&#9734;" * (3 - ftype.get("difficulty", 1))
            card_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:3px solid {ftype["color"]};'
                f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:6px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<div style="font-family:{A["font_display"]};font-size:15px;'
                f'font-weight:600;color:{A["label_primary"]}">{ftype["label"]}</div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'{ftype["description"]}</div>'
                f'</div>'
                f'<div style="font-size:12px;color:{ftype["color"]}">{diff_stars}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        col_proto, col_custom = st.columns([2, 1])
        with col_proto:
            protocol_options = {v["label"]: k for k, v in FASTING_TYPES.items() if k != "custom"}
            selected_label = st.selectbox("Select Protocol", list(protocol_options.keys()))
            selected_type = protocol_options[selected_label]
        with col_custom:
            custom_hours = st.number_input(
                "Custom hours (optional)",
                min_value=1, max_value=72, value=None,
                help="Override the default target hours",
            )

        notes = st.text_input("Notes (optional)", placeholder="e.g., Trying 16:8 for the first time")

        if st.button("Start Fast", use_container_width=True, type="primary"):
            target = custom_hours if custom_hours else None
            start_fast(user_id, selected_type, target_hours=target, notes=notes if notes else None)
            ft = FASTING_TYPES.get(selected_type, {})
            st.toast(f"Fast started! ({ft.get('label', selected_type)})")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: History
# ══════════════════════════════════════════════════════════════════════════
with tab_history:
    render_section_header("Fasting History")

    stats = get_fasting_stats(user_id, days=30)
    render_fasting_stat_cards(stats)

    history = get_fasting_history(user_id, limit=30)
    if not history:
        st.caption("No completed fasts yet. Start your first fast!")
    else:
        for s in history:
            ft = FASTING_TYPES.get(s.get("fasting_type", ""), {})
            completed = s.get("completed", 0)
            actual = s.get("actual_hours", 0)
            target = s.get("target_hours", 0)

            status_color = "#30D158" if completed else "#FF9F0A"
            status_label = "Completed" if completed else "Ended Early"

            start_dt = s.get("start_time", "")[:16]
            end_dt = s.get("end_time", "")[:16] if s.get("end_time") else ""

            row_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:3px solid {status_color};'
                f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:6px;'
                f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
                f'<div style="min-width:100px">'
                f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
                f'{ft.get("label", s.get("fasting_type", ""))}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">{start_dt}</div>'
                f'</div>'
                f'<div style="font-family:{A["font_display"]};font-size:18px;'
                f'font-weight:700;color:{A["label_primary"]}">{actual}h</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">/ {target}h target</div>'
                f'<div style="font-size:10px;font-weight:600;padding:2px 8px;'
                f'border-radius:4px;background:{status_color}20;color:{status_color}">'
                f'{status_label}</div>'
                f'</div>'
            )
            st.markdown(row_html, unsafe_allow_html=True)

        # Trend chart
        if len(history) >= 3:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            render_section_header("Duration Trend")

            dates = [s["start_time"][:10] for s in reversed(history)]
            hours = [s.get("actual_hours", 0) for s in reversed(history)]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=hours,
                marker_color=["#30D158" if s.get("completed") else "#FF9F0A" for s in reversed(history)],
                opacity=0.8,
                hovertemplate="%{y:.1f}h<br>%{x}<extra></extra>",
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1C1C1E",
                font=dict(family=A["font_text"]),
                margin=dict(l=40, r=20, t=20, b=40),
                height=250,
                xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
                yaxis=dict(title="Hours", gridcolor="rgba(84,84,88,0.3)"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Metabolic Zones
# ══════════════════════════════════════════════════════════════════════════
with tab_zones:
    render_section_header("Metabolic Zones", "What happens in your body as you fast")

    for zone in FASTING_ZONES:
        zone_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:3px solid {zone["color"]};'
            f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<span style="font-size:24px">{zone["icon"]}</span>'
            f'<div>'
            f'<div style="font-family:{A["font_display"]};font-size:16px;'
            f'font-weight:700;color:{zone["color"]}">{zone["name"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'{zone["start_hours"]}-{zone["end_hours"]} hours</div>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:13px;line-height:20px;color:{A["label_secondary"]}">'
            f'{zone["mechanism"]}</div>'
            f'</div>'
        )
        st.markdown(zone_html, unsafe_allow_html=True)

        if zone.get("causation_note"):
            note_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:10px 14px;margin-top:-8px;margin-bottom:12px">'
                f'<div style="font-size:11px;color:{A["orange"]}">'
                f'&#9888; {zone["causation_note"]}</div>'
                f'</div>'
            )
            st.markdown(note_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Science & Safety
# ══════════════════════════════════════════════════════════════════════════
with tab_info:
    render_section_header("Safety Information", "Important considerations before fasting")

    # Contraindications
    contra_items = ""
    for item in FASTING_SAFETY["contraindications"]:
        contra_items += (
            f'<div style="font-size:13px;color:{A["label_secondary"]};'
            f'padding:3px 0">&#10060; {item}</div>'
        )
    contra_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:3px solid {A["red"]};border-radius:{A["radius_lg"]};'
        f'padding:16px;margin-bottom:12px">'
        f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
        f'color:{A["red"]};margin-bottom:8px">Contraindications</div>'
        f'{contra_items}'
        f'</div>'
    )
    st.markdown(contra_html, unsafe_allow_html=True)

    # General guidance
    guidance_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
        f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
        f'color:{A["label_primary"]};margin-bottom:8px">General Guidance</div>'
        f'<div style="font-size:13px;line-height:20px;color:{A["label_secondary"]}">'
        f'{FASTING_SAFETY["general_guidance"]}</div>'
        f'</div>'
    )
    st.markdown(guidance_html, unsafe_allow_html=True)

    # Disclaimer
    disc_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:12px">'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};font-style:italic">'
        f'{FASTING_SAFETY["disclaimer"]}</div>'
        f'</div>'
    )
    st.markdown(disc_html, unsafe_allow_html=True)
