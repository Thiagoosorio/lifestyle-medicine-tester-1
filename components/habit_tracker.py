import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from models.habit import toggle_habit


def render_habit_grid(user_id: int, week_data: dict, week_start: date):
    """Render a 7-column habit tracker grid.
    week_data = {habit_id: {habit: {...}, completions: {date_str: bool}}}
    """
    if not week_data:
        st.info("No habits set up yet. Add habits in the Goals page or Settings.")
        return

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
                        st.rerun()
