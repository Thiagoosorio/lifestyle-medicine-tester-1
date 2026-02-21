-- ============================================================
-- Lifestyle Medicine Wheel of Life App - Database Schema
-- ============================================================

-- Reference table for the 6 ACLM pillars
CREATE TABLE IF NOT EXISTS pillars (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    icon        TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Seed the 6 ACLM pillars
INSERT OR IGNORE INTO pillars (id, name, display_name, description, icon, sort_order) VALUES
(1, 'nutrition', 'Nutrition', 'Whole-food, plant-predominant eating. Emphasis on vegetables, fruits, whole grains, legumes, nuts, and seeds.', 'nutrition', 1),
(2, 'physical_activity', 'Physical Activity', 'Regular movement: 150+ min/week moderate or 75+ min/week vigorous aerobic activity, plus strength training 2+ days/week.', 'directions_run', 2),
(3, 'sleep', 'Sleep', 'Restorative sleep: consistently achieving 7-9 hours of quality sleep with good sleep hygiene practices.', 'bedtime', 3),
(4, 'stress_management', 'Stress Management', 'Practices to manage chronic stress: mindfulness, meditation, breathing exercises, yoga, time in nature.', 'self_improvement', 4),
(5, 'social_connection', 'Social Connection', 'Meaningful relationships, community involvement, and a sense of belonging and connectedness.', 'group', 5),
(6, 'substance_avoidance', 'Substance Avoidance', 'Eliminating tobacco, limiting or eliminating alcohol, and avoiding recreational drugs and other harmful substances.', 'block', 6);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    display_name    TEXT,
    email           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Wheel assessments: 6 rows per session (one per pillar)
CREATE TABLE IF NOT EXISTS wheel_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    score           INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
    notes           TEXT,
    assessed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    session_id      TEXT NOT NULL,
    UNIQUE(session_id, pillar_id)
);

CREATE INDEX IF NOT EXISTS idx_wheel_user_date ON wheel_assessments(user_id, assessed_at);
CREATE INDEX IF NOT EXISTS idx_wheel_session ON wheel_assessments(session_id);

-- Stages of Change per pillar (append-only log)
CREATE TABLE IF NOT EXISTS stage_of_change (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    stage           TEXT NOT NULL CHECK (stage IN (
                        'precontemplation', 'contemplation', 'preparation',
                        'action', 'maintenance'
                    )),
    assessed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_stage_user ON stage_of_change(user_id, pillar_id, assessed_at);

-- COM-B barrier assessment
CREATE TABLE IF NOT EXISTS comb_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    capability_physical     INTEGER CHECK (capability_physical BETWEEN 1 AND 5),
    capability_psychological INTEGER CHECK (capability_psychological BETWEEN 1 AND 5),
    opportunity_physical    INTEGER CHECK (opportunity_physical BETWEEN 1 AND 5),
    opportunity_social      INTEGER CHECK (opportunity_social BETWEEN 1 AND 5),
    motivation_reflective   INTEGER CHECK (motivation_reflective BETWEEN 1 AND 5),
    motivation_automatic    INTEGER CHECK (motivation_automatic BETWEEN 1 AND 5),
    primary_barrier TEXT,
    notes           TEXT,
    assessed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- SMART-EST Goals
CREATE TABLE IF NOT EXISTS goals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    title           TEXT NOT NULL,
    specific        TEXT NOT NULL,
    measurable      TEXT NOT NULL,
    achievable      TEXT NOT NULL,
    relevant        TEXT NOT NULL,
    time_bound      TEXT NOT NULL,
    evidence_base   TEXT,
    strategic       TEXT,
    tailored        TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'abandoned', 'paused')),
    progress_pct    INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    target_value    REAL,
    current_value   REAL DEFAULT 0,
    unit            TEXT,
    start_date      TEXT NOT NULL,
    target_date     TEXT NOT NULL,
    completed_at    TEXT,
    abandoned_at    TEXT,
    abandon_reason  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_goals_user_status ON goals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_goals_pillar ON goals(user_id, pillar_id);

-- Goal progress entries
CREATE TABLE IF NOT EXISTS goal_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id         INTEGER NOT NULL REFERENCES goals(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    progress_pct    INTEGER NOT NULL CHECK (progress_pct BETWEEN 0 AND 100),
    current_value   REAL,
    notes           TEXT,
    logged_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_goalprogress ON goal_progress(goal_id, logged_at);

-- User-defined habits linked to pillars
CREATE TABLE IF NOT EXISTS habits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    name            TEXT NOT NULL,
    description     TEXT,
    frequency       TEXT NOT NULL DEFAULT 'daily'
                        CHECK (frequency IN ('daily', 'weekdays', 'weekends', 'custom')),
    custom_days     TEXT,
    target_per_day  INTEGER DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id, is_active);

-- Daily habit completion log
CREATE TABLE IF NOT EXISTS habit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id        INTEGER NOT NULL REFERENCES habits(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    log_date        TEXT NOT NULL,
    completed_count INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    UNIQUE(habit_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_habitlog_date ON habit_log(user_id, log_date);
CREATE INDEX IF NOT EXISTS idx_habitlog_habit ON habit_log(habit_id, log_date);

-- Daily check-ins (one per day per user)
CREATE TABLE IF NOT EXISTS daily_checkins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    checkin_date    TEXT NOT NULL,
    mood            INTEGER CHECK (mood BETWEEN 1 AND 10),
    energy          INTEGER CHECK (energy BETWEEN 1 AND 10),
    nutrition_rating     INTEGER CHECK (nutrition_rating BETWEEN 1 AND 10),
    activity_rating      INTEGER CHECK (activity_rating BETWEEN 1 AND 10),
    sleep_rating         INTEGER CHECK (sleep_rating BETWEEN 1 AND 10),
    stress_rating        INTEGER CHECK (stress_rating BETWEEN 1 AND 10),
    connection_rating    INTEGER CHECK (connection_rating BETWEEN 1 AND 10),
    substance_rating     INTEGER CHECK (substance_rating BETWEEN 1 AND 10),
    journal_entry   TEXT,
    gratitude       TEXT,
    win_of_day      TEXT,
    challenge       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, checkin_date)
);

CREATE INDEX IF NOT EXISTS idx_checkin_user_date ON daily_checkins(user_id, checkin_date);

-- Weekly reviews
CREATE TABLE IF NOT EXISTS weekly_reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    week_start      TEXT NOT NULL,
    avg_mood        REAL,
    avg_energy      REAL,
    habit_completion_pct REAL,
    reflection      TEXT,
    highlights      TEXT,
    challenges      TEXT,
    next_week_focus TEXT,
    ai_summary      TEXT,
    ai_insights     TEXT,
    ai_suggestions  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_review_user ON weekly_reviews(user_id, week_start);

-- AI coaching conversation log
CREATE TABLE IF NOT EXISTS coaching_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    context_type    TEXT,
    pillar_id       INTEGER REFERENCES pillars(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_coaching_user ON coaching_messages(user_id, created_at);
