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
    -- Implementation Intention fields
    cue_behavior    TEXT,
    location        TEXT,
    implementation_intention TEXT,
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

-- ============================================================
-- NEW FEATURES: Engagement, Insights, CBT, Nudges
-- ============================================================

-- Engagement coins (gamification / reward system)
CREATE TABLE IF NOT EXISTS coin_transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    amount          INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    ref_date        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, reason, ref_date)
);

CREATE INDEX IF NOT EXISTS idx_coins_user ON coin_transactions(user_id, created_at);

-- Daily AI insights (post-check-in feedback loop)
CREATE TABLE IF NOT EXISTS daily_insights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    insight_date    TEXT NOT NULL,
    insight_text    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, insight_date)
);

-- CBT thought checks (thought distortion journal)
CREATE TABLE IF NOT EXISTS thought_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    original_thought TEXT NOT NULL,
    distortion_type  TEXT,
    reframe          TEXT,
    pillar_id        INTEGER REFERENCES pillars(id),
    ai_response      TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_thought_user ON thought_checks(user_id, created_at);

-- ============================================================
-- FEATURES: Implementation Intentions, Progressive Unlocking,
--           Micro-Lessons, Future Self Letters, Auto Reports
-- ============================================================

-- Progressive Habit Unlocking: user journey state
CREATE TABLE IF NOT EXISTS user_journey (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    max_habits      INTEGER NOT NULL DEFAULT 3,
    consistency_days INTEGER NOT NULL DEFAULT 0,
    level           INTEGER NOT NULL DEFAULT 1,
    unlocked_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- Micro-lesson content (seeded on init)
CREATE TABLE IF NOT EXISTS micro_lessons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    quiz_question   TEXT,
    quiz_options    TEXT,
    quiz_answer     INTEGER,
    lesson_type     TEXT NOT NULL DEFAULT 'article'
                        CHECK (lesson_type IN ('article', 'exercise', 'reflection')),
    difficulty      INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3),
    sort_order      INTEGER DEFAULT 0
);

