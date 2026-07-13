from datetime import date

import services.garmin_service as garmin
import services.wearable_wheel_service as wearable


class _GarminClient:
    def get_heart_rates(self, day):
        return {"restingHeartRate": 57}


def test_garmin_resting_hr_uses_wearable_store(db_conn, monkeypatch):
    monkeypatch.setattr(wearable, "get_connection", db_conn)
    conn = db_conn()
    user_id = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("garmin.user", "hash"),
    ).lastrowid
    conn.commit()
    conn.close()

    assert garmin.import_heart_rate(user_id, _GarminClient(), days=1) == 1

    conn = db_conn()
    row = conn.execute(
        "SELECT metric_code, value, source FROM wearable_measurements WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    assert dict(row) == {
        "metric_code": "resting_heart_rate_bpm",
        "value": 57.0,
        "source": "garmin",
    }
