"""Daily Micro-Lesson Engine: 5-minute CBT-based lessons mapped to ACLM pillars."""

import streamlit as st
from datetime import date
from db.database import get_connection
from config.settings import PILLARS
from config.lessons import LESSON_LIBRARY

user_id = st.session_state.user_id

st.title("Daily Micro-Lessons")
st.caption("5-minute evidence-based lessons to deepen your lifestyle medicine knowledge")

# ── Seed lessons into DB if not present ──────────────────────────────────────
conn = get_connection()
try:
    count = conn.execute("SELECT COUNT(*) as cnt FROM micro_lessons").fetchone()["cnt"]
    if count == 0:
        for pillar_id, title, content, quiz_q, quiz_opts, quiz_ans, ltype, diff in LESSON_LIBRARY:
            conn.execute(
                """INSERT INTO micro_lessons (pillar_id, title, content, quiz_question, quiz_options, quiz_answer, lesson_type, difficulty)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (pillar_id, title, content, quiz_q, quiz_opts, quiz_ans, ltype, diff),
            )
        conn.commit()
finally:
    conn.close()

# ── Get all lessons and user progress ────────────────────────────────────────
conn = get_connection()
try:
    all_lessons = conn.execute(
        "SELECT * FROM micro_lessons ORDER BY pillar_id, sort_order, id"
    ).fetchall()
    all_lessons = [dict(r) for r in all_lessons]

    completed_ids = set()
    progress_rows = conn.execute(
        "SELECT lesson_id, quiz_score FROM user_lesson_progress WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    for row in progress_rows:
        completed_ids.add(row["lesson_id"])
finally:
    conn.close()

# ── Progress summary ─────────────────────────────────────────────────────────
total = len(all_lessons)
done = len(completed_ids)
pct = done / total if total > 0 else 0

prog_col1, prog_col2, prog_col3 = st.columns(3)
with prog_col1:
    st.metric("Lessons Completed", f"{done}/{total}")
with prog_col2:
    st.metric("Progress", f"{pct:.0%}")
with prog_col3:
    # Find today's recommended lesson (first uncompleted)
    today_lesson = None
    for lesson in all_lessons:
        if lesson["id"] not in completed_ids:
            today_lesson = lesson
            break
    if today_lesson:
        st.metric("Today's Lesson", today_lesson["title"][:25] + "...")
    else:
        st.metric("Status", "All Complete!")

st.progress(pct)
st.divider()

# ── Filter by pillar ─────────────────────────────────────────────────────────
filter_options = {"all": "All Pillars"} | {str(pid): PILLARS[pid]["display_name"] for pid in sorted(PILLARS.keys())}
pillar_filter = st.selectbox(
    "Filter by pillar",
    options=list(filter_options.keys()),
    format_func=lambda x: filter_options[x],
)

# ── Display lessons ──────────────────────────────────────────────────────────
filtered = all_lessons if pillar_filter == "all" else [l for l in all_lessons if str(l["pillar_id"]) == pillar_filter]

# Group by pillar
lessons_by_pillar = {}
for lesson in filtered:
    pid = lesson["pillar_id"]
    if pid not in lessons_by_pillar:
        lessons_by_pillar[pid] = []
    lessons_by_pillar[pid].append(lesson)

for pid in sorted(lessons_by_pillar.keys()):
    pillar = PILLARS.get(pid, {})
    st.markdown(f"### {pillar.get('icon', '')} {pillar.get('display_name', '')}")

    for lesson in lessons_by_pillar[pid]:
        is_completed = lesson["id"] in completed_ids
        status_icon = ":white_check_mark:" if is_completed else ":book:"
        difficulty_stars = ":star:" * lesson.get("difficulty", 1)
        lesson_type_icon = {
            "article": ":newspaper:",
            "exercise": ":muscle:",
            "reflection": ":thought_balloon:",
        }.get(lesson.get("lesson_type", "article"), ":book:")

        with st.expander(f"{status_icon} {lesson['title']} {lesson_type_icon} {difficulty_stars}"):
            st.markdown(lesson["content"])

            # Quiz section
            if lesson.get("quiz_question") and lesson.get("quiz_options"):
                st.divider()
                st.markdown("**Quick Quiz**")
                options = lesson["quiz_options"].split(",")
                correct_idx = lesson.get("quiz_answer", 0)

                if is_completed:
                    st.success(f"Completed! Correct answer: **{options[correct_idx]}**")
                else:
                    selected = st.radio(
                        lesson["quiz_question"],
                        options=options,
                        key=f"quiz_{lesson['id']}",
                        index=None,
                    )

                    if st.button("Submit Answer", key=f"submit_{lesson['id']}"):
                        if selected is None:
                            st.warning("Please select an answer.")
                        else:
                            answer_idx = options.index(selected)
                            is_correct = answer_idx == correct_idx
                            score = 100 if is_correct else 0

                            # Save progress
                            conn = get_connection()
                            try:
                                conn.execute(
                                    "INSERT OR IGNORE INTO user_lesson_progress (user_id, lesson_id, quiz_score) VALUES (?, ?, ?)",
                                    (user_id, lesson["id"], score),
                                )
                                conn.commit()
                            finally:
                                conn.close()

                            if is_correct:
                                st.success("Correct! Great job!")
                                from services.coin_service import award_coins
                                award_coins(user_id, 2, f"lesson_{lesson['id']}", date.today().isoformat())
                                st.toast(":material/stars: +2 LifeCoins for completing a lesson!")
                            else:
                                st.error(f"Not quite. The correct answer is: **{options[correct_idx]}**")
                                # Still mark as completed
                                conn = get_connection()
                                try:
                                    conn.execute(
                                        "INSERT OR IGNORE INTO user_lesson_progress (user_id, lesson_id, quiz_score) VALUES (?, ?, ?)",
                                        (user_id, lesson["id"], score),
                                    )
                                    conn.commit()
                                finally:
                                    conn.close()
                            st.rerun()