-- User lesson progress
CREATE TABLE IF NOT EXISTS user_lesson_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    lesson_id       INTEGER NOT NULL REFERENCES micro_lessons(id),
    completed_at    TEXT NOT NULL DEFAULT (datetime('now')),
    quiz_score      INTEGER,
    UNIQUE(user_id, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_progress ON user_lesson_progress(user_id, completed_at);

-- Future Self Letters
CREATE TABLE IF NOT EXISTS future_self_letters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    letter_text     TEXT NOT NULL,
    delivery_date   TEXT NOT NULL,
    delivered       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_letters_user ON future_self_letters(user_id, delivery_date);

-- Auto Weekly Reports (data-driven summaries)
CREATE TABLE IF NOT EXISTS auto_weekly_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    week_start      TEXT NOT NULL,
    report_text     TEXT NOT NULL,
    stats_json      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_auto_reports ON auto_weekly_reports(user_id, week_start);

-- Habit celebration log (micro-feedback tracking)
CREATE TABLE IF NOT EXISTS habit_celebrations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    habit_id        INTEGER NOT NULL REFERENCES habits(id),
    celebration_type TEXT NOT NULL,
    feeling_tag     TEXT,
    log_date        TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- PHASE 1: SCIENCE FOUNDATION
-- ============================================================

-- Research evidence library (curated PubMed citations)
CREATE TABLE IF NOT EXISTS research_evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid            TEXT,
    doi             TEXT,
    title           TEXT NOT NULL,
    authors         TEXT,
    journal         TEXT,
    year            INTEGER,
    study_type      TEXT NOT NULL CHECK (study_type IN (
                        'meta_analysis', 'systematic_review', 'rct',
                        'cohort', 'case_control', 'cross_sectional',
                        'case_report', 'expert_opinion', 'guideline'
                    )),
    evidence_grade  TEXT NOT NULL CHECK (evidence_grade IN ('A', 'B', 'C', 'D')),
    pillar_id       INTEGER REFERENCES pillars(id),
    summary         TEXT NOT NULL,
    key_finding     TEXT,
    effect_size     TEXT,
    sample_size     INTEGER,
    population      TEXT,
    dose_response   TEXT,
    causation_note  TEXT,
    tags            TEXT,
    url             TEXT,
    journal_tier    TEXT CHECK (journal_tier IN ('elite', 'q1', 'q2', 'q3', 'q4')),
    domain          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_pillar ON research_evidence(pillar_id);
CREATE INDEX IF NOT EXISTS idx_evidence_grade ON research_evidence(evidence_grade);
CREATE INDEX IF NOT EXISTS idx_evidence_domain ON research_evidence(domain);

-- Links evidence to other entities (protocols, lessons, habits, insights)
CREATE TABLE IF NOT EXISTS evidence_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id     INTEGER NOT NULL REFERENCES research_evidence(id),
    entity_type     TEXT NOT NULL CHECK (entity_type IN (
                        'protocol', 'lesson', 'recommendation', 'biomarker',
                        'habit', 'insight', 'goal_template'
                    )),
    entity_id       INTEGER NOT NULL,
    relevance_note  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_links ON evidence_links(entity_type, entity_id);

-- Science-backed daily protocols
CREATE TABLE IF NOT EXISTS protocols (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar_id       INTEGER NOT NULL REFERENCES pillars(id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    timing          TEXT,
    duration        TEXT,
    frequency       TEXT NOT NULL DEFAULT 'daily',
    difficulty      INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3),
    mechanism       TEXT,
    expected_benefit TEXT,
    contraindications TEXT,
    sort_order      INTEGER DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_protocols_pillar ON protocols(pillar_id);

-- User's adopted protocols
CREATE TABLE IF NOT EXISTS user_protocols (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    protocol_id     INTEGER NOT NULL REFERENCES protocols(id),
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    notes           TEXT,
    UNIQUE(user_id, protocol_id)
);

-- Daily protocol completion log
CREATE TABLE IF NOT EXISTS protocol_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    protocol_id     INTEGER NOT NULL REFERENCES protocols(id),
    log_date        TEXT NOT NULL,
    completed       INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    UNIQUE(user_id, protocol_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_protocol_log ON protocol_log(user_id, log_date);

-- ============================================================
-- PHASE 2: ADVANCED TRACKING
-- ============================================================

-- Biomarker definitions (seeded from config)
CREATE TABLE IF NOT EXISTS biomarker_definitions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL CHECK (category IN (
                        'lipids', 'metabolic', 'inflammation', 'vitamins',
                        'hormones', 'thyroid', 'liver', 'kidney',
                        'blood_count', 'minerals'
                    )),
    unit            TEXT NOT NULL,
    standard_low    REAL,
    standard_high   REAL,
    optimal_low     REAL,
    optimal_high    REAL,
    critical_low    REAL,
    critical_high   REAL,
    description     TEXT,
    clinical_note   TEXT,
    pillar_id       INTEGER REFERENCES pillars(id),
    sort_order      INTEGER DEFAULT 0
);

-- User biomarker lab results
CREATE TABLE IF NOT EXISTS biomarker_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    biomarker_id    INTEGER NOT NULL REFERENCES biomarker_definitions(id),
    value           REAL NOT NULL,
    lab_date        TEXT NOT NULL,
    lab_name        TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, biomarker_id, lab_date)
);

CREATE INDEX IF NOT EXISTS idx_biomarker_results_user ON biomarker_results(user_id, lab_date);
CREATE INDEX IF NOT EXISTS idx_biomarker_results_marker ON biomarker_results(biomarker_id, lab_date);

-- Detailed sleep logs
CREATE TABLE IF NOT EXISTS sleep_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    sleep_date      TEXT NOT NULL,
    bedtime         TEXT,
    wake_time       TEXT,
    sleep_latency_min INTEGER,
    awakenings      INTEGER DEFAULT 0,
    wake_duration_min INTEGER DEFAULT 0,
    sleep_quality   INTEGER CHECK (sleep_quality BETWEEN 1 AND 5),
    naps_min        INTEGER DEFAULT 0,
    caffeine_cutoff TEXT,
    screen_cutoff   TEXT,
    alcohol         INTEGER DEFAULT 0,
    exercise_today  INTEGER DEFAULT 0,
    notes           TEXT,
    total_sleep_min INTEGER,
    sleep_efficiency REAL,
    sleep_score     INTEGER CHECK (sleep_score BETWEEN 0 AND 100),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, sleep_date)
);

