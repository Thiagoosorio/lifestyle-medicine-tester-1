import streamlit as st
from datetime import date, timedelta
import calendar
from config.settings import PILLARS
from services.checkin_service import get_month_checkins, get_week_averages
from services.habit_service import get_day_completion_rate
from services.wheel_service import get_history
from components.calendar_heatmap import render_calendar_heatmap
from components.progress_charts import render_mood_energy_chart, render_pillar_trends
from components.wheel_chart import create_comparison_chart
from models.review import get_weekly_reviews_for_month

user_id = st.session_state.user_id

st.title("Monthly Plan")

# ── Month navigator ─────────────────────────────────────────────────────────
today = date.today()
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

offset = st.session_state.month_offset
view_date = date(today.year, today.month, 1)
# Apply offset
month = today.month + offset
year = today.year
while month > 12:
    month -= 12
    year += 1
while month < 1:
    month += 12
    year -= 1

nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
with nav_col1:
    if st.button("← Previous", use_container_width=True, key="prev_month"):
        st.session_state.month_offset -= 1
        st.rerun()
with nav_col2:
    st.markdown(
        f"<h3 style='text-align:center'>{calendar.month_name[month]} {year}</h3>",
        unsafe_allow_html=True,
    )
    if offset != 0:
        if st.button("Go to Current Month", use_container_width=True, key="cur_month"):
            st.session_state.month_offset = 0
            st.rerun()
with nav_col3:
    if st.button("Next →", use_container_width=True, key="next_month"):
        st.session_state.month_offset += 1
        st.rerun()

st.divider()

# ── Calendar Heatmap ────────────────────────────────────────────────────────
st.markdown("### Habit Completion Calendar")

# Build day values
days_in_month = calendar.monthrange(year, month)[1]
day_values = {}
for d in range(1, days_in_month + 1):
    day_date = date(year, month, d)
    if day_date <= today:
        rate = get_day_completion_rate(user_id, day_date.isoformat())
        day_values[day_date.isoformat()] = rate

render_calendar_heatmap(year, month, day_values)

# ── Weekly Summaries ────────────────────────────────────────────────────────
st.divider()
st.markdown("### Weekly Summaries")

# Find all Mondays in this month
mondays = []
first_day = date(year, month, 1)
last_day = date(year, month, days_in_month)
d = first_day
while d <= last_day:
    if d.weekday() == 0:
        mondays.append(d)
    d += timedelta(days=1)
# Include the Monday before the 1st if the 1st is not a Monday
if first_day.weekday() != 0:
    prev_monday = first_day - timedelta(days=first_day.weekday())
    mondays.insert(0, prev_monday)

reviews = get_weekly_reviews_for_month(user_id, year, month)
reviews_by_week = {r["week_start"]: r for r in reviews}

for monday in mondays:
    week_end = monday + timedelta(days=6)
    avg = get_week_averages(user_id, monday)
    review = reviews_by_week.get(monday.isoformat())

    with st.expander(f"Week: {monday.strftime('%b %d')} — {week_end.strftime('%b %d')}"):
        if avg:
            met_cols = st.columns(4)
            with met_cols[0]:
                st.metric("Days Checked In", avg.get("days_checked_in", 0))
            with met_cols[1]:
                st.metric("Avg Mood", f"{avg['mood']}/10" if avg.get("mood") else "—")
            with met_cols[2]:
                st.metric("Avg Energy", f"{avg['energy']}/10" if avg.get("energy") else "—")
            with met_cols[3]:
                from services.habit_service import get_week_completion_rate
                rate = get_week_completion_rate(user_id, monday)
                st.metric("Habit Completion", f"{rate:.0%}")
        else:
            st.caption("No check-in data for this week.")

        if review:
            if review.get("highlights"):
                st.markdown(f"**Highlights:** {review['highlights']}")
            if review.get("challenges"):
                st.markdown(f"**Challenges:** {review['challenges']}")
            if review.get("ai_summary"):
                st.info(f"**AI Summary:** {review['ai_summary']}")

# ── Monthly Trends ──────────────────────────────────────────────────────────
st.divider()
st.markdown("### Monthly Trends")

checkins = list(get_month_checkins(user_id, year, month).values())
if checkins:
    tab_mood, tab_pillars = st.tabs(["Mood & Energy", "Pillar Ratings"])
    with tab_mood:
        render_mood_energy_chart(checkins)
    with tab_pillars:
        render_pillar_trends(checkins)
else:
    st.info("No check-in data this month. Start checking in daily to see trends!")

# ── Wheel Comparison ────────────────────────────────────────────────────────
st.divider()
st.markdown("### Wheel of Life Comparison")

history = get_history(user_id, limit=10)
month_assessments = [
    h for h in history
    if h["assessed_at"][:7] == f"{year}-{month:02d}"
]

if len(month_assessments) >= 2:
    compare_data = [
        {"scores": month_assessments[-1]["scores"], "label": f"Start ({month_assessments[-1]['assessed_at'][:10]})"},
        {"scores": month_assessments[0]["scores"], "label": f"Latest ({month_assessments[0]['assessed_at'][:10]})"},
    ]
    st.plotly_chart(create_comparison_chart(compare_data), use_container_width=True)
elif month_assessments:
    from components.wheel_chart import create_wheel_chart
    st.plotly_chart(
        create_wheel_chart(month_assessments[0]["scores"], title=f"Assessment: {month_assessments[0]['assessed_at'][:10]}"),
        use_container_width=True,
    )
else:
    st.caption("No wheel assessments this month.")
