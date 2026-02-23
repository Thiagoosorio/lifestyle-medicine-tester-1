"""Garmin Connect integration — import sleep, activity, body composition, heart rate."""

from datetime import date, timedelta
from db.database import get_connection


# ---------------------------------------------------------------------------
#  Credential management
# ---------------------------------------------------------------------------

def save_garmin_credentials(user_id, garmin_email):
    """Save Garmin email (credentials are used per-session, not stored)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO garmin_connections (user_id, garmin_email)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               garmin_email = excluded.garmin_email""",
            (user_id, garmin_email),
        )
        conn.commit()
    finally:
        conn.close()


def get_garmin_connection(user_id):
    """Get stored Garmin connection info."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM garmin_connections WHERE user_id = ?", (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_last_sync(user_id):
    """Update the last sync timestamp."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE garmin_connections SET last_sync = datetime('now') WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  Garmin Connect client
# ---------------------------------------------------------------------------

def connect(email, password):
    """Authenticate with Garmin Connect and return the client instance."""
    from garminconnect import Garmin
    client = Garmin(email, password)
    client.login()
    return client


# ---------------------------------------------------------------------------
#  Data import functions
# ---------------------------------------------------------------------------

def import_sleep_data(user_id, client, days=7):
    """Import sleep summaries from Garmin and insert into sleep_logs."""
    imported = 0
    conn = get_connection()
    try:
        for i in range(days):
            d = date.today() - timedelta(days=i)
            try:
                sleep = client.get_sleep_data(d.isoformat())
                if not sleep or not sleep.get("dailySleepDTO"):
                    continue

                dto = sleep["dailySleepDTO"]
                sleep_start = dto.get("sleepStartTimestampLocal", "")
                sleep_end = dto.get("sleepEndTimestampLocal", "")

                # Extract times from timestamps
                bedtime = sleep_start[11:16] if len(sleep_start) > 16 else None
                wake_time = sleep_end[11:16] if len(sleep_end) > 16 else None
                total_min = round(dto.get("sleepTimeSeconds", 0) / 60)
                awakenings = dto.get("awakeSleepSeconds", 0)
                wake_dur_min = round(awakenings / 60) if awakenings else 0

                if not bedtime or not wake_time or total_min <= 0:
                    continue

                # Simple sleep score mapping from Garmin's quality
                garmin_score = dto.get("overallSleepScore", {})
                quality_score = garmin_score.get("value") if isinstance(garmin_score, dict) else None

                conn.execute(
                    """INSERT OR IGNORE INTO sleep_logs
                       (user_id, sleep_date, bedtime, wake_time, total_sleep_min,
                        sleep_efficiency, sleep_score, awakenings, wake_duration_min,
                        sleep_quality, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, d.isoformat(), bedtime, wake_time, total_min,
                        round(total_min / ((total_min + wake_dur_min) or 1) * 100),
                        quality_score or 0,
                        len(sleep.get("sleepMovement", [])),
                        wake_dur_min,
                        3,  # default quality
                        "Imported from Garmin Connect",
                    ),
                )
                imported += 1
            except Exception:
                continue
        conn.commit()
    finally:
        conn.close()
    return imported


def import_activity_data(user_id, client, days=7):
    """Import daily step counts and active minutes from Garmin."""
    imported = 0
    conn = get_connection()
    try:
        for i in range(days):
            d = date.today() - timedelta(days=i)
            try:
                stats = client.get_stats(d.isoformat())
                if not stats:
                    continue

                steps = stats.get("totalSteps", 0)
                active_min = stats.get("activeSeconds", 0)
                active_min = round(active_min / 60) if active_min else 0
                calories = stats.get("totalKilocalories", 0)

                # Map to an activity rating (1-10 scale)
                if steps >= 12000:
                    rating = 10
                elif steps >= 10000:
                    rating = 8
                elif steps >= 7000:
                    rating = 7
                elif steps >= 5000:
                    rating = 5
                elif steps >= 3000:
                    rating = 4
                else:
                    rating = 2

                # Update daily checkin activity_rating if checkin exists
                existing = conn.execute(
                    "SELECT id FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
                    (user_id, d.isoformat()),
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE daily_checkins SET activity_rating = ? WHERE id = ?",
                        (rating, existing["id"]),
                    )
                    imported += 1
            except Exception:
                continue
        conn.commit()
    finally:
        conn.close()
    return imported


def import_body_composition(user_id, client, days=30):
    """Import weight and body fat data from Garmin."""
    imported = 0
    conn = get_connection()
    try:
        end = date.today()
        start = end - timedelta(days=days)

        try:
            data = client.get_body_composition(start.isoformat(), end.isoformat())
            if data and data.get("dateWeightList"):
                for entry in data["dateWeightList"]:
                    ts = entry.get("calendarDate")
                    weight_g = entry.get("weight")
                    if not ts or not weight_g:
                        continue

                    weight_kg = round(weight_g / 1000, 1)
                    bmi = entry.get("bmi")
                    body_fat = entry.get("bodyFat")

                    conn.execute(
                        """INSERT OR IGNORE INTO body_metrics
                           (user_id, log_date, weight_kg, body_fat_pct, notes)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            user_id, ts, weight_kg,
                            round(body_fat, 1) if body_fat else None,
                            "Imported from Garmin Connect",
                        ),
                    )
                    imported += 1
        except Exception:
            pass

        conn.commit()
    finally:
        conn.close()
    return imported


def import_heart_rate(user_id, client, days=7):
    """Import resting heart rate data as biomarker entries."""
    imported = 0
    conn = get_connection()
    try:
        # Get resting HR biomarker ID
        hr_bio = conn.execute(
            "SELECT id FROM biomarkers WHERE LOWER(name) LIKE '%resting heart rate%' OR code = 'rhr'",
        ).fetchone()

        if not hr_bio:
            return 0

        bio_id = hr_bio["id"]

        for i in range(days):
            d = date.today() - timedelta(days=i)
            try:
                hr_data = client.get_heart_rates(d.isoformat())
                if not hr_data:
                    continue

                rhr = hr_data.get("restingHeartRate")
                if not rhr:
                    continue

                conn.execute(
                    """INSERT OR IGNORE INTO biomarker_results
                       (user_id, biomarker_id, value, lab_date, lab_name, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, bio_id, rhr, d.isoformat(),
                     "Garmin Connect", "Auto-imported from Garmin"),
                )
                imported += 1
            except Exception:
                continue
        conn.commit()
    finally:
        conn.close()
    return imported
