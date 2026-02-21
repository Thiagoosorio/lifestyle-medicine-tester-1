import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from services.habit_service import get_week_habit_data, initialize_default_habits, get_week_completion_rate, get_overall_streak
from services.checkin_service import get_week_checkins, save_daily_checkin, get_week_averages
from components.habit_tracker import render_habit_grid
from services.journey_service import get_journey, update_journey, can_add_habit, get_next_unlock, get_level_label
from services.report_service import get_or_generate_report

user_id = st.session_state.user_id

# Initialize default habits on first visit
initialize_default_habits(user_id)

st.title("Weekly Plan")

# ── Week navigator ──────────────────────────────────────────────────────────
today = date.today()
if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0

offset = st.session_state.week_offset
week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
week_end = week_start + timedelta(days=6)

nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
with nav_col1:
    if st.button("← Previous", use_container_width=True):
        st.session_state.week_offset -= 1
        st.rerun()
with nav_col2:
    st.markdown(
        f"<h4 style='text-align:center'>{week_start.strftime('%b %d')} — {week_end.strftime('%b %d, %Y')}</h4>",
        unsafe_allow_html=True,
    )
    if offset != 0:
        if st.button("Go to Current Week", use_container_width=True):
            st.session_state.week_offset = 0
            st.rerun()
with nav_col3:
    if st.button("Next →", use_container_width=True):
        st.session_state.week_offset += 1
        st.rerun()

st.divider()

# ── Weekly summary metrics ──────────────────────────────────────────────────
completion_rate = get_week_completion_rate(user_id, week_start)
averages = get_week_averages(user_id, week_start)
streak = get_overall_streak(user_id)

# Update journey and check for unlocks
unlock_info = update_journey(user_id)
if unlock_info:
    st.balloons()
    st.success(f":unlock: **Level Up!** You reached **{unlock_info['label']}** (Level {unlock_info['level']})! You can now track up to {unlock_info['max_habits']} habits.")

journey = get_journey(user_id)

met_cols = st.columns(5)
with met_cols[0]:
    st.metric("Streak", f"{streak} days")
with met_cols[1]:
    st.metric("Habit Completion", f"{completion_rate:.0%}")
with met_cols[2]:
    avg_mood = averages.get("mood")
    st.metric("Avg Mood", f"{avg_mood}/10" if avg_mood else "—")
with met_cols[3]:
    avg_energy = averages.get("energy")
    st.metric("Avg Energy", f"{avg_energy}/10" if avg_energy else "—")
with met_cols[4]:
    st.metric("Level", f"{get_level_label(journey['level'])}")
    next_info = get_next_unlock(user_id)
    if next_info:
        st.caption(f"{next_info['days_remaining']}d to next unlock")

st.divider()

# ── Habit Tracker Grid ──────────────────────────────────────────────────────
st.markdown("### Habits")
week_data = get_week_habit_data(user_id, week_start)
render_habit_grid(user_id, week_data, week_start)

# ── Add new habit ───────────────────────────────────────────────────────────
allowed, limit_msg = can_add_habit(user_id)
if not allowed:
    st.info(f":lock: {limit_msg}")
with st.expander("Add New Habit", expanded=False):
    with st.form("add_habit_form"):
        h_col1, h_col2 = st.columns(2)
        with h_col1:
            habit_name = st.text_input("Habit name")
        with h_col2:
            pillar_id = st.selectbox(
                "Pillar",
                options=list(PILLARS.keys()),
                format_func=lambda x: PILLARS[x]["display_name"],
            )

        # Implementation Intention builder
        st.markdown("**Implementation Intention** *(optional — makes habits 2-3x more likely to stick!)*")
        st.caption('Format: "After I [cue], I will [habit] at [location]"')
        ii_col1, ii_col2 = st.columns(2)
        with ii_col1:
            cue_behavior = st.text_input("After I...", placeholder="e.g., finish my morning coffee")
        with ii_col2:
            location = st.text_input("At/In...", placeholder="e.g., the kitchen")

        if st.form_submit_button("Add Habit"):
            if habit_name:
                can_add, msg = can_add_habit(user_id)
                if not can_add:
                    st.warning(msg)
                else:
                    from models.habit import create_habit
                    ii_text = None
                    if cue_behavior and location:
                        ii_text = f"After I {cue_behavior}, I will {habit_name} at {location}"
                    create_habit(user_id, pillar_id, habit_name,
                                 cue_behavior=cue_behavior or None,
                                 location=location or None,
                                 implementation_intention=ii_text)
                    st.toast(f"Habit added: {habit_name}")
                    st.rerun()

st.divider()

# ── Daily Check-in Detail ──────────────────────────────────────────────────
st.markdown("### Daily Check-ins")
checkins = get_week_checkins(user_id, week_start)

