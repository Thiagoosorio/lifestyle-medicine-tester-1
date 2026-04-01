import services.coaching_service as coaching
from config.prompts import get_context_prompt


def _create_user(db_conn, username="gptcoach.user"):
    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        (username, "fakehash", "GPTCoach User", "gptcoach@example.com"),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def test_gptcoach_prompt_is_registered():
    prompt = get_context_prompt("gptcoach_pa")
    assert "7-day movement plan" in prompt
    assert "physical activity" in prompt.lower()


def test_history_can_be_filtered_by_context_type(db_conn, monkeypatch):
    monkeypatch.setattr(coaching, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    coaching._save_message(user_id, "user", "general message", context_type="general")
    coaching._save_message(user_id, "assistant", "general response", context_type="general")
    coaching._save_message(user_id, "user", "gpt message", context_type="gptcoach_pa")
    coaching._save_message(user_id, "assistant", "gpt response", context_type="gptcoach_pa")

    all_msgs = coaching._get_conversation_history(user_id, limit=10)
    gpt_msgs = coaching._get_conversation_history(user_id, limit=10, context_type="gptcoach_pa")

    assert len(all_msgs) == 4
    assert len(gpt_msgs) == 2
    assert gpt_msgs[0]["content"] == "gpt message"
    assert gpt_msgs[1]["content"] == "gpt response"


def test_clear_conversation_can_target_single_context(db_conn, monkeypatch):
    monkeypatch.setattr(coaching, "get_connection", db_conn)
    user_id = _create_user(db_conn, username="gptcoach.clear")

    coaching._save_message(user_id, "user", "general message", context_type="general")
    coaching._save_message(user_id, "user", "gpt message", context_type="gptcoach_pa")

    coaching.clear_conversation(user_id, context_type="gptcoach_pa")
    remaining = coaching._get_conversation_history(user_id, limit=10)

    assert len(remaining) == 1
    assert remaining[0]["content"] == "general message"
