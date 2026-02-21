from datetime import date, timedelta
from models.checkin import save_checkin, get_checkin, get_checkins_for_range


def save_daily_checkin(user_id: int, checkin_date: str, data: dict):
    save_checkin(user_id, checkin_date, data)


def get_daily_checkin(user_id: int, checkin_date: str) -> dict | None:
    return get_checkin(user_id, checkin_date)


def get_week_checkins(user_id: int, week_start: date) -> dict:
    """Get check-ins for a week as {date_str: checkin_dict}."""
    week_end = week_start + timedelta(days=6)
    checkins = get_checkins_for_range(user_id, week_start.isoformat(), week_end.isoformat())
    return {c["checkin_date"]: c for c in checkins}


def get_week_averages(user_id: int, week_start: date) -> dict:
    """Calculate average mood, energy, and pillar ratings for a week."""
    checkins = list(get_week_checkins(user_id, week_start).values())
    if not checkins:
        return {}

    fields = ["mood", "energy", "nutrition_rating", "activity_rating",
              "sleep_rating", "stress_rating", "connection_rating", "substance_rating"]
    averages = {}
    for field in fields:
        values = [c[field] for c in checkins if c.get(field) is not None]
        averages[field] = round(sum(values) / len(values), 1) if values else None
    averages["days_checked_in"] = len(checkins)
    return averages


def get_month_checkins(user_id: int, year: int, month: int) -> dict:
    """Get check-ins for a month as {date_str: checkin_dict}."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    checkins = get_checkins_for_range(user_id, start.isoformat(), end.isoformat())
    return {c["checkin_date"]: c for c in checkins}
