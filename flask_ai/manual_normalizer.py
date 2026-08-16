"""
manual_normalizer.py

Batch-normalize raw JSON exports into MrCarLift "normalized" format.

What it does:
1) Reads every *.json file from:        F:\manualinbox\raw
2) Normalizes with the agreed rules
3) Saves normalized JSON to:           F:\ai_inbox\normalized\<assignmentRequestID>.json
4) Moves the original raw JSON to:     F:\manualinbox\processed

Notes:
- Empty strings "" become null
- Lat/Lon strings like "25.2391° N" become floats (25.2391); S/W become negative
- Booking status rules:
    Yes / Yes_NeedBothways  -> include both legs if not empty
    Yes_NeedMorning         -> include morning only (even if evening has values)
    Yes_NeedEvening         -> include evening only (even if morning has values)
- Legs that are effectively empty are skipped
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================
# PATHS (as required)
# =========================
RAW_DIR = Path(r"F:\manualinbox\rawed")
PROCESSED_DIR = Path(r"F:\manualinbox\manualprocessed")
NORMALIZED_DIR = Path(r"F:\ai_inbox\normalized")


# =========================
# HELPERS
# =========================

def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)


def now_utc_z() -> str:
    # ISO8601 with Z
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def nullify_empty(v: Any) -> Any:
    if v == "":
        return None
    return v


def safe_get(d: Any, key: str, default=None) -> Any:
    if not isinstance(d, dict):
        return default
    return nullify_empty(d.get(key, default))


_num_re = re.compile(r"[-+]?\d*\.?\d+")


def parse_coord(v: Any) -> Optional[float]:
    """
    Accepts:
      - "25.2391° N" -> 25.2391
      - "55.3130° E" -> 55.313
      - "25.2391° S" -> -25.2391
      - "55.3130° W" -> -55.313
      - "24.861"     -> 24.861
      - 24.861       -> 24.861
    Returns None if empty/unparseable.
    """
    v = nullify_empty(v)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)

    if not isinstance(v, str):
        return None

    s = v.strip()
    if not s:
        return None

    m = _num_re.search(s)
    if not m:
        return None

    num = float(m.group(0))

    # Determine direction letter if present
    # Common formats: "25.2391° N", "25.2391 N"
    dir_match = re.search(r"\b([NSEW])\b", s.upper())
    if dir_match:
        direction = dir_match.group(1)
        if direction in ("S", "W"):
            num = -abs(num)
        else:
            num = abs(num)

    return num


def to_int(v: Any) -> Optional[int]:
    v = nullify_empty(v)
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        # only convert cleanly
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            # handles "6", "6.0"
            f = float(s)
            return int(f)
        except ValueError:
            return None
    return None


def to_number(v: Any) -> Optional[float]:
    v = nullify_empty(v)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def leg_is_empty(leg: Any) -> bool:
    """
    A leg is considered empty if all key fields are empty/null.
    """
    if not isinstance(leg, dict):
        return True

    keys = [
        "pickupName", "pickupLat", "pickupLon",
        "dropoffName", "dropoffLat", "dropoffLon",
        "pickupTime", "etaMin", "tripType"
    ]
    for k in keys:
        val = nullify_empty(leg.get(k))
        if val not in (None, ""):
            # some value exists
            if isinstance(val, str) and val.strip() == "":
                continue
            return False
    return True


def allowed_trip_sides(status: Optional[str]) -> List[str]:
    """
    Status mapping rules:
      - Yes / Yes_NeedBothways -> morning + evening
      - Yes_NeedMorning -> morning only
      - Yes_NeedEvening -> evening only
      - anything else -> none
    """
    status = nullify_empty(status)
    if status in ("Yes", "Yes_NeedBothways"):
        return ["morning", "evening"]
    if status == "Yes_NeedMorning":
        return ["morning"]
    if status == "Yes_NeedEvening":
        return ["evening"]
    return []


# =========================
# NORMALIZATION
# =========================

def normalize_one(raw: Dict[str, Any]) -> Dict[str, Any]:
    assignment_request_id = safe_get(raw, "assignmentRequestID")
    created_at_iso = safe_get(raw, "createdAtISO")  # used for bookings CreatedAt

    # ---- Drivers ----
    drivers_out: List[Dict[str, Any]] = []
    for d in (safe_get(raw, "drivers", []) or []):
        row = {
            "DriverID": safe_get(d, "id"),
            "DriverName": safe_get(d, "name"),
            "DriverPhone": safe_get(d, "phone"),
            "CarType": safe_get(d, "carType"),
            "NoOfSeats": to_int(safe_get(d, "seats")),
            "DriverStatus": safe_get(d, "status"),
            "DriverMonthlyMinimum": to_int(safe_get(d, "monthlyMinimum")),
            "DriverAssignedCounts": to_int(safe_get(d, "driverAssignedCount")) or 0,
            "DriverPayoutFrequency": safe_get(d, "payoutFrequency"),
            "DriverStartingLocation": safe_get(d, "startLocation"),
            "DriverStartingLocationLat": parse_coord(safe_get(d, "startLat")),
            "DriverStartingLocationLon": parse_coord(safe_get(d, "startLon")),
            "DriverNotes": safe_get(d, "notes"),
            "AssignmentRequestID": assignment_request_id
        }

        # Normalize empty notes explicitly
        row["DriverNotes"] = nullify_empty(row["DriverNotes"])
        drivers_out.append(row)

    # ---- DriverSchedules ----
    schedules_out: List[Dict[str, Any]] = []
    for s in (safe_get(raw, "schedules", []) or []):
        row = {
            "ScheduleID": safe_get(s, "id"),
            "DriverID": safe_get(s, "driverId"),
            "ActiveRideID": safe_get(s, "activeRideId"),
            "ScheduleStartTime": safe_get(s, "startTime"),
            "ScheduleEndTime": safe_get(s, "endTime"),
            "ScheduleStartLocationName": safe_get(s, "startName"),
            "ScheduleStartLat": parse_coord(safe_get(s, "startLat")),
            "ScheduleStartLon": parse_coord(safe_get(s, "startLon")),
            "ScheduleEndLocationName": safe_get(s, "endName"),
            "ScheduleEndLat": parse_coord(safe_get(s, "endLat")),
            "ScheduleEndLon": parse_coord(safe_get(s, "endLon")),
            "ScheduleETA": safe_get(s, "eta"),
            "ScheduleTripType": safe_get(s, "tripType"),
            "ScheduleSeatsOccupied": to_int(safe_get(s, "seatsOccupied")),
            "ScheduleStatus": safe_get(s, "status"),
            "ScheduleNotes": safe_get(s, "notes"),
            "AssignmentRequestID": assignment_request_id
        }

        row["ScheduleNotes"] = nullify_empty(row["ScheduleNotes"])
        schedules_out.append(row)

    # ---- Bookings (flatten legs based on status rules) ----
    bookings_out: List[Dict[str, Any]] = []
    for b in (safe_get(raw, "bookings", []) or []):
        booking_id = safe_get(b, "id")
        booking_status = safe_get(b, "status")

        passenger = safe_get(b, "passenger", {}) or {}
        legs = safe_get(b, "legs", {}) or {}

        sides = allowed_trip_sides(booking_status)
        for side in sides:
            leg = legs.get(side)
            if leg_is_empty(leg):
                continue  # skip empty leg blocks

            row = {
                "BookingID": booking_id,
                "CreatedAt": created_at_iso,
                "PassengerName": safe_get(passenger, "name"),
                "PassengerPhone": safe_get(passenger, "phone"),
                "NoOfPassengers": to_int(safe_get(passenger, "noOfPassengers")),
                "DaysPerWeek": safe_get(passenger, "daysPerWeek"),
                "PassengerMonthlyFare": to_int(safe_get(passenger, "monthlyFare")),
                "PassengerNotes": safe_get(passenger, "notes"),
                "PassengerBookingActiveStatus": booking_status,
                "TripSide": side,
                "PickupLocation": safe_get(leg, "pickupName"),
                "PickupLat": parse_coord(safe_get(leg, "pickupLat")),
                "PickupLon": parse_coord(safe_get(leg, "pickupLon")),
                "DropoffLocation": safe_get(leg, "dropoffName"),
                "DropoffLat": parse_coord(safe_get(leg, "dropoffLat")),
                "DropoffLon": parse_coord(safe_get(leg, "dropoffLon")),
                "PickupTime": safe_get(leg, "pickupTime"),
                "ETA": safe_get(leg, "etaMin"),
                "TripType": safe_get(leg, "tripType"),
                "AssignmentRequestID": assignment_request_id
            }

            row["PassengerNotes"] = nullify_empty(row["PassengerNotes"])
            bookings_out.append(row)

    normalized = {
        "assignmentRequestID": assignment_request_id,
        "savedAt": now_utc_z(),
        "Drivers": drivers_out,
        "DriverSchedules": schedules_out,
        "Bookings": bookings_out,
        "counts": {
            "Drivers": len(drivers_out),
            "DriverSchedules": len(schedules_out),
            "Bookings": len(bookings_out)
        }
    }

    return normalized


# =========================
# FILE PROCESSING
# =========================

def unique_processed_path(dest_dir: Path, original_name: str) -> Path:
    """
    Avoid overwriting a processed file if the same filename already exists.
    """
    candidate = dest_dir / original_name
    if not candidate.exists():
        return candidate

    stem = Path(original_name).stem
    suffix = Path(original_name).suffix
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dest_dir / f"{stem}__{ts}{suffix}"


def process_all() -> None:
    ensure_dirs()

    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        print(f"[INFO] No JSON files found in: {RAW_DIR}")
        return

    print(f"[INFO] Found {len(files)} JSON file(s) in: {RAW_DIR}")

    for raw_file in files:
        print(f"\n[PROCESSING] {raw_file.name}")
        try:
            with raw_file.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, dict):
                raise ValueError("Root JSON must be an object.")

            assignment_request_id = raw_data.get("assignmentRequestID")
            if not assignment_request_id:
                raise ValueError("assignmentRequestID is required in raw JSON.")

            normalized = normalize_one(raw_data)

            # Save normalized as <assignmentRequestID>.json
            out_path = NORMALIZED_DIR / f"{assignment_request_id}.json"
            tmp_path = out_path.with_suffix(".json.tmp")

            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(normalized, f, ensure_ascii=False, indent=2)

            # Atomic-ish replace
            tmp_path.replace(out_path)

            # Move raw to processed (after normalized save succeeded)
            dest_processed = unique_processed_path(PROCESSED_DIR, raw_file.name)
            shutil.move(str(raw_file), str(dest_processed))

            print(f"[OK] Normalized saved: {out_path}")
            print(f"[OK] Raw moved to:     {dest_processed}")
            print(f"[COUNTS] Drivers={normalized['counts']['Drivers']}, "
                  f"Schedules={normalized['counts']['DriverSchedules']}, "
                  f"Bookings={normalized['counts']['Bookings']}")

        except Exception as e:
            # Leave the raw file in place so it can be fixed and re-run.
            print(f"[ERROR] Failed to process {raw_file.name}: {e}")


if __name__ == "__main__":
    process_all()
