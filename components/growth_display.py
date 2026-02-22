"""Display components for Daily Growth: quote cards, nudge cards, meditation stats."""

import streamlit as st
from components.custom_theme import APPLE

A = APPLE


def render_quote_card(quote, reflection_prompt=None):
    """Render a large-typography wisdom quote card with author and source."""
    source_line = f' — {quote["source"]}' if quote.get("source") and quote["source"] != "attributed" else ""
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:32px 28px;margin-bottom:16px;'
        f'text-align:center">'
        f'<div style="font-family:{A["font_display"]};font-size:22px;line-height:1.5;'
        f'font-weight:400;color:{A["label_primary"]};font-style:italic;'
        f'letter-spacing:-0.01em;margin-bottom:16px">'
        f'&ldquo;{quote["text"]}&rdquo;</div>'
        f'<div style="font-family:{A["font_text"]};font-size:14px;font-weight:600;'
        f'color:{A["purple"]};letter-spacing:0.02em">'
        f'{quote["author"]}{source_line}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if reflection_prompt:
        prompt_html = (
            f'<div style="font-family:{A["font_text"]};font-size:13px;'
            f'color:{A["label_tertiary"]};font-style:italic;'
            f'padding:0 4px;margin-bottom:12px">'
            f'{reflection_prompt}</div>'
        )
        st.markdown(prompt_html, unsafe_allow_html=True)


def render_nudge_card(nudge_text):
    """Render a soft, minimal mindfulness nudge card."""
    html = (
        f'<div style="background:{A["bg_secondary"]};'
        f'border-radius:{A["radius_md"]};padding:20px 24px;margin-bottom:12px;'
        f'border-left:3px solid {A["teal"]}">'
        f'<div style="font-family:{A["font_text"]};font-size:13px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;'
        f'color:{A["teal"]};margin-bottom:8px">Mindfulness Moment</div>'
        f'<div style="font-family:{A["font_display"]};font-size:16px;line-height:1.5;'
        f'color:{A["label_primary"]}">{nudge_text}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_meditation_streak(streak, total_sessions=None):
    """Render a minimal meditation streak counter."""
    sub = f'{total_sessions} sessions (30d)' if total_sessions else ''
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:16px 20px;text-align:center;'
        f'margin-bottom:12px">'
        f'<div style="font-family:{A["font_display"]};font-size:36px;font-weight:700;'
        f'color:{A["label_primary"]};line-height:1">{streak}</div>'
        f'<div style="font-family:{A["font_text"]};font-size:12px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;'
        f'color:{A["label_tertiary"]};margin-top:4px">day streak</div>'
        f'<div style="font-family:{A["font_text"]};font-size:11px;'
        f'color:{A["label_quaternary"]};margin-top:4px">{sub}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_meditation_log_summary(stats):
    """Render meditation statistics summary."""
    if not stats or stats["total_sessions"] == 0:
        st.caption("No meditation sessions recorded yet.")
        return

    html = (
        f'<div style="display:flex;gap:12px;margin-bottom:12px">'
        f'<div style="flex:1;background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
        f'color:{A["label_primary"]}">{stats["total_sessions"]}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">Sessions</div></div>'
        f'<div style="flex:1;background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
        f'color:{A["label_primary"]}">{stats["total_minutes"]}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">Minutes</div></div>'
        f'<div style="flex:1;background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;text-align:center">'
        f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
        f'color:{A["label_primary"]}">{stats["avg_duration"]}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">Avg min</div></div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_mood_change(before, after):
    """Render a small before/after mood indicator."""
    from config.growth_data import MOOD_LABELS
    if before is None and after is None:
        return
    b_label = MOOD_LABELS.get(before, "—") if before else "—"
    a_label = MOOD_LABELS.get(after, "—") if after else "—"
    b_color = A["label_tertiary"]
    a_color = A["green"] if after and before and after > before else (A["orange"] if after and before and after < before else A["label_secondary"])

    html = (
        f'<span style="font-size:12px;color:{b_color}">{b_label}</span>'
        f'<span style="font-size:12px;color:{A["label_quaternary"]}"> &rarr; </span>'
        f'<span style="font-size:12px;color:{a_color}">{a_label}</span>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_session_row(session):
    """Render a compact meditation session row."""
    from config.growth_data import MEDITATION_TYPES, MOOD_LABELS
    mt = MEDITATION_TYPES.get(session["meditation_type"], {})
    label = mt.get("label", session["meditation_type"])
    mood_str = ""
    if session.get("mood_before") and session.get("mood_after"):
        b = MOOD_LABELS.get(session["mood_before"], "")
        a = MOOD_LABELS.get(session["mood_after"], "")
        mood_str = f' &middot; {b} &rarr; {a}'

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_sm"]};padding:10px 14px;margin-bottom:6px;'
        f'display:flex;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<span style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
        f'{label}</span>'
        f'<span style="font-size:12px;color:{A["label_tertiary"]}">'
        f' &middot; {session["session_date"]}{mood_str}</span>'
        f'</div>'
        f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:700;'
        f'color:{A["teal"]}">{session["duration_minutes"]} min</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_mini_quote(quote):
    """Render a small quote for the 'More quotes' section."""
    source_line = f' — {quote["source"]}' if quote.get("source") and quote["source"] != "attributed" else ""
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_sm"]};padding:14px 16px;margin-bottom:8px">'
        f'<div style="font-size:14px;color:{A["label_secondary"]};font-style:italic;'
        f'line-height:1.4;margin-bottom:6px">&ldquo;{quote["text"]}&rdquo;</div>'
        f'<div style="font-size:12px;color:{A["purple"]};font-weight:600">'
        f'{quote["author"]}{source_line}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
