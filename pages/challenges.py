"""Weekly Challenges page -- auto-generated challenges based on your weakest pillars."""

import streamlit as st
from datetime import date, timedelta
from config.settings import PILLARS
from services.challenge_service import (
    get_or_create_weekly_challenges,
    increment_challenge,
    get_challenge_history,
    get_all_time_stats,
)
from services.coin_service import award_coins

user_id = st.session_state.user_id

st.title("Weekly Challenges")
st.markdown(
    "Three personalized challenges each week, picked from your **weakest pillars**. "
    "Complete them to earn LifeCoins!"
)

# ── Helper constants ──────────────────────────────────────────────────────────
_DIFFICULTY_STARS = {"easy": 1, "medium": 2, "hard": 3}
_DIFFICULTY_LABELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. THIS WEEK'S CHALLENGES
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### This Week's Challenges")

challenges = get_or_create_weekly_challenges(user_id)

if not challenges:
    st.info("No challenges could be generated. Complete a daily check-in first so we can identify your focus areas!")
else:
    cols = st.columns(len(challenges))

    for idx, ch in enumerate(challenges):
        pillar = PILLARS.get(ch["pillar_id"], {})
        pillar_icon = pillar.get("icon", "")
        pillar_color = pillar.get("color", "#666")
        pillar_name = pillar.get("display_name", "Unknown")

        progress_pct = ch["current_count"] / ch["target_count"] if ch["target_count"] > 0 else 0
        is_done = ch["status"] == "completed"
        stars = _DIFFICULTY_STARS.get(ch["difficulty"], 2)
        difficulty_label = _DIFFICULTY_LABELS.get(ch["difficulty"], "Medium")

        with cols[idx]:
            # Card container
            with st.container(border=True):
                # Pillar badge
                st.markdown(
                    f"<span style='background-color:{pillar_color}; color:white; "
                    f"padding:2px 10px; border-radius:12px; font-size:0.85em;'>"
                    f"{pillar_icon} {pillar_name}</span>",
                    unsafe_allow_html=True,
                )

                # Title and description
                st.markdown(f"**{ch['title']}**")
                st.caption(ch["description"])

                # Progress bar
                st.progress(min(progress_pct, 1.0))
                st.markdown(
                    f"**{ch['current_count']}** / **{ch['target_count']}** completed"
                )

                # Difficulty and reward row
                star_display = ":star:" * stars
                st.markdown(
                    f"{star_display} {difficulty_label} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f":material/stars: **{ch['coin_reward']}** coins"
                )

                # Action / celebration
                if is_done:
                    st.success("Challenge Complete!")
                    st.balloons() if f"_celebrated_{ch['id']}" not in st.session_state else None
                    st.session_state[f"_celebrated_{ch['id']}"] = True
                else:
                    if st.button(
                        "+1 Done!",
                        key=f"inc_{ch['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        updated = increment_challenge(user_id, ch["id"])
                        if updated.get("status") == "completed":
                            st.toast(
                                f":material/stars: Challenge complete! +{ch['coin_reward']} LifeCoins!",
                            )
                        else:
                            st.toast(":white_check_mark: Progress logged!")
                        st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 2. WEEKLY STATS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### Weekly Stats")

# Current week stats
completed_this_week = sum(1 for c in challenges if c["status"] == "completed")
coins_this_week = sum(c["coin_reward"] for c in challenges if c["status"] == "completed")
all_time = get_all_time_stats(user_id)

stat_cols = st.columns(3)
with stat_cols[0]:
    st.metric(
        "Completed This Week",
        f"{completed_this_week}/{len(challenges)}",
        help="Challenges finished out of this week's total",
    )
with stat_cols[1]:
    st.metric(
        "Coins Earned This Week",
        str(coins_this_week),
        help="LifeCoins earned from completed challenges this week",
    )
with stat_cols[2]:
    st.metric(
        "Perfect Week Streak",
        f"{all_time['perfect_week_streak']} wk",
        help="Consecutive weeks where every challenge was completed",
    )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 3. CHALLENGE HISTORY
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### Challenge History")

history = get_challenge_history(user_id, weeks_back=4)

if len(history) <= 1:
    st.caption("Past week data will appear here after your first full week of challenges.")
else:
    # Skip the current week (already shown above) if it is the first entry
    past_weeks = [w for w in history if w["week_start"] != challenges[0]["week_start"]] if challenges else history

    if not past_weeks:
        st.caption("No past weeks to display yet. Check back next week!")
    else:
        for week in past_weeks:
            ws = week["week_start"]
            week_end = (date.fromisoformat(ws) + timedelta(days=6)).isoformat()
            header = f"Week of {ws} to {week_end}  --  {week['completed']}/{week['total']} completed  |  {week['coins_earned']} coins"

            with st.expander(header):
                for ch in week["challenges"]:
                    pillar = PILLARS.get(ch["pillar_id"], {})
                    icon = pillar.get("icon", "")
                    name = pillar.get("display_name", "")
                    status_icon = ":white_check_mark:" if ch["status"] == "completed" else ":x:"

                    st.markdown(
                        f"{status_icon} **{ch['title']}** ({icon} {name}) -- "
                        f"{ch['current_count']}/{ch['target_count']} -- "
                        f"{_DIFFICULTY_LABELS.get(ch['difficulty'], '')} -- "
                        f"{ch['coin_reward']} coins"
                    )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 4. LEADERBOARD AGAINST YOURSELF
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### Personal Leaderboard")
st.caption("Compete against your own best. Every week is a chance to set a new record.")

lb_cols = st.columns(4)

with lb_cols[0]:
    if all_time["best_week"]:
        bw = all_time["best_week"]
        st.metric(
            "Best Week Ever",
            f"{bw['cnt']}/{len(challenges) if challenges else '?'} done",
            help=f"Week of {bw['week_start']}",
        )
    else:
        st.metric("Best Week Ever", "N/A", help="Complete challenges to set your record")

with lb_cols[1]:
    st.metric(
        "Total Completed",
        str(all_time["total_completed"]),
        help="All-time challenges completed",
    )

with lb_cols[2]:
    rate_display = f"{all_time['completion_rate']:.0%}" if all_time["total_attempted"] > 0 else "N/A"
    st.metric(
        "Completion Rate",
        rate_display,
        help=f"{all_time['total_completed']} of {all_time['total_attempted']} challenges",
    )

with lb_cols[3]:
    st.metric(
        "Challenge Coins",
        str(all_time["total_coins"]),
        help="Total LifeCoins earned from challenges",
    )
