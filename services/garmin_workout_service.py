"""Garmin Connect workout export + TCX file generation for cycling workouts.

Converts structured workouts from the cycling training module into:
  1. Garmin Connect workout JSON — pushed directly via garminconnect library
  2. TCX (Training Center XML) — downloadable file compatible with TrainingPeaks,
     Garmin Connect manual import, and most training applications.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
import streamlit as st
from config.cycling_data import WORKOUT_LIBRARY_BY_ID

TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
TCX_XSI = "http://www.w3.org/2001/XMLSchema-instance"
TCX_SCHEMA_LOC = (
    "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 "
    "http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"
)

# Garmin sport type for cycling
_CYCLING_SPORT = {"sportTypeId": 2, "sportTypeKey": "cycling", "displayOrder": 2}

# Garmin step type IDs
_STEP_WARMUP   = {"stepTypeId": 1, "stepTypeKey": "warmup",    "displayOrder": 1}
_STEP_COOLDOWN = {"stepTypeId": 2, "stepTypeKey": "cooldown",  "displayOrder": 2}
_STEP_INTERVAL = {"stepTypeId": 3, "stepTypeKey": "interval",  "displayOrder": 3}
_STEP_RECOVERY = {"stepTypeId": 4, "stepTypeKey": "recovery",  "displayOrder": 4}

# Garmin end condition: time-based
_END_COND_TIME = {
    "conditionTypeId": 2,
    "conditionTypeKey": "time",
    "displayOrder": 2,
    "displayable": True,
}

# Garmin target type: power zone
_TARGET_POWER = {
    "workoutTargetTypeId": 2,
    "workoutTargetTypeKey": "power.zone",
    "displayOrder": 2,
}


# ── Internal helpers ────────────────────────────────────────────────────────

def _map_step_type(label: str, zone: str, idx: int, total: int) -> dict:
    """Return the Garmin stepType dict for a workout interval."""
    if idx == 0:
        return _STEP_WARMUP
    if idx == total - 1:
        return _STEP_COOLDOWN
    lbl = label.lower()
    if any(kw in lbl for kw in ("recovery", "rest", "easy", "spin")):
        return _STEP_RECOVERY
    return _STEP_INTERVAL


def _map_intensity_tcx(label: str, idx: int, total: int) -> str:
    """Return the TCX Intensity string for a workout interval."""
    if idx == 0:
        return "Warmup"
    if idx == total - 1:
        return "Cooldown"
    lbl = label.lower()
    if any(kw in lbl for kw in ("recovery", "rest", "easy")):
        return "Resting"
    return "Active"


def _power_band(ftp_watts: int, power_pct: float) -> tuple[int, int]:
    """Return (low_watts, high_watts) as a ±3 % band around the target power."""
    target = ftp_watts * power_pct
    return round(target * 0.97), round(target * 1.03)


# ── Garmin JSON conversion ──────────────────────────────────────────────────

def workout_to_garmin_json(workout: dict, ftp_watts: int) -> dict:
    """Convert a WORKOUT_LIBRARY entry into Garmin Connect workout JSON."""
    intervals = workout.get("intervals", [])
    total = len(intervals)
    steps = []

    for i, interval in enumerate(intervals):
        low_w, high_w = _power_band(ftp_watts, interval["power_pct"])
        step = {
            "type": "ExecutableStepDTO",
            "stepOrder": i + 1,
            "stepType": _map_step_type(interval["label"], interval.get("zone", ""), i, total),
            "endCondition": dict(_END_COND_TIME, endConditionValue=interval["duration_sec"]),
            "targetType": _TARGET_POWER,
            "targetValueOne": low_w,
            "targetValueTwo": high_w,
        }
        steps.append(step)

    return {
        "workoutName": workout["name"],
        "description": f"{workout.get('description', '')[:100]} | ~{workout.get('tss_estimate', 0)} TSS",
        "sportType": _CYCLING_SPORT,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": _CYCLING_SPORT,
                "workoutSteps": steps,
            }
        ],
    }


# ── Garmin Connect push ─────────────────────────────────────────────────────

def push_workout_to_garmin(
    user_id: int,
    workout: dict,
    ftp_watts: int,
    schedule_date: str | None = None,
) -> dict:
    """Upload a structured workout to Garmin Connect and optionally schedule it.

    Returns: {success: bool, workout_id: str | None, message: str}
    """
    client = st.session_state.get("garmin_client")
    if not client:
        return {
            "success": False,
            "workout_id": None,
            "message": "Not connected to Garmin. Re-login on the Garmin Import page.",
        }

    garmin_json = workout_to_garmin_json(workout, ftp_watts)

    try:
        response = client.upload_workout(garmin_json)
        workout_id = str(response.get("workoutId", ""))

        # Optionally schedule the workout on the Garmin Connect calendar
        if schedule_date and workout_id:
            try:
                client.connectapi(
                    f"/workout-service/schedule/{workout_id}",
                    method="POST",
                    json={"date": schedule_date},
                )
            except Exception:
                pass  # Scheduling is best-effort; upload already succeeded

        return {
            "success": True,
            "workout_id": workout_id,
            "message": f"Uploaded: {workout['name']}",
        }

    except Exception as exc:
        return {
            "success": False,
            "workout_id": None,
            "message": str(exc),
        }


def push_week_to_garmin(
    user_id: int,
    week_workouts: list[dict],
    ftp_watts: int,
) -> dict:
    """Upload all scheduled/rescheduled workouts for the current week to Garmin.

    Returns: {pushed: int, failed: int, details: list[dict]}
    """
    pushed, failed = 0, 0
    details: list[dict] = []
    skip_statuses = {"completed", "skipped"}

    for pw in week_workouts:
        if pw.get("status") in skip_statuses:
            continue
        workout = WORKOUT_LIBRARY_BY_ID.get(pw.get("workout_id", ""))
        if not workout:
            continue

        result = push_workout_to_garmin(
            user_id, workout, ftp_watts, schedule_date=pw.get("date")
        )
        result["plan_workout_id"] = pw.get("plan_workout_id", "")
        result["workout_name"] = workout["name"]
        details.append(result)

        if result["success"]:
            pushed += 1
        else:
            failed += 1

    return {"pushed": pushed, "failed": failed, "details": details}


# ── TCX generation ─────────────────────────────────────────────────────────

def _build_tcx_root() -> ET.Element:
    """Create and return the TCX root element with correct namespace declarations."""
    ET.register_namespace("", TCX_NS)
    ET.register_namespace("xsi", TCX_XSI)
    root = ET.Element(f"{{{TCX_NS}}}TrainingCenterDatabase")
    root.set(f"{{{TCX_XSI}}}schemaLocation", TCX_SCHEMA_LOC)
    return root


def _add_workout_to_tcx(
    workouts_el: ET.Element,
    workout: dict,
    ftp_watts: int,
    name_override: str | None = None,
) -> None:
    """Append a single <Workout> element to a <Workouts> parent element."""
    intervals = workout.get("intervals", [])
    total = len(intervals)

    workout_el = ET.SubElement(workouts_el, f"{{{TCX_NS}}}Workout")
    workout_el.set("Sport", "Biking")
    ET.SubElement(workout_el, f"{{{TCX_NS}}}Name").text = name_override or workout["name"]

    for i, interval in enumerate(intervals):
        low_w, high_w = _power_band(ftp_watts, interval["power_pct"])

        step_el = ET.SubElement(workout_el, f"{{{TCX_NS}}}Step")
        step_el.set(f"{{{TCX_XSI}}}type", "Step_t")
        ET.SubElement(step_el, f"{{{TCX_NS}}}StepId").text = str(i + 1)
        ET.SubElement(step_el, f"{{{TCX_NS}}}Name").text = interval["label"]

        dur_el = ET.SubElement(step_el, f"{{{TCX_NS}}}Duration")
        dur_el.set(f"{{{TCX_XSI}}}type", "Time_t")
        ET.SubElement(dur_el, f"{{{TCX_NS}}}Seconds").text = str(interval["duration_sec"])

        ET.SubElement(step_el, f"{{{TCX_NS}}}Intensity").text = _map_intensity_tcx(
            interval["label"], i, total
        )

        target_el = ET.SubElement(step_el, f"{{{TCX_NS}}}Target")
        target_el.set(f"{{{TCX_XSI}}}type", "Power_t")
        pzone_el = ET.SubElement(target_el, f"{{{TCX_NS}}}PowerZone")
        pzone_el.set(f"{{{TCX_XSI}}}type", "CustomPowerZone_t")

        low_el = ET.SubElement(pzone_el, f"{{{TCX_NS}}}Low")
        ET.SubElement(low_el, f"{{{TCX_NS}}}Watts").text = str(low_w)
        high_el = ET.SubElement(pzone_el, f"{{{TCX_NS}}}High")
        ET.SubElement(high_el, f"{{{TCX_NS}}}Watts").text = str(high_w)


def generate_tcx_workout(workout: dict, ftp_watts: int) -> str:
    """Generate a TCX XML string for a single structured workout.

    Returns a unicode string (no BOM). Use for preview / single download.
    """
    root = _build_tcx_root()
    workouts_el = ET.SubElement(root, f"{{{TCX_NS}}}Workouts")
    _add_workout_to_tcx(workouts_el, workout, ftp_watts)
    return ET.tostring(root, encoding="unicode")


def generate_tcx_plan(
    week_workouts: list[dict],
    ftp_watts: int,
    plan_meta: dict | None = None,
) -> bytes:
    """Generate a TCX file containing all non-completed workouts in a week.

    Returns bytes suitable for st.download_button.
    plan_meta: optional dict with keys 'phase' and 'week' for naming.
    """
    root = _build_tcx_root()
    workouts_el = ET.SubElement(root, f"{{{TCX_NS}}}Workouts")
    skip_statuses = {"completed", "skipped"}

    for pw in week_workouts:
        if pw.get("status") in skip_statuses:
            continue
        workout = WORKOUT_LIBRARY_BY_ID.get(pw.get("workout_id", ""))
        if not workout:
            continue
        workout_date = pw.get("date", "")
        name_override = f"{workout['name']} ({workout_date})"
        _add_workout_to_tcx(workouts_el, workout, ftp_watts, name_override=name_override)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