CREATE INDEX IF NOT EXISTS idx_sleep_logs_user ON sleep_logs(user_id, sleep_date);

-- Chronotype assessment (one per user, updatable)
CREATE TABLE IF NOT EXISTS chronotype_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    meq_score       INTEGER,
    chronotype      TEXT CHECK (chronotype IN ('lion', 'bear', 'wolf', 'dolphin')),
    ideal_bedtime   TEXT,
    ideal_waketime  TEXT,
    assessed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- Fasting sessions
CREATE TABLE IF NOT EXISTS fasting_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    target_hours    REAL DEFAULT 16,
    actual_hours    REAL,
    fasting_type    TEXT DEFAULT '16:8' CHECK (fasting_type IN (
                        '12:12', '14:10', '16:8', '18:6', '20:4',
                        'OMAD', '24h', '36h', 'custom'
                    )),
    notes           TEXT,
    completed       INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fasting_user ON fasting_sessions(user_id, start_time);

-- Meal logs
CREATE TABLE IF NOT EXISTS meal_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    log_date        TEXT NOT NULL,
    meal_type       TEXT NOT NULL CHECK (meal_type IN (
                        'breakfast', 'lunch', 'dinner', 'snack'
                    )),
    description     TEXT NOT NULL,
    color_category  TEXT CHECK (color_category IN ('green', 'yellow', 'red')),
    plant_servings  INTEGER DEFAULT 0,
    fruit_servings  INTEGER DEFAULT 0,
    vegetable_servings INTEGER DEFAULT 0,
    whole_grain_servings INTEGER DEFAULT 0,
    legume_servings INTEGER DEFAULT 0,
    nut_seed_servings INTEGER DEFAULT 0,
    fiber_grams     REAL,
    water_glasses   INTEGER DEFAULT 0,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_meal_logs_user ON meal_logs(user_id, log_date);

-- Daily nutrition summary (computed daily)
CREATE TABLE IF NOT EXISTS nutrition_daily_summary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    summary_date    TEXT NOT NULL,
    total_meals     INTEGER DEFAULT 0,
    green_count     INTEGER DEFAULT 0,
    yellow_count    INTEGER DEFAULT 0,
    red_count       INTEGER DEFAULT 0,
    total_plant_servings INTEGER DEFAULT 0,
    total_fiber_grams REAL DEFAULT 0,
    total_water_glasses INTEGER DEFAULT 0,
    plant_score     INTEGER CHECK (plant_score BETWEEN 0 AND 100),
    nutrition_score INTEGER CHECK (nutrition_score BETWEEN 0 AND 100),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, summary_date)
);

CREATE INDEX IF NOT EXISTS idx_nutrition_summary ON nutrition_daily_summary(user_id, summary_date);

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 3: Calorie Counter + Diet Pattern Assessment
-- ══════════════════════════════════════════════════════════════════════════════

