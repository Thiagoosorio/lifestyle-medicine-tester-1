"""Service for calorie/macro tracking, food database queries, and daily summaries."""

from db.database import get_connection
from datetime import date, timedelta


def seed_food_database():
    """Seed the food_database table from config/food_data.py (idempotent)."""
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM food_database").fetchone()[0]
        if count > 0:
            return
        from config.food_data import FOOD_DATABASE
        for food in FOOD_DATABASE:
            conn.execute(
                """INSERT INTO food_database
                   (name, category, serving_size, serving_unit,
                    calories, protein_g, carbs_g, fat_g, fiber_g,
                    vitamin_a_mcg, vitamin_c_mg, vitamin_d_mcg,
                    calcium_mg, iron_mg, potassium_mg, sodium_mg,
                    color_category, is_plant_based)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                food,
            )
        conn.commit()
    finally:
        conn.close()


def search_foods(query, category=None, limit=20):
    """Search food database by name (LIKE). Optional category filter."""
    conn = get_connection()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM food_database WHERE name LIKE ? AND category = ? ORDER BY name LIMIT ?",
                (f"%{query}%", category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM food_database WHERE name LIKE ? ORDER BY name LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_food_by_id(food_id):
    """Get a single food entry by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM food_database WHERE id = ?", (food_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_foods_by_category(category):
    """Get all foods in a category."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM food_database WHERE category = ? ORDER BY name", (category,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_foods():
    """Get all foods for the selectbox."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM food_database ORDER BY category, name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def log_food_item(user_id, food_id, log_date, meal_type, servings=1.0):
    """Log a food item with auto-calculated macros. Returns the created record."""
    food = get_food_by_id(food_id)
    if not food:
        return None

    calories = round(food["calories"] * servings, 1)
    protein = round(food["protein_g"] * servings, 1)
    carbs = round(food["carbs_g"] * servings, 1)
    fat = round(food["fat_g"] * servings, 1)
    fiber = round(food["fiber_g"] * servings, 1)

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO food_log_items
               (user_id, food_id, log_date, meal_type, servings,
                calories, protein_g, carbs_g, fat_g, fiber_g)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, food_id, log_date, meal_type, servings,
             calories, protein, carbs, fat, fiber),
        )
        conn.commit()
    finally:
        conn.close()

    compute_calorie_summary(user_id, log_date)
    return {
        "food_name": food["name"], "servings": servings,
        "calories": calories, "protein_g": protein,
        "carbs_g": carbs, "fat_g": fat,
    }


def delete_food_item(item_id, user_id):
    """Delete a food log item and recompute daily summary."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT log_date FROM food_log_items WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        ).fetchone()
        if not row:
            return
        log_date = row["log_date"]
        conn.execute("DELETE FROM food_log_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
    finally:
        conn.close()
    compute_calorie_summary(user_id, log_date)


def get_food_items_for_date(user_id, log_date):
    """Get all food log items for a specific date, joined with food names."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT fi.*, fd.name as food_name, fd.category, fd.serving_size,
                      fd.serving_unit, fd.color_category
               FROM food_log_items fi
               JOIN food_database fd ON fi.food_id = fd.id
               WHERE fi.user_id = ? AND fi.log_date = ?
               ORDER BY fi.created_at""",
            (user_id, log_date),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def compute_calorie_summary(user_id, log_date):
    """Compute and upsert daily calorie/macro totals."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                 SUM(calories) as total_calories,
                 SUM(protein_g) as total_protein_g,
                 SUM(carbs_g) as total_carbs_g,
                 SUM(fat_g) as total_fat_g,
                 SUM(fiber_g) as total_fiber_g,
                 COUNT(*) as total_items
               FROM food_log_items
               WHERE user_id = ? AND log_date = ?""",
            (user_id, log_date),
        ).fetchone()

        if not row or not row["total_items"]:
            conn.execute(
                "DELETE FROM calorie_daily_summary WHERE user_id = ? AND summary_date = ?",
                (user_id, log_date),
            )
            conn.commit()
            return

        conn.execute(
            """INSERT INTO calorie_daily_summary
               (user_id, summary_date, total_calories, total_protein_g,
                total_carbs_g, total_fat_g, total_fiber_g, total_items)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id, summary_date) DO UPDATE SET
                 total_calories=excluded.total_calories,
                 total_protein_g=excluded.total_protein_g,
                 total_carbs_g=excluded.total_carbs_g,
                 total_fat_g=excluded.total_fat_g,
                 total_fiber_g=excluded.total_fiber_g,
                 total_items=excluded.total_items""",
            (user_id, log_date,
             round(row["total_calories"] or 0, 1),
             round(row["total_protein_g"] or 0, 1),
             round(row["total_carbs_g"] or 0, 1),
             round(row["total_fat_g"] or 0, 1),
             round(row["total_fiber_g"] or 0, 1),
             row["total_items"]),
        )
        conn.commit()
    finally:
        conn.close()


def get_calorie_summary(user_id, log_date):
    """Get daily calorie summary for a date."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM calorie_daily_summary WHERE user_id = ? AND summary_date = ?",
            (user_id, log_date),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_calorie_trends(user_id, days=30):
    """Get daily calorie summaries for the last N days."""
    conn = get_connection()
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT * FROM calorie_daily_summary
               WHERE user_id = ? AND summary_date >= ?
               ORDER BY summary_date""",
            (user_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_calorie_targets(user_id):
    """Get user's calorie/macro targets. Returns defaults if none set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM calorie_targets WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        from config.food_data import DEFAULT_TARGETS
        return DEFAULT_TARGETS["default"]
    finally:
        conn.close()


def set_calorie_targets(user_id, calorie_target, protein_target_g, carbs_target_g, fat_target_g):
    """Set or update user's calorie/macro targets."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO calorie_targets
               (user_id, calorie_target, protein_target_g, carbs_target_g, fat_target_g)
               VALUES (?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 calorie_target=excluded.calorie_target,
                 protein_target_g=excluded.protein_target_g,
                 carbs_target_g=excluded.carbs_target_g,
                 fat_target_g=excluded.fat_target_g,
                 updated_at=datetime('now')""",
            (user_id, calorie_target, protein_target_g, carbs_target_g, fat_target_g),
        )
        conn.commit()
    finally:
        conn.close()
