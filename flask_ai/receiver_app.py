from flask import Flask, request, jsonify
from pathlib import Path
from datetime import datetime
import json
import traceback

app = Flask(__name__)

# IMPORTANT: use raw strings or pathlib to avoid Windows escape bugs
RAW_DIR = Path(r"F:\ai_inbox\raw")
NORMALIZED_DIR = Path(r"F:\ai_inbox\normalized")

# Ensure folders exist at startup
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)


def _nullify_empty(v):
    """Convert empty strings to None (so JSON becomes null)."""
    if v == "":
        return None
    return v


def _get(obj: dict, key: str, default=None):
    """Safe getter that also nullifies empty strings."""
    if not isinstance(obj, dict):
        return default
    return _nullify_empty(obj.get(key, default))


def _leg_get(leg: dict, canonical_key: str):
    """
    Support both naming styles that may appear:
      - Canonical: PickupLocation, PickupLat, PickupLon...
      - Alternative: pickupName, pickupLat, pickupLon...
    """
    if not isinstance(leg, dict):
        return None

    alt_map = {
        "PickupLocation": ["PickupLocation", "pickupName", "pickupLocation"],
        "PickupLat": ["PickupLat", "pickupLat"],
        "PickupLon": ["PickupLon", "pickupLon"],
        "DropoffLocation": ["DropoffLocation", "dropoffName", "dropoffLocation"],
        "DropoffLat": ["DropoffLat", "dropoffLat"],
        "DropoffLon": ["DropoffLon", "dropoffLon"],
        "PickupTime": ["PickupTime", "pickupTime"],
        "ETA": ["ETA", "etaMin", "eta"],
        "TripType": ["TripType", "tripType"]
    }

    for k in alt_map.get(canonical_key, [canonical_key]):
        if k in leg:
            return _nullify_empty(leg.get(k))
    return None


def normalize_payload(data: dict):
    assignment_request_id = data.get("assignmentRequestID")

    drivers_in = data.get("drivers", []) or []
    schedules_in = data.get("driverSchedules", []) or []
    bookings_in = data.get("bookings", []) or []

    # Normalize Drivers
    driver_cols = [
        "DriverID", "DriverName", "DriverPhone", "CarType", "NoOfSeats", "DriverStatus",
        "DriverMonthlyMinimum", "DriverAssignedCounts", "DriverPayoutFrequency",
        "DriverStartingLocation", "DriverStartingLocationLat", "DriverStartingLocationLon",
        "DriverNotes", "AssignmentRequestID"
    ]
    drivers_out = []
    for d in drivers_in:
        row = {c: None for c in driver_cols}
        for c in driver_cols:
            if c == "AssignmentRequestID":
                row[c] = assignment_request_id
            else:
                row[c] = _get(d, c, None)
        drivers_out.append(row)

    # Normalize DriverSchedules
    schedule_cols = [
        "ScheduleID", "DriverID", "ActiveRideID", "ScheduleStartTime", "ScheduleEndTime",
        "ScheduleStartLocationName", "ScheduleStartLat", "ScheduleStartLon",
        "ScheduleEndLocationName", "ScheduleEndLat", "ScheduleEndLon",
        "ScheduleETA", "ScheduleTripType", "ScheduleSeatsOccupied",
        "ScheduleStatus", "ScheduleNotes", "AssignmentRequestID"
    ]
    schedules_out = []
    for s in schedules_in:
        row = {c: None for c in schedule_cols}
        for c in schedule_cols:
            if c == "AssignmentRequestID":
                row[c] = assignment_request_id
            else:
                row[c] = _get(s, c, None)
        schedules_out.append(row)

    # Normalize Bookings into leg-blocks
    booking_cols = [
        "BookingID", "CreatedAt", "PassengerName", "PassengerPhone", "NoOfPassengers",
        "DaysPerWeek", "PassengerMonthlyFare", "PassengerNotes", "PassengerBookingActiveStatus",
        "TripSide",
        "PickupLocation", "PickupLat", "PickupLon",
        "DropoffLocation", "DropoffLat", "DropoffLon",
        "PickupTime", "ETA", "TripType",
        "AssignmentRequestID"
    ]

    bookings_out = []
    for b in bookings_in:
        legs = b.get("legs", {}) if isinstance(b, dict) else {}

        # Only create blocks for legs that exist
        for trip_side in ["morning", "evening"]:
            leg = legs.get(trip_side)
            if not leg:
                continue

            row = {c: None for c in booking_cols}

            # Common booking fields
            row["BookingID"] = _get(b, "BookingID")
            row["CreatedAt"] = _get(b, "CreatedAt")
            row["PassengerName"] = _get(b, "PassengerName")
            row["PassengerPhone"] = _get(b, "PassengerPhone")
            row["NoOfPassengers"] = _get(b, "NoOfPassengers")
            row["DaysPerWeek"] = _get(b, "DaysPerWeek")
            row["PassengerMonthlyFare"] = _get(b, "PassengerMonthlyFare")
            row["PassengerNotes"] = _get(b, "PassengerNotes")
            row["PassengerBookingActiveStatus"] = _get(b, "PassengerBookingActiveStatus")

            # TripSide from leg name
            row["TripSide"] = trip_side

            # Leg-specific fields (support both key styles)
            row["PickupLocation"] = _leg_get(leg, "PickupLocation")
            row["PickupLat"] = _leg_get(leg, "PickupLat")
            row["PickupLon"] = _leg_get(leg, "PickupLon")
            row["DropoffLocation"] = _leg_get(leg, "DropoffLocation")
            row["DropoffLat"] = _leg_get(leg, "DropoffLat")
            row["DropoffLon"] = _leg_get(leg, "DropoffLon")
            row["PickupTime"] = _leg_get(leg, "PickupTime")
            row["ETA"] = _leg_get(leg, "ETA")
            row["TripType"] = _leg_get(leg, "TripType")

            row["AssignmentRequestID"] = assignment_request_id

            bookings_out.append(row)

    normalized = {
        "assignmentRequestID": assignment_request_id,
        "drivers": drivers_out,
        "driverSchedules": schedules_out,
        "bookings": bookings_out,
        "counts": {
            "drivers": len(drivers_out),
            "driverSchedules": len(schedules_out),
            "bookings": len(bookings_out)
        }
    }

    return normalized


