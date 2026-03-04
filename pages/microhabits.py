"""Atomic Habits — 2-Minute Rule, Habit Stacking, 4 Laws Scorecard, Never Miss Twice."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from config.settings import PILLARS, FOUR_LAWS_QUESTIONS
from models.habit import get_active_habits
from services.habit_service import get_habit_streak
from services.microhabit_service import (
    get_micro_version, set_micro_version, create_micro_habit,
    create_stack, get_user_stacks, add_to_stack, remove_from_stack,
    get_stack_habits, reorder_stack, get_stack_text,
    save_four_laws, get_four_laws, get_weakest_law,
    diagnose_all_habits, get_four_laws_averages,
    get_missed_yesterday, get_never_miss_twice_alerts,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Atomic Habits",
    "Small changes, remarkable results. Build habits using the science of behavior change.",
)

tab_micro, tab_stacks, tab_laws, tab_miss = st.tabs([
    "2-Minute Rule", "Habit Stacks", "4 Laws Scorecard", "Never Miss Twice",
])

habits = get_active_habits(user_id)

# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1: 2-Minute Rule
# ═══════════════════════════════════════════════════════════════════════════════

with tab_micro:
    render_section_header(
        "The 2-Minute Rule",
        '"When you start a new habit, it should take less than two minutes to do." — James Clear',
    )

    if not habits:
        st.info("No active habits yet. Add habits in the Weekly Plan to get started.")
    else:
        for h in habits:
            pillar = PILLARS.get(h["pillar_id"], {})
            micro = get_micro_version(h["id"])
            streak = get_habit_streak(h["id"], user_id)
            pillar_color = pillar.get("color", A["blue"])

            card_html = (
                f'<div style="background:{A["bg_elevated"]};border-radius:{A["radius_md"]};'
                f'padding:16px;margin-bottom:12px;border-left:4px solid {pillar_color};'
                f'box-shadow:0 1px 3px rgba(0,0,0,0.06)">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
                f'color:{A["label_primary"]}">{h["name"]}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:13px;color:{A["label_tertiary"]};'
                f'margin-top:2px">{pillar.get("display_name", "")}</div>'
                f'</div>'
                f'<div style="font-family:{A["font_display"]};font-size:13px;color:{pillar_color};'
                f'font-weight:600">{streak}d streak</div>'
                f'</div>'
                f'<div style="margin-top:10px;padding:10px;background:{A["bg_secondary"]};'
                f'border-radius:{A["radius_sm"]};font-family:{A["font_text"]};font-size:13px;'
                f'color:{A["label_secondary"]}">'
                f'Micro version: <strong>{micro}</strong>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            c1, c2 = st.columns([3, 1])
            with c1:
                new_micro = st.text_input(
                    "Edit micro version",
                    value=micro,
                    key=f"micro_edit_{h['id']}",
                    label_visibility="collapsed",
                    placeholder="Type a 2-minute version...",
                )
            with c2:
                if st.button("Save", key=f"micro_save_{h['id']}", use_container_width=True):
                    set_micro_version(h["id"], new_micro)
                    st.toast(f"Micro version saved for {h['name']}")
                    st.rerun()

    st.divider()
    html_quote = (
        f'<div style="background:{A["bg_secondary"]};border-radius:{A["radius_md"]};'
        f'padding:20px;font-family:{A["font_text"]};font-size:14px;'
        f'color:{A["label_secondary"]};font-style:italic;line-height:1.6">'
        f'"Habits are the compound interest of self-improvement. '
        f'The same way that money multiplies through compound interest, '
        f'the effects of your habits multiply as you repeat them."'
        f'<div style="margin-top:8px;font-style:normal;font-weight:600;'
        f'color:{A["label_primary"]}">— James Clear, Atomic Habits</div>'
        f'</div>'
    )
    st.markdown(html_quote, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2: Habit Stacks
# ═══════════════════════════════════════════════════════════════════════════════

with tab_stacks:
    render_section_header(
        "Habit Stacking",
        '"After [CURRENT HABIT], I will [NEW HABIT]."',
    )

    stacks = get_user_stacks(user_id)

    if stacks:
        for s in stacks:
            stack_habits = get_stack_habits(s["id"])
            chain_text = get_stack_text(s["id"])

            header_html = (
                f'<div style="background:{A["bg_elevated"]};border-radius:{A["radius_md"]};'
                f'padding:16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06)">'
                f'<div style="font-family:{A["font_display"]};font-size:16px;font-weight:600;'
                f'color:{A["label_primary"]}">{s["name"]}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:13px;color:{A["label_tertiary"]};'
                f'margin-top:4px">{s["habit_count"]} habits</div>'
            )

            if s.get("anchor_cue"):
                header_html += (
                    f'<div style="margin-top:8px;padding:8px 12px;background:{A["bg_secondary"]};'
                    f'border-radius:{A["radius_sm"]};font-family:{A["font_text"]};font-size:13px;'
                    f'color:{A["label_secondary"]}">{chain_text}</div>'
                )

            header_html += '</div>'
            st.markdown(header_html, unsafe_allow_html=True)

            # Show chain as vertical nodes
            for idx, sh in enumerate(stack_habits):
                pillar_color = PILLARS.get(sh["pillar_id"], {}).get("color", A["blue"])
                arrow = "" if idx == 0 else (
                    f'<div style="text-align:center;color:{A["label_tertiary"]};'
                    f'font-size:18px;margin:4px 0">↓</div>'
                )
                node_html = (
                    f'{arrow}'
                    f'<div style="background:{A["bg_elevated"]};border-radius:{A["radius_sm"]};'
                    f'padding:10px 14px;margin:0 24px;border-left:3px solid {pillar_color};'
                    f'font-family:{A["font_text"]};font-size:14px;color:{A["label_primary"]}">'
                    f'{sh["name"]}</div>'
                )
                st.markdown(node_html, unsafe_allow_html=True)

            # Add/remove habits from stack
            with st.expander(f"Edit {s['name']}", expanded=False):
                available = [h for h in habits if h.get("stack_id") != s["id"]]
                if available:
                    sel = st.selectbox(
                        "Add habit",
                        options=available,
                        format_func=lambda x: x["name"],
                        key=f"stack_add_{s['id']}",
                    )
                    if st.button("Add to Stack", key=f"stack_add_btn_{s['id']}"):
                        add_to_stack(sel["id"], s["id"])
                        st.toast(f"Added {sel['name']} to {s['name']}")
                        st.rerun()

                if stack_habits:
                    rm_sel = st.selectbox(
                        "Remove habit",
                        options=stack_habits,
                        format_func=lambda x: x["name"],
                        key=f"stack_rm_{s['id']}",
                    )
                    if st.button("Remove from Stack", key=f"stack_rm_btn_{s['id']}"):
                        remove_from_stack(rm_sel["id"])
                        st.toast(f"Removed {rm_sel['name']}")
                        st.rerun()

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Create new stack
    st.divider()
    st.markdown("### Create New Stack")
    with st.form("new_stack_form"):
        stack_name = st.text_input("Stack name", placeholder="e.g. Morning Routine")
        stack_cue = st.text_input("Anchor cue", placeholder="e.g. After morning coffee")
        stack_time = st.time_input("Anchor time (optional)", value=None)

        first_habit = None
        if habits:
            first_habit = st.selectbox(
                "First habit in stack",
                options=habits,
                format_func=lambda x: x["name"],
            )

        if st.form_submit_button("Create Stack", use_container_width=True):
            if stack_name:
                time_str = stack_time.strftime("%H:%M") if stack_time else None
                sid = create_stack(user_id, stack_name, anchor_cue=stack_cue or None,
                                   anchor_time=time_str)
                if first_habit:
                    add_to_stack(first_habit["id"], sid, position=1)
                st.toast(f"Stack '{stack_name}' created!")
                st.rerun()
            else:
                st.error("Please enter a stack name.")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3: 4 Laws Scorecard
# ═══════════════════════════════════════════════════════════════════════════════

with tab_laws:
    render_section_header(
        "4 Laws Scorecard",
        "Rate each habit to find what's holding you back.",
    )

    # Radar chart of averages
    avgs = get_four_laws_averages(user_id)
    if any(v > 0 for v in avgs.values()):
        fig = go.Figure()
        categories = ["Obvious", "Attractive", "Easy", "Satisfying", "Obvious"]
        values = [avgs["obvious"], avgs["attractive"], avgs["easy"],
                  avgs["satisfying"], avgs["obvious"]]
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories,
            fill="toself", name="Average",
            line=dict(color=A["indigo"], width=2),
            fillcolor="rgba(103,80,164,0.15)",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5]),
                bgcolor=A["bg_elevated"],
            ),
            showlegend=False, height=350,
            margin=dict(l=60, r=60, t=30, b=30),
            paper_bgcolor=A["bg_primary"],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Per-habit scoring
    if not habits:
        st.info("No active habits yet.")
    else:
        by_pillar: dict[int, list] = {}
        for h in habits:
            by_pillar.setdefault(h["pillar_id"], []).append(h)

        for pid in sorted(by_pillar.keys()):
            pillar = PILLARS.get(pid, {})
            st.markdown(f"#### {pillar.get('display_name', f'Pillar {pid}')}")

            for h in by_pillar[pid]:
                scores = get_four_laws(h["id"]) or {"obvious": 3, "attractive": 3, "easy": 3, "satisfying": 3}
                weakest = get_weakest_law(h["id"])

                with st.expander(h["name"], expanded=False):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        o = st.slider("Obvious", 1, 5, scores["obvious"], key=f"law_o_{h['id']}")
                    with c2:
                        a = st.slider("Attractive", 1, 5, scores["attractive"], key=f"law_a_{h['id']}")
                    with c3:
                        e = st.slider("Easy", 1, 5, scores["easy"], key=f"law_e_{h['id']}")
                    with c4:
                        s = st.slider("Satisfying", 1, 5, scores["satisfying"], key=f"law_s_{h['id']}")

                    if st.button("Save Scores", key=f"law_save_{h['id']}", use_container_width=True):
                        save_four_laws(h["id"], obvious=o, attractive=a, easy=e, satisfying=s)
                        st.toast(f"Scores saved for {h['name']}")
                        st.rerun()

                    if weakest:
                        law_info = FOUR_LAWS_QUESTIONS.get(weakest, {})
                        tip = law_info.get("tips", [""])[0]
                        tip_html = (
                            f'<div style="background:#FFF3E0;border-radius:{A["radius_sm"]};'
                            f'padding:10px 14px;margin-top:8px;font-family:{A["font_text"]};'
                            f'font-size:13px;color:#E65100">'
                            f'<strong>Weakest: {law_info.get("label", weakest)}</strong> — {tip}'
                            f'</div>'
                        )
                        st.markdown(tip_html, unsafe_allow_html=True)

    # Diagnosis table
    diagnosis = diagnose_all_habits(user_id)
    if diagnosis:
        st.divider()
        render_section_header("Diagnosis Summary")
        for d in diagnosis:
            law_info = FOUR_LAWS_QUESTIONS.get(d["weakest_law"], {})
            pillar_color = PILLARS.get(d["pillar_id"], {}).get("color", A["blue"])
            row_html = (
                f'<div style="display:flex;align-items:center;padding:8px 0;'
                f'border-bottom:1px solid {A["separator"]}">'
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{pillar_color};margin-right:10px;flex-shrink:0"></div>'
                f'<div style="flex:1;font-family:{A["font_text"]};font-size:14px;'
                f'color:{A["label_primary"]}">{d["name"]}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:13px;color:{A["orange"]};'
                f'font-weight:600;min-width:120px">{law_info.get("label", d["weakest_law"])}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:12px;color:{A["label_tertiary"]};'
                f'max-width:250px">{d["tip"]}</div>'
                f'</div>'
            )
            st.markdown(row_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 4: Never Miss Twice
# ═══════════════════════════════════════════════════════════════════════════════

with tab_miss:
    render_section_header(
        "Never Miss Twice",
        '"The first mistake is never the one that ruins you. It is the spiral of repeated mistakes that follows." — James Clear',
    )

    alerts = get_never_miss_twice_alerts(user_id)
    missed = get_missed_yesterday(user_id)
    missed_only_once = [m for m in missed if m["id"] not in {a["id"] for a in alerts}]

    if alerts:
        for a in alerts:
            micro = get_micro_version(a["id"])
            alert_html = (
                f'<div style="background:#FFEBEE;border-radius:{A["radius_md"]};'
                f'padding:16px;margin-bottom:12px;border-left:4px solid {A["red"]}">'
                f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
                f'color:{A["red"]}">2 days missed: {a["name"]}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:13px;color:{A["label_secondary"]};'
                f'margin-top:6px">Don\'t miss a third day. Try the micro version:</div>'
                f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
                f'color:{A["label_primary"]};margin-top:4px">{micro}</div>'
                f'</div>'
            )
            st.markdown(alert_html, unsafe_allow_html=True)

    if missed_only_once:
        for m in missed_only_once:
            micro = get_micro_version(m["id"])
            warn_html = (
                f'<div style="background:#FFF8E1;border-radius:{A["radius_md"]};'
                f'padding:14px;margin-bottom:10px;border-left:4px solid {A["yellow"]}">'
                f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
                f'color:{A["orange"]}">Missed yesterday: {m["name"]}</div>'
                f'<div style="font-family:{A["font_text"]};font-size:13px;color:{A["label_secondary"]};'
                f'margin-top:4px">Get back on track today. Micro version: <strong>{micro}</strong></div>'
                f'</div>'
            )
            st.markdown(warn_html, unsafe_allow_html=True)

    if not alerts and not missed_only_once:
        ok_html = (
            f'<div style="background:#E8F5E9;border-radius:{A["radius_md"]};'
            f'padding:20px;text-align:center">'
            f'<div style="font-family:{A["font_display"]};font-size:18px;font-weight:600;'
            f'color:{A["green"]}">You\'re on track!</div>'
            f'<div style="font-family:{A["font_text"]};font-size:14px;color:{A["label_secondary"]};'
            f'margin-top:6px">No habits missed yesterday. Keep the chain going!</div>'
            f'</div>'
        )
        st.markdown(ok_html, unsafe_allow_html=True)
