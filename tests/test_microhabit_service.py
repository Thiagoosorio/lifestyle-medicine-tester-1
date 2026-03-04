"""TDD tests for the Micro Habits service.

Written FIRST (Red phase) — all tests fail until the service is implemented.
Covers: 2-Minute Rule, Habit Stacking, 4 Laws Scorecard, Never Miss Twice,
        Identity Statements, Temptation Bundling, Completion Heatmap, Milestones.
"""

from datetime import date, timedelta


# ── Helper ────────────────────────────────────────────────────────────────────

def _create_habit(db_conn, user_id, name, pillar_id=1, **extra):
    """Insert a habit and return its id."""
    conn = db_conn()
    cols = "user_id, pillar_id, name"
    vals = [user_id, pillar_id, name]
    for k, v in extra.items():
        cols += f", {k}"
        vals.append(v)
    placeholders = ", ".join(["?"] * len(vals))
    cursor = conn.execute(
        f"INSERT INTO habits ({cols}) VALUES ({placeholders})", vals,
    )
    conn.commit()
    hid = cursor.lastrowid
    conn.close()
    return hid


def _log_habit(db_conn, habit_id, user_id, log_date, completed=1):
    """Insert a habit_log entry."""
    conn = db_conn()
    conn.execute(
        "INSERT OR REPLACE INTO habit_log (habit_id, user_id, log_date, completed_count) "
        "VALUES (?, ?, ?, ?)",
        (habit_id, user_id, log_date, completed),
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 2-Minute Rule Tests (4)
# ═══════════════════════════════════════════════════════════════════════════════


def test_get_micro_version_known_habit(test_user, db_conn):
    """Default habit with a known name returns predefined micro version."""
    from services.microhabit_service import get_micro_version

    hid = _create_habit(db_conn, test_user, "30 minutes of movement")
    result = get_micro_version(hid)
    assert result == "Put on your workout shoes"


def test_get_micro_version_custom_habit(test_user, db_conn):
    """Custom habit with no predefined micro returns a generic template."""
    from services.microhabit_service import get_micro_version

    hid = _create_habit(db_conn, test_user, "Practice piano")
    result = get_micro_version(hid)
    assert "2 minutes" in result.lower() or "practice piano" in result.lower()


def test_set_micro_version(test_user, db_conn):
    """set_micro_version() stores text and get_micro_version() returns it."""
    from services.microhabit_service import set_micro_version, get_micro_version

    hid = _create_habit(db_conn, test_user, "Read 30 pages")
    set_micro_version(hid, "Read 1 paragraph")
    assert get_micro_version(hid) == "Read 1 paragraph"


def test_create_micro_habit_from_parent(test_user, db_conn):
    """create_micro_habit() creates a child habit with is_micro=1."""
    from services.microhabit_service import create_micro_habit, get_micro_version

    parent_id = _create_habit(
        db_conn, test_user, "5 minutes of meditation/breathing", pillar_id=4,
    )
    child_id = create_micro_habit(parent_id, test_user)
    assert child_id != parent_id

    conn = db_conn()
    child = dict(conn.execute("SELECT * FROM habits WHERE id = ?", (child_id,)).fetchone())
    conn.close()

    assert child["is_micro"] == 1
    assert child["pillar_id"] == 4
    assert child["is_active"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Habit Stacking Tests (7)
# ═══════════════════════════════════════════════════════════════════════════════


def test_create_stack(test_user, db_conn):
    """create_stack() creates a row and returns a positive stack_id."""
    from services.microhabit_service import create_stack

    sid = create_stack(test_user, "Morning Routine", anchor_cue="After morning coffee")
    assert isinstance(sid, int)
    assert sid > 0


def test_add_habit_to_stack(test_user, db_conn):
    """add_to_stack() sets stack_id and stack_order on the habit."""
    from services.microhabit_service import create_stack, add_to_stack

    sid = create_stack(test_user, "Morning Routine")
    hid = _create_habit(db_conn, test_user, "Meditate")
    add_to_stack(hid, sid, position=1)

    conn = db_conn()
    row = dict(conn.execute("SELECT stack_id, stack_order FROM habits WHERE id = ?", (hid,)).fetchone())
    conn.close()

    assert row["stack_id"] == sid
    assert row["stack_order"] == 1


def test_get_stack_habits_ordered(test_user, db_conn):
    """get_stack_habits() returns habits ordered by stack_order."""
    from services.microhabit_service import create_stack, add_to_stack, get_stack_habits

    sid = create_stack(test_user, "Morning")
    h1 = _create_habit(db_conn, test_user, "Stretch")
    h2 = _create_habit(db_conn, test_user, "Journal")
    h3 = _create_habit(db_conn, test_user, "Meditate")
    add_to_stack(h1, sid, position=1)
    add_to_stack(h2, sid, position=3)
    add_to_stack(h3, sid, position=2)

    habits = get_stack_habits(sid)
    names = [h["name"] for h in habits]
    assert names == ["Stretch", "Meditate", "Journal"]


def test_get_user_stacks(test_user, db_conn):
    """get_user_stacks() returns all active stacks with habit count."""
    from services.microhabit_service import create_stack, add_to_stack, get_user_stacks

    s1 = create_stack(test_user, "Morning")
    s2 = create_stack(test_user, "Evening")
    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")
    add_to_stack(h1, s1)
    add_to_stack(h2, s1)

    stacks = get_user_stacks(test_user)
    assert len(stacks) == 2
    morning = next(s for s in stacks if s["name"] == "Morning")
    assert morning["habit_count"] == 2


def test_remove_from_stack(test_user, db_conn):
    """remove_from_stack() clears stack_id and reorders remaining."""
    from services.microhabit_service import create_stack, add_to_stack, remove_from_stack, get_stack_habits

    sid = create_stack(test_user, "Morning")
    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")
    h3 = _create_habit(db_conn, test_user, "C")
    add_to_stack(h1, sid, position=1)
    add_to_stack(h2, sid, position=2)
    add_to_stack(h3, sid, position=3)

    remove_from_stack(h2)

    habits = get_stack_habits(sid)
    assert len(habits) == 2
    assert [h["name"] for h in habits] == ["A", "C"]

    # Check h2 is cleared
    conn = db_conn()
    row = dict(conn.execute("SELECT stack_id FROM habits WHERE id = ?", (h2,)).fetchone())
    conn.close()
    assert row["stack_id"] is None


def test_stack_text_generation(test_user, db_conn):
    """get_stack_text() returns a formatted chain text."""
    from services.microhabit_service import create_stack, add_to_stack, get_stack_text

    sid = create_stack(test_user, "Morning", anchor_cue="After coffee")
    h1 = _create_habit(db_conn, test_user, "Meditate")
    h2 = _create_habit(db_conn, test_user, "Journal")
    add_to_stack(h1, sid, position=1)
    add_to_stack(h2, sid, position=2)

    text = get_stack_text(sid)
    assert "After coffee" in text
    assert "Meditate" in text
    assert "Journal" in text


def test_reorder_stack(test_user, db_conn):
    """reorder_stack() applies new order."""
    from services.microhabit_service import create_stack, add_to_stack, reorder_stack, get_stack_habits

    sid = create_stack(test_user, "Morning")
    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")
    h3 = _create_habit(db_conn, test_user, "C")
    add_to_stack(h1, sid, position=1)
    add_to_stack(h2, sid, position=2)
    add_to_stack(h3, sid, position=3)

    reorder_stack(sid, [h3, h1, h2])

    habits = get_stack_habits(sid)
    assert [h["name"] for h in habits] == ["C", "A", "B"]


# ═══════════════════════════════════════════════════════════════════════════════
# 4 Laws Scorecard Tests (5)
# ═══════════════════════════════════════════════════════════════════════════════


def test_save_four_laws_scores(test_user, db_conn):
    """save_four_laws() stores 4 scores on the habit row."""
    from services.microhabit_service import save_four_laws

    hid = _create_habit(db_conn, test_user, "Exercise")
    save_four_laws(hid, obvious=4, attractive=2, easy=3, satisfying=5)

    conn = db_conn()
    row = dict(conn.execute(
        "SELECT law_obvious, law_attractive, law_easy, law_satisfying FROM habits WHERE id = ?",
        (hid,),
    ).fetchone())
    conn.close()

    assert row == {"law_obvious": 4, "law_attractive": 2, "law_easy": 3, "law_satisfying": 5}


def test_get_four_laws_scores(test_user, db_conn):
    """get_four_laws() retrieves stored scores as a dict."""
    from services.microhabit_service import save_four_laws, get_four_laws

    hid = _create_habit(db_conn, test_user, "Meditate")
    save_four_laws(hid, obvious=5, attractive=3, easy=4, satisfying=4)

    scores = get_four_laws(hid)
    assert scores["obvious"] == 5
    assert scores["attractive"] == 3


def test_get_weakest_law(test_user, db_conn):
    """get_weakest_law() returns the name of the lowest-scoring law."""
    from services.microhabit_service import save_four_laws, get_weakest_law

    hid = _create_habit(db_conn, test_user, "Read")
    save_four_laws(hid, obvious=4, attractive=1, easy=3, satisfying=5)
    assert get_weakest_law(hid) == "attractive"


def test_four_laws_diagnosis_all_habits(test_user, db_conn):
    """diagnose_all_habits() returns habits with weakest law and tip."""
    from services.microhabit_service import save_four_laws, diagnose_all_habits

    h1 = _create_habit(db_conn, test_user, "Exercise")
    h2 = _create_habit(db_conn, test_user, "Meditate")
    save_four_laws(h1, obvious=2, attractive=4, easy=4, satisfying=4)
    save_four_laws(h2, obvious=4, attractive=4, easy=1, satisfying=4)

    results = diagnose_all_habits(test_user)
    assert len(results) == 2

    exercise_diag = next(r for r in results if r["name"] == "Exercise")
    assert exercise_diag["weakest_law"] == "obvious"
    assert "tip" in exercise_diag

    meditate_diag = next(r for r in results if r["name"] == "Meditate")
    assert meditate_diag["weakest_law"] == "easy"


def test_four_laws_average_scores(test_user, db_conn):
    """get_four_laws_averages() returns average scores across scored habits."""
    from services.microhabit_service import save_four_laws, get_four_laws_averages

    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")
    save_four_laws(h1, obvious=4, attractive=2, easy=4, satisfying=4)
    save_four_laws(h2, obvious=2, attractive=4, easy=2, satisfying=4)

    avgs = get_four_laws_averages(test_user)
    assert avgs["obvious"] == 3.0
    assert avgs["attractive"] == 3.0
    assert avgs["easy"] == 3.0
    assert avgs["satisfying"] == 4.0


# ═══════════════════════════════════════════════════════════════════════════════
# Never Miss Twice Tests (3)
# ═══════════════════════════════════════════════════════════════════════════════


def test_missed_yesterday_true(test_user, db_conn):
    """get_missed_yesterday() returns habits NOT completed yesterday."""
    from services.microhabit_service import get_missed_yesterday

    today = date(2026, 3, 4)
    yesterday = today - timedelta(days=1)

    h1 = _create_habit(db_conn, test_user, "Exercise")
    h2 = _create_habit(db_conn, test_user, "Meditate")

    # Only h1 completed yesterday
    _log_habit(db_conn, h1, test_user, yesterday.isoformat(), completed=1)

    missed = get_missed_yesterday(test_user, ref_date=today)
    missed_names = [m["name"] for m in missed]
    assert "Meditate" in missed_names
    assert "Exercise" not in missed_names


def test_missed_yesterday_false(test_user, db_conn):
    """Empty list when all active habits completed yesterday."""
    from services.microhabit_service import get_missed_yesterday

    today = date(2026, 3, 4)
    yesterday = today - timedelta(days=1)

    h1 = _create_habit(db_conn, test_user, "Exercise")
    _log_habit(db_conn, h1, test_user, yesterday.isoformat(), completed=1)

    missed = get_missed_yesterday(test_user, ref_date=today)
    assert missed == []


def test_never_miss_twice_alert(test_user, db_conn):
    """Only flags habits missed 2+ consecutive days."""
    from services.microhabit_service import get_never_miss_twice_alerts

    today = date(2026, 3, 4)
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)

    h1 = _create_habit(db_conn, test_user, "Exercise")
    h2 = _create_habit(db_conn, test_user, "Meditate")

    # h1: completed day-before but NOT yesterday → missed once (no alert)
    _log_habit(db_conn, h1, test_user, day_before.isoformat(), completed=1)

    # h2: NOT completed either day → missed twice (alert!)
    # (no logs at all)

    alerts = get_never_miss_twice_alerts(test_user, ref_date=today)
    alert_names = [a["name"] for a in alerts]
    assert "Meditate" in alert_names
    assert "Exercise" not in alert_names


# ═══════════════════════════════════════════════════════════════════════════════
# Identity Statement Tests (2)
# ═══════════════════════════════════════════════════════════════════════════════


def test_set_and_get_identity(test_user, db_conn):
    """set_identity() stores text and get_identity() retrieves it."""
    from services.microhabit_service import set_identity, get_identity

    hid = _create_habit(db_conn, test_user, "30 minutes of movement")
    set_identity(hid, "I am a person who moves every day")
    assert get_identity(hid) == "I am a person who moves every day"


def test_get_identity_none(test_user, db_conn):
    """get_identity() returns None when no identity is set."""
    from services.microhabit_service import get_identity

    hid = _create_habit(db_conn, test_user, "Read")
    assert get_identity(hid) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Temptation Bundling Tests (2)
# ═══════════════════════════════════════════════════════════════════════════════


def test_set_and_get_temptation_bundle(test_user, db_conn):
    """set_temptation_bundle() stores and get_temptation_bundle() retrieves."""
    from services.microhabit_service import set_temptation_bundle, get_temptation_bundle

    hid = _create_habit(db_conn, test_user, "Exercise")
    set_temptation_bundle(hid, "Watch my favorite show while on the treadmill")
    assert get_temptation_bundle(hid) == "Watch my favorite show while on the treadmill"


def test_get_temptation_bundle_none(test_user, db_conn):
    """get_temptation_bundle() returns None when not set."""
    from services.microhabit_service import get_temptation_bundle

    hid = _create_habit(db_conn, test_user, "Meditate")
    assert get_temptation_bundle(hid) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Completion Heatmap Tests (3)
# ═══════════════════════════════════════════════════════════════════════════════


def test_heatmap_with_completions(test_user, db_conn):
    """get_completion_heatmap_data() returns correct rates for logged days."""
    from services.microhabit_service import get_completion_heatmap_data

    today = date(2026, 3, 4)
    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")

    # Both completed yesterday
    yesterday = (today - timedelta(days=1)).isoformat()
    _log_habit(db_conn, h1, test_user, yesterday)
    _log_habit(db_conn, h2, test_user, yesterday)

    data = get_completion_heatmap_data(test_user, weeks=2, ref_date=today)
    assert data[yesterday] == 1.0  # 2/2 = 100%


def test_heatmap_empty(test_user, db_conn):
    """get_completion_heatmap_data() returns zeros when no habits exist."""
    from services.microhabit_service import get_completion_heatmap_data

    today = date(2026, 3, 4)
    data = get_completion_heatmap_data(test_user, weeks=2, ref_date=today)
    # Should return a dict (possibly empty or all zeros)
    assert isinstance(data, dict)


def test_heatmap_partial(test_user, db_conn):
    """get_completion_heatmap_data() returns partial rates for mixed completion."""
    from services.microhabit_service import get_completion_heatmap_data

    today = date(2026, 3, 4)
    h1 = _create_habit(db_conn, test_user, "A")
    h2 = _create_habit(db_conn, test_user, "B")

    # Only h1 completed yesterday
    yesterday = (today - timedelta(days=1)).isoformat()
    _log_habit(db_conn, h1, test_user, yesterday)

    data = get_completion_heatmap_data(test_user, weeks=2, ref_date=today)
    assert data[yesterday] == 0.5  # 1/2 = 50%


# ═══════════════════════════════════════════════════════════════════════════════
# Milestone Badge Tests (3)
# ═══════════════════════════════════════════════════════════════════════════════


def test_milestone_earned_7_days(test_user, db_conn):
    """get_habit_milestones() marks 7-day milestone as earned for 7+ day streak."""
    from services.microhabit_service import get_habit_milestones

    today = date(2026, 3, 4)
    hid = _create_habit(db_conn, test_user, "Exercise")

    # Log 7 consecutive days
    for i in range(7):
        d = (today - timedelta(days=i + 1)).isoformat()
        _log_habit(db_conn, hid, test_user, d)

    milestones = get_habit_milestones(hid, test_user, ref_date=today)
    seven_day = next(m for m in milestones if m["days"] == 7)
    assert seven_day["earned"] is True


def test_milestone_not_earned(test_user, db_conn):
    """get_habit_milestones() shows unearned for short streaks."""
    from services.microhabit_service import get_habit_milestones

    today = date(2026, 3, 4)
    hid = _create_habit(db_conn, test_user, "Read")

    # Log only 3 days
    for i in range(3):
        d = (today - timedelta(days=i + 1)).isoformat()
        _log_habit(db_conn, hid, test_user, d)

    milestones = get_habit_milestones(hid, test_user, ref_date=today)
    seven_day = next(m for m in milestones if m["days"] == 7)
    assert seven_day["earned"] is False


def test_all_milestones_summary(test_user, db_conn):
    """get_all_milestones_summary() returns correct totals across habits."""
    from services.microhabit_service import get_all_milestones_summary

    today = date(2026, 3, 4)
    h1 = _create_habit(db_conn, test_user, "Exercise")
    h2 = _create_habit(db_conn, test_user, "Read")

    # h1: 8 day streak (earns 7-day badge)
    for i in range(8):
        _log_habit(db_conn, h1, test_user, (today - timedelta(days=i + 1)).isoformat())

    # h2: 3 day streak (no badges)
    for i in range(3):
        _log_habit(db_conn, h2, test_user, (today - timedelta(days=i + 1)).isoformat())

    summary = get_all_milestones_summary(test_user, ref_date=today)
    assert summary["total_earned"] >= 1  # At least the 7-day badge for h1
    assert summary["best_streak"] >= 8
