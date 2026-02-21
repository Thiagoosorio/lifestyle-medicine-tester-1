import streamlit as st
from config.settings import PILLARS, STAGES_OF_CHANGE
from services.coaching_service import get_coaching_response, clear_conversation, _get_conversation_history, _assemble_user_context
from services.wheel_service import get_current_wheel, get_stages
from services.goal_service import get_active_goals

user_id = st.session_state.user_id

st.title("AI Lifestyle Medicine Coach")
st.markdown("Your evidence-based coaching companion using Motivational Interviewing, Stages of Change, and the COM-B model.")

# ── Context selector ────────────────────────────────────────────────────────
context_options = {
    "general": "General Coaching",
    "wheel_review": "Wheel of Life Review",
    "goal_help": "Goal Help (SMART-EST)",
    "weekly_reflection": "Weekly Reflection",
    "barrier_analysis": "Barrier Analysis (COM-B)",
    "thought_check": "Thought Check (CBT)",
}

col_ctx, col_clear = st.columns([3, 1])
with col_ctx:
    context_type = st.radio(
        "Coaching Mode",
        options=list(context_options.keys()),
        format_func=lambda x: context_options[x],
        horizontal=True,
    )
with col_clear:
    if st.button("Clear Chat", use_container_width=True):
        clear_conversation(user_id)
        st.rerun()

# ── Quick action buttons ───────────────────────────────────────────────────
st.markdown("**Quick prompts:**")
quick_cols = st.columns(4)
if context_type == "thought_check":
    quick_prompts = {
        "I missed my workout, week is ruined": "I missed my workout today and now I feel like the whole week is ruined. What's the point of trying?",
        "Everyone judges me at the gym": "I feel like everyone at the gym is looking at me and judging me. I don't belong there.",
        "I'll never change": "I've tried so many times to eat healthy and I always fail. I'll never be able to change.",
        "I should be further along": "I should be much further along by now. Other people seem to change so easily.",
    }
else:
    quick_prompts = {
        "What should I focus on this week?": "Based on my current data, what pillar should I prioritize this week and what's one specific action I can take?",
        "Help me set a goal": "Help me create a SMART-EST goal for my lowest-scoring pillar. Walk me through each criterion.",
        "Celebrate my wins": "I'd like to celebrate my progress. What patterns of improvement do you see in my data?",
        "Overcome a barrier": "I'm struggling with one of my lifestyle medicine pillars. Help me identify what's blocking me using the COM-B model.",
    }

selected_quick = None
for i, (label, prompt) in enumerate(quick_prompts.items()):
    with quick_cols[i]:
        if st.button(label, use_container_width=True, key=f"quick_{i}"):
            selected_quick = prompt

# ── Sidebar context panel ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Your Context")
    st.caption("This is what the AI coach knows about you:")

    wheel = get_current_wheel(user_id)
    if wheel:
        st.markdown("**Wheel Scores:**")
        for pid in sorted(wheel["scores"].keys()):
            score = wheel["scores"][pid]
            bar = "█" * score + "░" * (10 - score)
            st.text(f"{PILLARS[pid]['display_name'][:12]:12s} {bar} {score}/10")
    else:
        st.caption("No wheel assessment yet.")

    stages = get_stages(user_id)
    if stages:
        st.markdown("**Stage of Change:**")
        for pid, stage in sorted(stages.items()):
            st.text(f"{PILLARS[pid]['display_name'][:12]:12s} {STAGES_OF_CHANGE[stage]['label']}")

    goals = get_active_goals(user_id)
    if goals:
        st.markdown(f"**Active Goals:** {len(goals)}")
        for g in goals[:3]:
            st.caption(f"- {g['title']} ({g['progress_pct']}%)")

st.divider()

# ── Chat interface ──────────────────────────────────────────────────────────
history = _get_conversation_history(user_id)

# Display message history
if not history:
    st.chat_message("assistant").markdown(
        "Hello! I'm your lifestyle medicine coach. I'm here to help you thrive across all 6 pillars — "
        "Nutrition, Physical Activity, Sleep, Stress Management, Social Connection, and Substance Avoidance.\n\n"
        "How can I support you today? You can use the quick prompts above or ask me anything!"
    )

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new message
user_input = st.chat_input("Type your message...")

if selected_quick:
    user_input = selected_quick

if user_input:
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get and display response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_coaching_response(user_id, user_input, context_type)
        st.markdown(response)

    st.rerun()