-- Curated food database (seeded from config/food_data.py, USDA FDC SR Legacy)
CREATE TABLE IF NOT EXISTS food_database (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL CHECK (category IN (
                        'fruits', 'vegetables', 'grains', 'legumes',
                        'nuts_seeds', 'dairy', 'meat', 'fish_seafood',
                        'oils_fats', 'beverages', 'snacks', 'condiments'
                    )),
    serving_size    REAL NOT NULL,
    serving_unit    TEXT NOT NULL,
    calories        REAL NOT NULL,
    protein_g       REAL NOT NULL DEFAULT 0,
    carbs_g         REAL NOT NULL DEFAULT 0,
    fat_g           REAL NOT NULL DEFAULT 0,
    fiber_g         REAL NOT NULL DEFAULT 0,
    vitamin_a_mcg   REAL DEFAULT 0,
    vitamin_c_mg    REAL DEFAULT 0,
    vitamin_d_mcg   REAL DEFAULT 0,
    calcium_mg      REAL DEFAULT 0,
    iron_mg         REAL DEFAULT 0,
    potassium_mg    REAL DEFAULT 0,
    sodium_mg       REAL DEFAULT 0,
    color_category  TEXT CHECK (color_category IN ('green', 'yellow', 'red')),
    is_plant_based  INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_food_name ON food_database(name);
CREATE INDEX IF NOT EXISTS idx_food_category ON food_database(category);

-- Individual food items logged by users
CREATE TABLE IF NOT EXISTS food_log_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    food_id         INTEGER NOT NULL REFERENCES food_database(id),
    log_date        TEXT NOT NULL,
    meal_type       TEXT NOT NULL CHECK (meal_type IN (
                        'breakfast', 'lunch', 'dinner', 'snack'
                    )),
    servings        REAL NOT NULL DEFAULT 1.0,
    calories        REAL NOT NULL,
    protein_g       REAL NOT NULL DEFAULT 0,
    carbs_g         REAL NOT NULL DEFAULT 0,
    fat_g           REAL NOT NULL DEFAULT 0,
    fiber_g         REAL NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_food_log_user ON food_log_items(user_id, log_date);

-- Daily calorie/macro summary (computed)
CREATE TABLE IF NOT EXISTS calorie_daily_summary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    summary_date    TEXT NOT NULL,
    total_calories  REAL DEFAULT 0,
    total_protein_g REAL DEFAULT 0,
    total_carbs_g   REAL DEFAULT 0,
    total_fat_g     REAL DEFAULT 0,
    total_fiber_g   REAL DEFAULT 0,
    total_items     INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, summary_date)
);

CREATE INDEX IF NOT EXISTS idx_calorie_summary ON calorie_daily_summary(user_id, summary_date);

-- User calorie/macro targets
CREATE TABLE IF NOT EXISTS calorie_targets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    calorie_target  REAL NOT NULL DEFAULT 2000,
    protein_target_g REAL NOT NULL DEFAULT 50,
    carbs_target_g  REAL NOT NULL DEFAULT 250,
    fat_target_g    REAL NOT NULL DEFAULT 65,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- Diet pattern assessment results
CREATE TABLE IF NOT EXISTS diet_assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    assessment_date TEXT NOT NULL,
    diet_type       TEXT NOT NULL CHECK (diet_type IN (
                        'mediterranean', 'dash', 'plant_based',
                        'flexitarian', 'standard_american', 'low_carb',
                        'paleo', 'traditional'
                    )),
    hei_score       INTEGER CHECK (hei_score BETWEEN 0 AND 100),
    component_scores TEXT,
    answers         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_diet_assess_user ON diet_assessments(user_id, assessment_date);

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 4: Daily Growth — Meditation, Quotes & Mindfulness
-- ══════════════════════════════════════════════════════════════════════════════

-- Meditation session logs (post-session, not a timer)
CREATE TABLE IF NOT EXISTS meditation_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    session_date    TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    meditation_type TEXT NOT NULL CHECK (meditation_type IN (
                        'guided', 'unguided', 'breathing', 'body_scan', 'walking'
                    )),
    mood_before     INTEGER CHECK (mood_before BETWEEN 1 AND 5),
    mood_after      INTEGER CHECK (mood_after BETWEEN 1 AND 5),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_meditation_user ON meditation_sessions(user_id, session_date);

-- Quote interactions (shown, favorited, reflected on)
CREATE TABLE IF NOT EXISTS quote_interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    quote_index     INTEGER NOT NULL,
    shown_date      TEXT NOT NULL,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    reflection_text TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, quote_index, shown_date)
);

CREATE INDEX IF NOT EXISTS idx_quote_user ON quote_interactions(user_id, shown_date);

-- Nudge display tracking (avoid short-term repeats)
CREATE TABLE IF NOT EXISTS nudge_shown (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    nudge_index     INTEGER NOT NULL,
    shown_date      TEXT NOT NULL,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, nudge_index, shown_date)
);

CREATE INDEX IF NOT EXISTS idx_nudge_user ON nudge_shown(user_id, shown_date);

