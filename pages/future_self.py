"""Future Self Letter: write to your future self and receive it when you need it most."""

import streamlit as st
from datetime import date, timedelta
from db.database import get_connection

user_id = st.session_state.user_id

st.title("Letter to Your Future Self")
st.caption("Write to the person you're becoming. Your letter will be delivered when the time comes.")

# ── Check for undelivered letters that are due ────────────────────────────────
today_str = date.today().isoformat()
conn = get_connection()
try:
    due_letters = conn.execute(
        """SELECT * FROM future_self_letters
           WHERE user_id = ? AND delivered = 0 AND delivery_date <= ?
           ORDER BY delivery_date ASC""",
        (user_id, today_str),
    ).fetchall()
    due_letters = [dict(r) for r in due_letters]

    # Mark as delivered
    for letter in due_letters:
        conn.execute(
            "UPDATE future_self_letters SET delivered = 1 WHERE id = ?",
            (letter["id"],),
        )
    conn.commit()
finally:
    conn.close()

if due_letters:
    st.markdown("---")
    st.markdown("### :love_letter: A Letter From Your Past Self")
    for letter in due_letters:
        written_date = letter["created_at"][:10] if letter.get("created_at") else "Unknown"
        st.info(f"**Written on {written_date}:**")
        st.markdown(f"> {letter['letter_text']}")
        st.markdown("")
    st.divider()

# ── Past letters ──────────────────────────────────────────────────────────────
conn = get_connection()
try:
    all_letters = conn.execute(
        "SELECT * FROM future_self_letters WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    all_letters = [dict(r) for r in all_letters]
finally:
    conn.close()

# ── Writing prompts ──────────────────────────────────────────────────────────
prompts = [
    "Dear Future Me, right now I'm struggling with..., but I want you to know that...",
    "In [X] months, I will be the person who...",
    "The one habit that will change everything for me is...",
    "I'm writing this on a tough day because I want you to remember...",
    "The health goal I'm most excited about achieving is...",
    "To my future self who just hit a milestone: remember when...",
]

# ── Write a new letter ────────────────────────────────────────────────────────
st.markdown("### Write a New Letter")

# Show a random prompt for inspiration
import random
if "letter_prompt" not in st.session_state:
    st.session_state.letter_prompt = random.choice(prompts)
st.caption(f"*Inspiration: {st.session_state.letter_prompt}*")
if st.button("New prompt", key="new_prompt"):
    st.session_state.letter_prompt = random.choice(prompts)
    st.rerun()

with st.form("write_letter"):
    letter_text = st.text_area(
        "Dear Future Me...",
        height=200,
        placeholder="Write from your heart. Be honest about where you are now, what you're working toward, and what you want your future self to remember.",
    )

    delivery_options = {
        "1_week": "1 week from now",
        "1_month": "1 month from now",
        "3_months": "3 months from now",
        "6_months": "6 months from now",
        "1_year": "1 year from now",
    }
    delivery_choice = st.selectbox(
        "When should this letter be delivered?",
        options=list(delivery_options.keys()),
        format_func=lambda x: delivery_options[x],
        index=2,  # Default: 3 months
    )

    if st.form_submit_button("Seal & Send to My Future Self", type="primary", use_container_width=True):
        if letter_text.strip():
            delivery_deltas = {
                "1_week": timedelta(weeks=1),
                "1_month": timedelta(days=30),
                "3_months": timedelta(days=90),
                "6_months": timedelta(days=180),
                "1_year": timedelta(days=365),
            }
            delivery_date = date.today() + delivery_deltas[delivery_choice]

            conn = get_connection()
            try:
                conn.execute(
                    "INSERT INTO future_self_letters (user_id, letter_text, delivery_date) VALUES (?, ?, ?)",
                    (user_id, letter_text.strip(), delivery_date.isoformat()),
                )
                conn.commit()
            finally:
                conn.close()

            from services.coin_service import award_coins
            award_coins(user_id, 3, f"letter_{date.today().isoformat()}", date.today().isoformat())

            st.success(f"Letter sealed! It will be delivered on **{delivery_date.strftime('%B %d, %Y')}**.")
            st.toast(":material/stars: +3 LifeCoins for writing to your future self!")
            st.rerun()
        else:
            st.warning("Please write something before sending.")

# ── Letter history ────────────────────────────────────────────────────────────
if all_letters:
    st.divider()
    st.markdown("### Your Letters")

    pending = [l for l in all_letters if not l["delivered"]]
    delivered = [l for l in all_letters if l["delivered"]]

    if pending:
        st.markdown(f"**Pending Delivery ({len(pending)})**")
        for letter in pending:
            delivery = letter["delivery_date"]
            days_left = (date.fromisoformat(delivery) - date.today()).days
            with st.expander(f":hourglass: Arrives in {days_left} days ({delivery})"):
                st.caption("This letter is sealed until delivery day.")
                st.markdown(f"Written on: {letter['created_at'][:10]}")

    if delivered:
        st.markdown(f"**Delivered ({len(delivered)})**")
        for letter in delivered:
            with st.expander(f":love_letter: Written {letter['created_at'][:10]} — Delivered {letter['delivery_date']}"):
                st.markdown(f"> {letter['letter_text']}")
else:
    st.info("You haven't written any letters yet. Take a moment to write to the person you're becoming.")
