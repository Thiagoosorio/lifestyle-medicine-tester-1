import streamlit as st
from config.settings import PILLARS, STAGES_OF_CHANGE
from services.coaching_service import (
    clear_conversation,
    get_coaching_response,
    get_gptcoach_response,
    _get_conversation_history,
)
from services.goal_service import get_active_goals
from services.wearable_wheel_service import compute_wearable_wheel
from services.wheel_service import get_current_wheel, get_stages


user_id = st.session_state.user_id

st.title("AI Lifestyle Medicine Coach")
st.markdown(
    "Your evidence-based coaching companion using Motivational Interviewing, "
    "Stages of Change, and the COM-B model."
)

context_options = {
    "general": "General Coaching",
    "gptcoach_pa": "Stanford GPTCoach Mode (Physical Activity)",
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
        if context_type == "gptcoach_pa":
            clear_conversation(user_id, context_type="gptcoach_pa")
        else:
            clear_conversation(user_id)
        st.rerun()

st.markdown("**Quick prompts:**")
quick_cols = st.columns(4)
if context_type == "thought_check":
    quick_prompts = {
        "I missed my workout": "I missed my workout today and now I feel like the whole week is ruined. What's the point of trying?",
        "Everyone judges me": "I feel like everyone at the gym is looking at me and judging me. I don't belong there.",
        "I will never change": "I've tried so many times to eat healthy and I always fail. I'll never be able to change.",
        "I should be further": "I should be much further along by now. Other people seem to change so easily.",
    }
elif context_type == "gptcoach_pa":
    quick_prompts = {
        "Build my 7-day plan": "Please build a 7-day movement plan based on my recent wearable and exercise data.",
        "Busy schedule plan": "I have work and family constraints. Help me build a realistic physical activity plan that still moves me forward.",
        "Missed workout fallback": "I keep missing planned workouts. Help me with if-then fallback rules and a minimum effective routine.",
        "Safe progression": "How can I safely progress my activity over the next 4 weeks without overdoing it?",
    }
else:
    quick_prompts = {
        "Weekly focus": "Based on my current data, what pillar should I prioritize this week and what's one specific action I can take?",
        "Set a goal": "Help me create a SMART-EST goal for my lowest-scoring pillar. Walk me through each criterion.",
        "Celebrate wins": "I'd like to celebrate my progress. What patterns of improvement do you see in my data?",
        "Overcome barrier": "I'm struggling with one of my lifestyle medicine pillars. Help me identify what's blocking me using the COM-B model.",
    }

selected_quick = None
for idx, (label, prompt) in enumerate(quick_prompts.items()):
    with quick_cols[idx]:
        if st.button(label, use_container_width=True, key=f"quick_{idx}"):
            selected_quick = prompt

with st.sidebar:
    st.markdown("### Your Context")
    st.caption("This is what the AI coach knows about you:")

    wheel = get_current_wheel(user_id)
    if wheel:
        st.markdown("**Wheel Scores:**")
        for pid in sorted(wheel["scores"].keys()):
            score = wheel["scores"][pid]
            filled = "#" * score
            empty = "-" * (10 - score)
            st.text(f"{PILLARS[pid]['display_name'][:12]:12s} {filled}{empty} {score}/10")
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
        for goal in goals[:3]:
            st.caption(f"- {goal['title']} ({goal['progress_pct']}%)")

st.divider()

if context_type == "gptcoach_pa":
    st.info(
        "Stanford GPTCoach-inspired mode is active. "
        "This app uses original prompts and your own data; it does not copy proprietary Active Choices scripts."
    )
    st.link_button("Open GPTCoach Research Repo", "https://github.com/StanfordHCI/GPTCoach-CHI2025")
    try:
        wearable = compute_wearable_wheel(user_id)
        c1, c2, c3 = st.columns(3)
        c1.metric("Wearable Readiness", f"{wearable.get('overall_readiness_10', 0)}/10")
        c2.metric("Wearable Resilience", f"{wearable.get('overall_resilience_10', 0)}/10")
        step_metric = (wearable.get("metrics") or {}).get("steps_count")
        if step_metric:
            c3.metric("Recent Steps", f"{step_metric.get('raw_value', 0):.0f}")
        else:
            c3.metric("Recent Steps", "N/A")
    except Exception:
        st.caption("Wearable snapshot is currently unavailable.")
    st.divider()

history_context = "gptcoach_pa" if context_type == "gptcoach_pa" else None
history = _get_conversation_history(user_id, context_type=history_context)

if not history:
    if context_type == "gptcoach_pa":
        st.chat_message("assistant").markdown(
            "Welcome to GPTCoach mode. I can build a realistic 7-day physical activity plan from your data, "
            "including fallback rules for busy days.\n\n"
            "What kind of week do you have ahead?"
        )
    else:
        st.chat_message("assistant").markdown(
            "Hello. I am your lifestyle medicine coach across all 6 pillars: "
            "Nutrition, Physical Activity, Sleep, Stress, Social Connection, and Substance Avoidance.\n\n"
            "How can I support you today?"
        )

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message...")
if selected_quick:
    user_input = selected_quick

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if context_type == "gptcoach_pa":
                response = get_gptcoach_response(user_id, user_input)
            else:
                response = get_coaching_response(user_id, user_input, context_type)
        st.markdown(response)

    st.rerun()