@app.route("/process_assignments", methods=["POST"])
def process_assignments():
    try:
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, dict):
            return jsonify({"status": "error", "message": "JSON body must be an object"}), 400

        assignment_request_id = data.get("assignmentRequestID")
        if not assignment_request_id:
            return jsonify({"status": "error", "message": "assignmentRequestID is required"}), 400

        drivers = data.get("drivers", []) or []
        schedules = data.get("driverSchedules", []) or []
        bookings = data.get("bookings", []) or []

        print("\n[RECEIVED]")
        print(f" assignmentRequestID: {assignment_request_id}")
        print(f" drivers: {len(drivers)} | schedules: {len(schedules)} | bookings: {len(bookings)}")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        raw_path = RAW_DIR / f"{assignment_request_id}__{ts}__raw.json"
        norm_path = NORMALIZED_DIR / f"{assignment_request_id}__{ts}.json"

        # Save RAW
        with raw_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Normalize
        normalized = normalize_payload(data)

        # Save NORMALIZED
        with norm_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)

        # VERIFY (this is the key part)
        raw_exists = raw_path.exists()
        norm_exists = norm_path.exists()
        raw_size = raw_path.stat().st_size if raw_exists else 0
        norm_size = norm_path.stat().st_size if norm_exists else 0

        print(f"[RAW SAVED] {raw_path} | exists={raw_exists} | size={raw_size} bytes")
        print(f"[NORMALIZED SAVED] {norm_path} | exists={norm_exists} | size={norm_size} bytes")
        print(f"[COUNTS] Drivers={normalized['counts']['drivers']}, Schedules={normalized['counts']['driverSchedules']}, Bookings={normalized['counts']['bookings']}")

        if not (raw_exists and norm_exists):
            return jsonify({
                "status": "error",
                "message": "Files did not save (verification failed). Check path/permissions.",
                "rawPath": str(raw_path),
                "normalizedPath": str(norm_path)
            }), 500

        return jsonify({
            "status": "received",
            "message": "Payload received and saved to disk.",
            "assignmentRequestID": assignment_request_id,
            "rawPath": str(raw_path),
            "normalizedPath": str(norm_path),
            "rawBytes": raw_size,
            "normalizedBytes": norm_size,
            "counts": normalized["counts"]
        }), 200

    except Exception as e:
        print("[ERROR] Exception in /process_assignments")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/test", methods=["GET"])
def test():
    return jsonify({"status": "ok", "rawDir": str(RAW_DIR), "normalizedDir": str(NORMALIZED_DIR)}), 200


if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=5000, debug=True)
