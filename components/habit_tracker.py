import random
import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from models.habit import toggle_habit, get_habit_streak
from services.microhabit_service import get_never_miss_twice_alerts, get_missed_yesterday

# Celebration messages for different streak milestones
CELEBRATIONS = {
    1: ["Nice start!", "First step!", "You showed up!"],
    3: ["3 days strong!", "Building momentum!", "Hat trick!"],
    7: ["One week streak!", "Consistency is key!", "7-day champion!"],
    14: ["Two weeks! You're unstoppable!", "14-day warrior!"],
    21: ["21 days = new habit forming!", "3 weeks of excellence!"],
    30: ["30-day milestone! This is who you are now!", "One month strong!"],
}


def _get_celebration(streak: int) -> str | None:
    """Get a celebration message based on the habit's streak."""
    for threshold in sorted(CELEBRATIONS.keys(), reverse=True):
        if streak >= threshold:
            return random.choice(CELEBRATIONS[threshold])
    return None


def _render_never_miss_twice_banner(user_id: int):
    """Show Never Miss Twice alerts above the habit grid."""
    try:
        alerts = get_never_miss_twice_alerts(user_id)
        missed = get_missed_yesterday(user_id)
    except Exception:
        return

    if alerts:
        for a in alerts:
            banner = (
                f'<div style="background:rgba(255,59,48,0.12);border:1px solid rgba(255,59,48,0.3);'
                f'border-radius:12px;padding:12px 16px;margin-bottom:8px;display:flex;'
                f'align-items:center;gap:10px">'
                f'<span style="font-size:1.3rem">🔴</span>'
                f'<div>'
                f'<div style="font-weight:600;color:#FF3B30;font-size:14px">'
                f'Never Miss Twice!</div>'
                f'<div style="color:#ccc;font-size:13px">{a["message"]}</div>'
                f'</div></div>'
            )
            st.markdown(banner, unsafe_allow_html=True)

    missed_only = [m for m in missed if m["id"] not in {a["id"] for a in alerts}]
    if missed_only:
        names = ", ".join(m["name"] for m in missed_only[:5])
        extra = f" +{len(missed_only)-5} more" if len(missed_only) > 5 else ""
        banner = (
            f'<div style="background:rgba(255,204,0,0.10);border:1px solid rgba(255,204,0,0.3);'
            f'border-radius:12px;padding:12px 16px;margin-bottom:8px;display:flex;'
            f'align-items:center;gap:10px">'
            f'<span style="font-size:1.3rem">🟡</span>'
            f'<div>'
            f'<div style="font-weight:600;color:#FFCC00;font-size:14px">'
            f'Missed Yesterday</div>'
            f'<div style="color:#ccc;font-size:13px">{names}{extra} — get back on track today!</div>'
            f'</div></div>'
        )
        st.markdown(banner, unsafe_allow_html=True)


def render_habit_grid(user_id: int, week_data: dict, week_start: date):
    """Render a 7-column habit tracker grid with celebrations.
    week_data = {habit_id: {habit: {...}, completions: {date_str: bool}}}
    """
    if not week_data:
        st.info("No habits set up yet. Add habits in the Goals page or Settings.")
        return

    _render_never_miss_twice_banner(user_id)

    days = [(week_start + timedelta(days=i)) for i in range(7)]
    day_labels = [d.strftime("%a\n%b %d") for d in days]
    today = date.today()

    # Header row
    cols = st.columns([2] + [1] * 7)
    with cols[0]:
        st.markdown("**Habit**")
    for i, label in enumerate(day_labels):
        with cols[i + 1]:
            is_today = days[i] == today
            if is_today:
                st.markdown(f"**:green[{label}]**")
            else:
                st.markdown(f"**{label}**")

    # Group habits by pillar
    habits_by_pillar = {}
    for hid, data in week_data.items():
        pid = data["habit"]["pillar_id"]
        if pid not in habits_by_pillar:
            habits_by_pillar[pid] = []
        habits_by_pillar[pid].append((hid, data))

    for pid in sorted(habits_by_pillar.keys()):
        pillar = PILLARS.get(pid, {})
        st.markdown(f"**{pillar.get('icon', '')} {pillar.get('display_name', '')}**")

        for hid, data in habits_by_pillar[pid]:
            habit = data["habit"]
            completions = data["completions"]

            cols = st.columns([2] + [1] * 7)
            with cols[0]:
                # Show habit name + implementation intention hint
                ii = habit.get("implementation_intention")
                if ii:
                    st.caption(f"{habit['name']}")
                    st.caption(f"*{ii}*")
                else:
                    st.caption(habit["name"])

            for i, day in enumerate(days):
                day_str = day.isoformat()
                is_completed = completions.get(day_str, False)

                with cols[i + 1]:
                    checked = st.checkbox(
                        f"{habit['name']} {day_str}",
                        value=is_completed,
                        key=f"habit_{hid}_{day_str}",
                        label_visibility="collapsed",
                    )
                    if checked != is_completed:
                        toggle_habit(hid, user_id, day_str, checked)
                        if checked:
                            # Celebration micro-feedback
                            streak = get_habit_streak(hid, user_id)
                            celebration = _get_celebration(streak)
                            if celebration:
                                st.toast(f":tada: {celebration} (Streak: {streak} days)")
                            else:
                                st.toast(":white_check_mark: Done!")
                        st.rerun()
