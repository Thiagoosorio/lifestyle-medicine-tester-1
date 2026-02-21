import json
import csv
import io
from db.database import get_connection


def export_checkins_csv(user_id: int, start_date: str = None, end_date: str = None) -> str:
    conn = get_connection()
    try:
        query = "SELECT * FROM daily_checkins WHERE user_id = ?"
        params = [user_id]
        if start_date:
            query += " AND checkin_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND checkin_date <= ?"
            params.append(end_date)
        query += " ORDER BY checkin_date"
        rows = conn.execute(query, params).fetchall()

        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))
        return output.getvalue()
    finally:
        conn.close()


def export_goals_csv(user_id: int) -> str:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM goals WHERE user_id = ? ORDER BY created_at", (user_id,)).fetchall()
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))
        return output.getvalue()
    finally:
        conn.close()


def export_assessments_csv(user_id: int) -> str:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM wheel_assessments WHERE user_id = ? ORDER BY assessed_at",
            (user_id,),
        ).fetchall()
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))
        return output.getvalue()
    finally:
        conn.close()


def export_all_json(user_id: int) -> str:
    conn = get_connection()
    try:
        data = {}
        for table in ["daily_checkins", "wheel_assessments", "goals", "goal_progress",
                       "habits", "habit_log", "weekly_reviews", "stage_of_change"]:
            rows = conn.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,)).fetchall()
            data[table] = [dict(r) for r in rows]
        return json.dumps(data, indent=2)
    finally:
        conn.close()