-- Per-user daily growth state (today's assigned quote/nudge + streak)
CREATE TABLE IF NOT EXISTS daily_growth_state (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    current_quote_index INTEGER,
    current_nudge_index INTEGER,
    state_date          TEXT NOT NULL,
    meditation_streak   INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 5: SIBO & FODMAP Tracker
-- ══════════════════════════════════════════════════════════════════════════════

-- Daily GI symptom tracking
CREATE TABLE IF NOT EXISTS sibo_symptom_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    log_date        TEXT NOT NULL,
    bloating        INTEGER CHECK (bloating BETWEEN 0 AND 10),
    abdominal_pain  INTEGER CHECK (abdominal_pain BETWEEN 0 AND 10),
    gas             INTEGER CHECK (gas BETWEEN 0 AND 10),
    diarrhea        INTEGER CHECK (diarrhea BETWEEN 0 AND 3),
    constipation    INTEGER CHECK (constipation BETWEEN 0 AND 3),
    nausea          INTEGER CHECK (nausea BETWEEN 0 AND 10),
    fatigue         INTEGER CHECK (fatigue BETWEEN 0 AND 10),
    overall_score   INTEGER CHECK (overall_score BETWEEN 0 AND 10),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_sibo_symptoms_user ON sibo_symptom_logs(user_id, log_date);

-- FODMAP-aware food diary
CREATE TABLE IF NOT EXISTS sibo_food_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    log_date        TEXT NOT NULL,
    meal_type       TEXT NOT NULL CHECK (meal_type IN (
                        'breakfast', 'lunch', 'dinner', 'snack'
                    )),
    food_name       TEXT NOT NULL,
    food_category   TEXT,
    serving_size    REAL,
    serving_unit    TEXT,
    fodmap_rating   TEXT CHECK (fodmap_rating IN ('low', 'moderate', 'high')),
    fodmap_groups   TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sibo_food_user ON sibo_food_logs(user_id, log_date);

-- Low-FODMAP phase tracking (Elimination / Reintroduction / Personalization)
CREATE TABLE IF NOT EXISTS sibo_fodmap_phase (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    phase           TEXT NOT NULL CHECK (phase IN (
                        'elimination', 'reintroduction', 'personalization'
                    )),
    started_date    TEXT NOT NULL,
    ended_date      TEXT,
    reintro_group   TEXT,
    washout_until   TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sibo_phase_user ON sibo_fodmap_phase(user_id, started_date);

-- FODMAP reintroduction challenge results
CREATE TABLE IF NOT EXISTS sibo_reintro_challenges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    fodmap_group    TEXT NOT NULL,
    challenge_food  TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT,
    day1_symptoms   TEXT,
    day2_symptoms   TEXT,
    day3_symptoms   TEXT,
    washout_end     TEXT NOT NULL,
    tolerance       TEXT CHECK (tolerance IN ('tolerated', 'partial', 'not_tolerated')),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sibo_reintro_user ON sibo_reintro_challenges(user_id, start_date);

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 6: Body Metrics (moved from inline page) + User Settings + Garmin
-- ══════════════════════════════════════════════════════════════════════════════

-- Body metrics tracking
CREATE TABLE IF NOT EXISTS body_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    log_date        TEXT NOT NULL,
    weight_kg       REAL,
    height_cm       REAL,
    waist_cm        REAL,
    hip_cm          REAL,
    body_fat_pct    REAL,
    notes           TEXT,
    photo_note      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_body_metrics_user ON body_metrics(user_id, log_date);

-- User settings (goal weight, preferences)
CREATE TABLE IF NOT EXISTS user_settings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    goal_weight_kg  REAL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- Garmin Connect integration
CREATE TABLE IF NOT EXISTS garmin_connections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    garmin_email    TEXT NOT NULL,
    garmin_token    TEXT,
    last_sync       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- Per-user SIBO module state
CREATE TABLE IF NOT EXISTS sibo_user_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    active_diet     TEXT,
    current_phase   TEXT,
    phase_start     TEXT,
    total_symptom_logs INTEGER DEFAULT 0,
    total_food_logs INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- ═══════════════════════════════════════════════════════════════
-- ORGAN HEALTH SCORES
-- ═══════════════════════════════════════════════════════════════

-- Clinical/demographic inputs needed for certain scores
CREATE TABLE IF NOT EXISTS user_clinical_profile (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id),
    date_of_birth   TEXT,
    sex             TEXT CHECK (sex IN ('male', 'female')),
    height_cm       REAL,
    weight_kg       REAL,
    smoking_status  TEXT CHECK (smoking_status IN ('never', 'former', 'current')),
    diabetes_status INTEGER DEFAULT 0,
    systolic_bp     REAL,
    diastolic_bp    REAL,
    on_bp_medication INTEGER DEFAULT 0,
    on_statin       INTEGER DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Organ score definitions (seeded from config)
CREATE TABLE IF NOT EXISTS organ_score_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    organ_system        TEXT NOT NULL,
    tier                TEXT NOT NULL CHECK (tier IN ('validated', 'derived')),
    formula_key         TEXT NOT NULL,
    required_biomarkers TEXT NOT NULL,   -- JSON array of biomarker codes
    required_clinical   TEXT,            -- JSON array of clinical profile fields
    interpretation      TEXT NOT NULL,   -- JSON: ranges with labels + severity
    citation_pmid       TEXT,
    citation_text       TEXT,
    description         TEXT,
    sort_order          INTEGER DEFAULT 0
);

-- Computed organ score results (append-only log)
CREATE TABLE IF NOT EXISTS organ_score_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    score_def_id    INTEGER NOT NULL REFERENCES organ_score_definitions(id),
    value           REAL NOT NULL,
    label           TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('optimal','normal','elevated','high','critical')),
    input_snapshot  TEXT NOT NULL,       -- JSON of all inputs used
    lab_date        TEXT NOT NULL,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, score_def_id, lab_date)
);

