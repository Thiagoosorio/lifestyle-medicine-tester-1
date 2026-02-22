"""Service for meal logging, plant score calculation, and nutrition tracking."""

from db.database import get_connection
from datetime import date, timedelta


def log_meal(user_id, log_date, meal_type, description, color_category="yellow",
             plant_servings=0, fruit_servings=0, vegetable_servings=0,
             whole_grain_servings=0, legume_servings=0, nut_seed_servings=0,
             fiber_grams=0, water_glasses=0, notes=None):
    """Log a single meal entry."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO meal_logs
           (user_id, log_date, meal_type, description, color_category,
            plant_servings, fruit_servings, vegetable_servings,
            whole_grain_servings, legume_servings, nut_seed_servings,
            fiber_grams, water_glasses, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, log_date, meal_type, description, color_category,
         plant_servings, fruit_servings, vegetable_servings,
         whole_grain_servings, legume_servings, nut_seed_servings,
         fiber_grams, water_glasses, notes),
    )
    conn.commit()
    conn.close()

    # Update daily summary
    compute_daily_summary(user_id, log_date)


def get_meals_for_date(user_id, log_date):
    """Get all meals logged for a specific date."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meal_logs WHERE user_id = ? AND log_date = ? ORDER BY created_at",
        (user_id, log_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_meal(meal_id, user_id):
    """Delete a meal entry and recompute daily summary."""
    conn = get_connection()
    row = conn.execute(
        "SELECT log_date FROM meal_logs WHERE id = ? AND user_id = ?",
        (meal_id, user_id),
    ).fetchone()
    if row:
        log_date = row["log_date"]
        conn.execute("DELETE FROM meal_logs WHERE id = ? AND user_id = ?", (meal_id, user_id))
        conn.commit()
        conn.close()
        compute_daily_summary(user_id, log_date)
    else:
        conn.close()


def compute_daily_summary(user_id, log_date):
    """Compute and upsert the daily nutrition summary."""
    conn = get_connection()
    meals = conn.execute(
        "SELECT * FROM meal_logs WHERE user_id = ? AND log_date = ?",
        (user_id, log_date),
    ).fetchall()

    if not meals:
        conn.execute(
            "DELETE FROM nutrition_daily_summary WHERE user_id = ? AND summary_date = ?",
            (user_id, log_date),
        )
        conn.commit()
        conn.close()
        return

    total_meals = len(meals)
    green_count = sum(1 for m in meals if m["color_category"] == "green")
    yellow_count = sum(1 for m in meals if m["color_category"] == "yellow")
    red_count = sum(1 for m in meals if m["color_category"] == "red")
    total_plant = sum(m["plant_servings"] or 0 for m in meals)
    total_fiber = sum(m["fiber_grams"] or 0 for m in meals)
    total_water = sum(m["water_glasses"] or 0 for m in meals)

    plant_score = calculate_plant_score(
        plant_servings=total_plant,
        fruit_veg=sum((m["fruit_servings"] or 0) + (m["vegetable_servings"] or 0) for m in meals),
        fiber_grams=total_fiber,
        green_count=green_count,
        yellow_count=yellow_count,
        red_count=red_count,
    )

    # Overall nutrition score combines plant score with color balance
    total_colored = green_count + yellow_count + red_count
    color_ratio = green_count / total_colored if total_colored > 0 else 0
    nutrition_score = round(plant_score * 0.7 + color_ratio * 100 * 0.3)

    conn.execute(
        """INSERT INTO nutrition_daily_summary
           (user_id, summary_date, total_meals, green_count, yellow_count, red_count,
            total_plant_servings, total_fiber_grams, total_water_glasses,
            plant_score, nutrition_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id, summary_date) DO UPDATE SET
             total_meals=excluded.total_meals, green_count=excluded.green_count,
             yellow_count=excluded.yellow_count, red_count=excluded.red_count,
             total_plant_servings=excluded.total_plant_servings,
             total_fiber_grams=excluded.total_fiber_grams,
             total_water_glasses=excluded.total_water_glasses,
             plant_score=excluded.plant_score, nutrition_score=excluded.nutrition_score""",
        (user_id, log_date, total_meals, green_count, yellow_count, red_count,
         total_plant, total_fiber, total_water, plant_score, nutrition_score),
    )
    conn.commit()
    conn.close()


def calculate_plant_score(plant_servings, fruit_veg, fiber_grams,
                          green_count=0, yellow_count=0, red_count=0):
    """Calculate plant score (0-100) based on ACLM guidelines + Wang DD (PMID: 33641343)."""
    # Component 1: Total plant servings (target: 10+/day) — 40 pts
    plant_pts = min(40, (plant_servings / 10) * 40)

    # Component 2: Fruit + vegetable servings (target: 5+/day) — 30 pts
    fv_pts = min(30, (fruit_veg / 5) * 30)

    # Component 3: Fiber (target: 30g+/day) — 20 pts
    fiber_pts = min(20, (fiber_grams / 30) * 20)

    # Component 4: Color balance (green:total ratio) — 10 pts
    total_colored = green_count + yellow_count + red_count
    if total_colored > 0:
        color_pts = (green_count / total_colored) * 10
    else:
        color_pts = 0

    return round(min(100, plant_pts + fv_pts + fiber_pts + color_pts))


def get_daily_summary(user_id, log_date):
    """Get the daily nutrition summary for a specific date."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM nutrition_daily_summary WHERE user_id = ? AND summary_date = ?",
        (user_id, log_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_nutrition_trends(user_id, days=30):
    """Get daily nutrition summaries for the last N days."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT * FROM nutrition_daily_summary
           WHERE user_id = ? AND summary_date >= ?
           ORDER BY summary_date""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_nutrition_averages(user_id, days=30):
    """Get average nutrition metrics."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT
             AVG(total_plant_servings) as avg_plants,
             AVG(total_fiber_grams) as avg_fiber,
             AVG(total_water_glasses) as avg_water,
             AVG(plant_score) as avg_plant_score,
             AVG(nutrition_score) as avg_nutrition_score,
             AVG(green_count) as avg_green,
             AVG(yellow_count) as avg_yellow,
             AVG(red_count) as avg_red,
             COUNT(*) as log_count
           FROM nutrition_daily_summary
           WHERE user_id = ? AND summary_date >= ?""",
        (user_id, cutoff),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
