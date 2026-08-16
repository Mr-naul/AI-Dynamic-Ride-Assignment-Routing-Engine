from flask import Flask, request, jsonify
import mysql.connector
import json
import traceback
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# -----------------------------
# MySQL Database Configuration
# -----------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "admin",
    "database": "ai_project_db"
}

# -----------------------------
# Output folder configuration
# -----------------------------
OUT_DIR = Path(r"F:/ai_outbox/Manualuploads")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# DB Connection
# -----------------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        print(f"[INFO] Database connected successfully: {DB_CONFIG['host']}")
        return conn
    except mysql.connector.Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None


# -----------------------------
# Fetch assignments by AssignmentRequestID
# -----------------------------
def get_assignments(assignment_request_id):
    conn = get_db_connection()
    if conn is None:
        print("[ERROR] Database connection failed.")
        return None

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM assignments WHERE AssignmentRequestID = %s"
    cursor.execute(query, (assignment_request_id,))
    rows = cursor.fetchall()

    print(f"[INFO] Found {len(rows)} assignments for AssignmentRequestID {assignment_request_id}.")
    conn.close()
    return rows


# -----------------------------
# Construct JSON response (same as sender)
# -----------------------------
def construct_json(assignments):
    json_response = {
        "Assignments": []
    }

    for assignment in assignments:
        assignment_data = {
            "AssignmentID": assignment.get('AssignmentID', ""),
            "BookingID": assignment.get('BookingID', ""),
            "TripSide": assignment.get('TripSide', ""),
            "PassengerName": assignment.get('PassengerName', ""),
            "PassengerPhone": assignment.get('PassengerPhone', ""),
            "NoOfWorkingDays": assignment.get('NoOfWorkingDays', ""),
            "PickupLocationName": assignment.get('PickupLocationName', ""),
            "PickupLocationLat": assignment.get('PickupLocationLat', ""),
            "PickupLocationLon": assignment.get('PickupLocationLon', ""),
            "DropoffLocationName": assignment.get('DropoffLocationName', ""),
            "DropoffLocationLat": assignment.get('DropoffLocationLat', ""),
            "DropoffLocationLon": assignment.get('DropoffLocationLon', ""),
            "PickupTime": assignment.get('PickupTime', ""),
            "ETA": assignment.get('ETA', ""),
            "SuggestedDriverID": assignment.get('SuggestedDriverID', ""),
            "AssignmentType": assignment.get('AssignmentType', ""),
            "SeatsOccupiedInSchedule": assignment.get('SeatsOccupiedInSchedule', ""),
            "FitScore": assignment.get('FitScore', ""),
            "SugestionDetail": assignment.get('SugestionDetail', ""),  # keep typo (Sheets expects it)
            "SystemRemarks": assignment.get('SystemRemarks', ""),
            "RelatedBookingIDs": assignment.get('RelatedBookingIDs', "")
        }
        
    return json_response


# -----------------------------
# Save JSON to disk (atomic)
# -----------------------------
def save_json_to_file(assignment_request_id, payload):
    # Save as: F:/ai_outbox/Manualuploads/<AssignmentRequestID>.json
    filename = f"{assignment_request_id}.json"
    final_path = OUT_DIR / filename
    tmp_path = OUT_DIR / (filename + ".tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # atomic replace
    os.replace(tmp_path, final_path)

    return str(final_path)


# -----------------------------
# Route: Export + Save (GET or POST)
# -----------------------------
@app.route("/export_assignments", methods=["GET", "POST"])
def export_assignments():
    try:
        # Accept AssignmentRequestID from:
        # - GET query param
        # - POST JSON body
        assignment_request_id = (request.args.get('AssignmentRequestID') or "").strip()

        if request.method == "POST" and not assignment_request_id:
            if request.is_json:
                body = request.get_json(silent=True) or {}
                assignment_request_id = (body.get("AssignmentRequestID") or "").strip()

        print(f"[INFO] Request received from {request.remote_addr} with AssignmentRequestID: {assignment_request_id}")

        if not assignment_request_id:
            print("[ERROR] AssignmentRequestID is missing in the request.")
            return jsonify({"status": "error", "message": "AssignmentRequestID is required"}), 400

        # Step 1: Query DB
        assignments = get_assignments(assignment_request_id)

        if not assignments:
            print(f"[INFO] No data found for AssignmentRequestID: {assignment_request_id}")
            return jsonify({"status": "error", "message": "No data available for this ID"}), 404

        # Step 2: Construct JSON (same as sender)
        json_payload = construct_json(assignments)

        # Optional metadata (does NOT affect Sheets, since Sheets only reads Assignments[])
        json_payload["ResultID"] = assignment_request_id
        json_payload["SavedAt"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Step 3: Save JSON to folder
        saved_path = save_json_to_file(assignment_request_id, json_payload)

        print(f"[INFO] JSON saved successfully: {saved_path}")

        # Step 4: Return status to Postman (not the big payload)
        return jsonify({
            "status": "ready",
            "message": "JSON saved successfully",
            "AssignmentRequestID": assignment_request_id,
            "file_path": saved_path,
            "assignments_count": len(json_payload.get("Assignments", []))
        }), 200

    except Exception as e:
        print(f"[ERROR] Exception in /export_assignments: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    print("[INFO] Manual Export Flask starting... Listening on port 5002.")
    app.run(host="0.0.0.0", port=5002, debug=True)