days = [(week_start + timedelta(days=i)) for i in range(7)]
selected_day = st.selectbox(
    "Select a day for detailed check-in",
    options=days,
    format_func=lambda d: f"{d.strftime('%A, %b %d')}" + (" (today)" if d == today else ""),
    index=min(today.weekday(), 6) if week_start <= today <= week_end else 0,
)

day_str = selected_day.isoformat()
existing = checkins.get(day_str)

with st.form(f"checkin_form_{day_str}"):
    st.markdown(f"**Check-in for {selected_day.strftime('%A, %B %d, %Y')}**")

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        mood = st.slider("Mood", 1, 10, existing["mood"] if existing and existing["mood"] else 5, key=f"mood_{day_str}")
    with row1_col2:
        energy = st.slider("Energy", 1, 10, existing["energy"] if existing and existing["energy"] else 5, key=f"energy_{day_str}")

    st.markdown("**Pillar Ratings**")
    pillar_cols = st.columns(3)
    pillar_ratings = {}
    pillar_fields = [
        (1, "nutrition_rating"), (2, "activity_rating"), (3, "sleep_rating"),
        (4, "stress_rating"), (5, "connection_rating"), (6, "substance_rating"),
    ]
    for i, (pid, field) in enumerate(pillar_fields):
        with pillar_cols[i % 3]:
            default = existing[field] if existing and existing.get(field) else 5
            pillar_ratings[field] = st.slider(
                PILLARS[pid]["display_name"], 1, 10, default, key=f"{field}_{day_str}"
            )

    st.markdown("**Reflections**")
    journal = st.text_area("Journal / How was your day?",
                           value=existing["journal_entry"] if existing and existing.get("journal_entry") else "",
                           key=f"journal_{day_str}", height=100)
    ref_col1, ref_col2, ref_col3 = st.columns(3)
    with ref_col1:
        gratitude = st.text_input("Gratitude",
                                   value=existing["gratitude"] if existing and existing.get("gratitude") else "",
                                   key=f"grat_{day_str}")
    with ref_col2:
        win = st.text_input("Win of the day",
                             value=existing["win_of_day"] if existing and existing.get("win_of_day") else "",
                             key=f"win_{day_str}")
    with ref_col3:
        challenge = st.text_input("Challenge",
                                   value=existing["challenge"] if existing and existing.get("challenge") else "",
                                   key=f"chal_{day_str}")

    if st.form_submit_button("Save Check-in", use_container_width=True, type="primary"):
        data = {
            "mood": mood,
            "energy": energy,
            **pillar_ratings,
            "journal_entry": journal,
            "gratitude": gratitude,
            "win_of_day": win,
            "challenge": challenge,
        }
        save_daily_checkin(user_id, day_str, data)
        st.success(f"Check-in saved for {selected_day.strftime('%B %d')}!")
        st.rerun()

# ── Auto Weekly Report ────────────────────────────────────────────────────
report = get_or_generate_report(user_id, week_start)
if report:
    st.divider()
    st.markdown("### Weekly Report")
    st.markdown(report["report"])

    stats = report.get("stats", {})
    if stats.get("pillar_avgs"):
        import plotly.graph_objects as go
        pillar_names = []
        pillar_vals = []
        for pid in sorted(stats["pillar_avgs"].keys()):
            if stats["pillar_avgs"][pid] is not None:
                pillar_names.append(PILLARS[int(pid)]["display_name"])
                pillar_vals.append(stats["pillar_avgs"][pid])

        if pillar_vals:
            fig = go.Figure(go.Bar(
                x=pillar_names, y=pillar_vals,
                marker_color=[PILLARS[pid]["color"] for pid in sorted(stats["pillar_avgs"].keys()) if stats["pillar_avgs"][pid] is not None],
            ))
            fig.update_layout(
                title="Average Pillar Ratings This Week",
                yaxis=dict(range=[0, 10], title="Rating"),
                height=300, margin=dict(t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

# ── Week overview of check-ins ──────────────────────────────────────────────
if checkins:
    st.divider()
    st.markdown("### Week at a Glance")
    glance_cols = st.columns(7)
    for i, day in enumerate(days):
        ds = day.isoformat()
        ci = checkins.get(ds)
        with glance_cols[i]:
            is_today = day == today
            st.markdown(f"**{'→ ' if is_today else ''}{day.strftime('%a %d')}**")
            if ci:
                st.markdown(f"Mood: {ci['mood']}/10" if ci.get("mood") else "—")
                st.markdown(f"Energy: {ci['energy']}/10" if ci.get("energy") else "—")
                if ci.get("win_of_day"):
                    st.caption(f"Win: {ci['win_of_day'][:30]}")
            else:
                st.caption("No check-in")