CREATE INDEX IF NOT EXISTS idx_organscore_user ON organ_score_results(user_id, computed_at);
CREATE INDEX IF NOT EXISTS idx_organscore_def ON organ_score_results(score_def_id);

-- ═══════════════════════════════════════════════════════════════
-- EXERCISE TRACKER + STRAVA INTEGRATION
-- ═══════════════════════════════════════════════════════════════

-- Detailed exercise/workout logs
CREATE TABLE IF NOT EXISTS exercise_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    exercise_date   TEXT NOT NULL,
    exercise_type   TEXT NOT NULL CHECK (exercise_type IN (
                        'run', 'walk', 'cycle', 'swim', 'hike',
                        'strength', 'yoga', 'pilates', 'hiit',
                        'dance', 'rowing', 'elliptical', 'sports',
                        'stretching', 'other'
                    )),
    category        TEXT NOT NULL CHECK (category IN (
                        'cardio', 'strength', 'flexibility', 'mixed'
                    )),
    duration_min    INTEGER NOT NULL CHECK (duration_min > 0),
    intensity       TEXT NOT NULL CHECK (intensity IN (
                        'light', 'moderate', 'vigorous'
                    )),
    distance_km     REAL,
    calories        INTEGER,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    rpe             INTEGER CHECK (rpe BETWEEN 1 AND 10),
    notes           TEXT,
    source          TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'strava', 'garmin')),
    external_id     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, exercise_date, external_id)
);

CREATE INDEX IF NOT EXISTS idx_exercise_user ON exercise_logs(user_id, exercise_date);
CREATE INDEX IF NOT EXISTS idx_exercise_type ON exercise_logs(exercise_type);

-- Weekly exercise summary (computed)
CREATE TABLE IF NOT EXISTS exercise_weekly_summary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    week_start      TEXT NOT NULL,
    total_min       INTEGER DEFAULT 0,
    cardio_min      INTEGER DEFAULT 0,
    strength_min    INTEGER DEFAULT 0,
    flexibility_min INTEGER DEFAULT 0,
    moderate_min    INTEGER DEFAULT 0,
    vigorous_min    INTEGER DEFAULT 0,
    session_count   INTEGER DEFAULT 0,
    exercise_score  INTEGER CHECK (exercise_score BETWEEN 0 AND 100),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_exweekly_user ON exercise_weekly_summary(user_id, week_start);

-- Strava OAuth connection
CREATE TABLE IF NOT EXISTS strava_connections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    strava_athlete_id INTEGER,
    access_token    TEXT,
    refresh_token   TEXT,
    token_expires_at INTEGER,
    last_sync       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)
);
