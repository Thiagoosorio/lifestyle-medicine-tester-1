"""Strava API integration — OAuth 2.0 authentication and activity import.

Strava API docs: https://developers.strava.com/docs/
OAuth 2.0 flow using authorization code grant.

Requires environment variables or st.secrets:
  STRAVA_CLIENT_ID
  STRAVA_CLIENT_SECRET
"""

import os
import time
from datetime import date, timedelta
from db.database import get_connection
from config.exercise_data import (
    STRAVA_TYPE_MAP,
    STRAVA_DEFAULT_TYPE,
    EXERCISE_TYPES,
)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


# ---------------------------------------------------------------------------
#  Config helpers
# ---------------------------------------------------------------------------

def _get_client_id():
    """Get Strava Client ID from environment or Streamlit secrets."""
    val = os.environ.get("STRAVA_CLIENT_ID")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get("STRAVA_CLIENT_ID")
    except Exception:
        return None


def _get_client_secret():
    """Get Strava Client Secret from environment or Streamlit secrets."""
    val = os.environ.get("STRAVA_CLIENT_SECRET")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get("STRAVA_CLIENT_SECRET")
    except Exception:
        return None


def is_strava_configured():
    """Check if Strava client credentials are available."""
    return bool(_get_client_id() and _get_client_secret())


# ---------------------------------------------------------------------------
#  OAuth 2.0
# ---------------------------------------------------------------------------

def get_strava_auth_url(redirect_uri):
    """Generate the Strava OAuth authorization URL."""
    client_id = _get_client_id()
    if not client_id:
        return None
    return (
        f"{STRAVA_AUTH_URL}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=read,activity:read_all&"
        f"approval_prompt=auto"
    )


def exchange_strava_code(user_id, code):
    """Exchange authorization code for access/refresh tokens."""
    import requests

    client_id = _get_client_id()
    client_secret = _get_client_secret()
    if not client_id or not client_secret:
        raise ValueError("Strava client credentials not configured")

    resp = requests.post(STRAVA_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    athlete_id = data.get("athlete", {}).get("id")
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at = data["expires_at"]

    _save_connection(user_id, athlete_id, access_token, refresh_token, expires_at)
    return data


def refresh_strava_token(user_id):
    """Refresh an expired Strava access token."""
    import requests

    conn_info = get_strava_connection(user_id)
    if not conn_info or not conn_info.get("refresh_token"):
        return None

    client_id = _get_client_id()
    client_secret = _get_client_secret()
    if not client_id or not client_secret:
        return None

    resp = requests.post(STRAVA_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": conn_info["refresh_token"],
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    _save_connection(
        user_id,
        conn_info.get("strava_athlete_id"),
        data["access_token"],
        data["refresh_token"],
        data["expires_at"],
    )
    return data["access_token"]


def _get_valid_token(user_id):
    """Get a valid access token, refreshing if expired."""
    conn_info = get_strava_connection(user_id)
    if not conn_info:
        return None

    if conn_info.get("token_expires_at") and conn_info["token_expires_at"] < time.time():
        return refresh_strava_token(user_id)

    return conn_info.get("access_token")


# ---------------------------------------------------------------------------
#  Connection management
# ---------------------------------------------------------------------------

def _save_connection(user_id, athlete_id, access_token, refresh_token, expires_at):
    """Save Strava connection to database."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO strava_connections
               (user_id, strava_athlete_id, access_token, refresh_token, token_expires_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 strava_athlete_id = excluded.strava_athlete_id,
                 access_token = excluded.access_token,
                 refresh_token = excluded.refresh_token,
                 token_expires_at = excluded.token_expires_at""",
            (user_id, athlete_id, access_token, refresh_token, expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_strava_connection(user_id):
    """Get stored Strava connection info."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM strava_connections WHERE user_id = ?", (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def disconnect_strava(user_id):
    """Remove Strava connection."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM strava_connections WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def update_last_sync(user_id):
    """Update the last sync timestamp."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE strava_connections SET last_sync = datetime('now') WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  Activity Import
# ---------------------------------------------------------------------------

def import_strava_activities(user_id, days=30):
    """Fetch recent activities from Strava and import as exercise logs.

    Returns number of activities imported.
    """
    import requests
    from services.exercise_service import log_exercise

    token = _get_valid_token(user_id)
    if not token:
        raise ValueError("No valid Strava token. Please reconnect.")

    after_ts = int((date.today() - timedelta(days=days)).strftime("%s"))

    headers = {"Authorization": f"Bearer {token}"}
    imported = 0
    page = 1

    while True:
        resp = requests.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers=headers,
            params={"after": after_ts, "per_page": 50, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        activities = resp.json()

        if not activities:
            break

        for act in activities:
            mapped = _map_strava_activity(act)
            if mapped:
                log_exercise(
                    user_id=user_id,
                    exercise_date=mapped["exercise_date"],
                    exercise_type=mapped["exercise_type"],
                    duration_min=mapped["duration_min"],
                    intensity=mapped["intensity"],
                    distance_km=mapped.get("distance_km"),
                    calories=mapped.get("calories"),
                    avg_hr=mapped.get("avg_hr"),
                    max_hr=mapped.get("max_hr"),
                    notes=mapped.get("notes"),
                    source="strava",
                    external_id=str(act["id"]),
                )
                imported += 1

        if len(activities) < 50:
            break
        page += 1

    update_last_sync(user_id)
    return imported


def _map_strava_activity(activity):
    """Convert a Strava activity dict to our exercise log format."""
    strava_type = activity.get("type", "Workout")
    exercise_type = STRAVA_TYPE_MAP.get(strava_type, STRAVA_DEFAULT_TYPE)

    # Duration
    moving_time = activity.get("moving_time", 0)
    duration_min = max(1, round(moving_time / 60))

    # Date (from start_date_local)
    start_date = activity.get("start_date_local", "")
    exercise_date = start_date[:10] if len(start_date) >= 10 else date.today().isoformat()

    # Distance (meters → km)
    distance_m = activity.get("distance", 0)
    distance_km = round(distance_m / 1000, 2) if distance_m else None

    # Heart rate → intensity classification
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    intensity = _classify_intensity(avg_hr, max_hr, strava_type)

    # Calories (Strava provides kilojoules for rides, calories for others)
    calories = None
    if activity.get("calories"):
        calories = round(activity["calories"])
    elif activity.get("kilojoules"):
        calories = round(activity["kilojoules"] * 0.239)  # kJ to kcal

    # Build notes from Strava name
    notes = activity.get("name", "")

    return {
        "exercise_date": exercise_date,
        "exercise_type": exercise_type,
        "duration_min": duration_min,
        "intensity": intensity,
        "distance_km": distance_km,
        "calories": calories,
        "avg_hr": round(avg_hr) if avg_hr else None,
        "max_hr": round(max_hr) if max_hr else None,
        "notes": f"Strava: {notes}" if notes else "Imported from Strava",
    }


def _classify_intensity(avg_hr, max_hr, strava_type):
    """Classify exercise intensity from heart rate data or activity type.

    Uses HR zones if available, otherwise infers from activity type.
    Zone thresholds: light < 64% max HR, moderate 64-76%, vigorous > 76%
    """
    if avg_hr and max_hr and max_hr > 0:
        hr_pct = avg_hr / max_hr * 100
        if hr_pct >= 77:
            return "vigorous"
        elif hr_pct >= 64:
            return "moderate"
        else:
            return "light"

    # Fallback: classify by activity type
    vigorous_types = {"Run", "Trail Run", "HIIT", "Crossfit", "Swim", "Rowing"}
    light_types = {"Walk", "Yoga", "Pilates", "Golf"}

    if strava_type in vigorous_types:
        return "vigorous"
    elif strava_type in light_types:
        return "light"
    return "moderate"
