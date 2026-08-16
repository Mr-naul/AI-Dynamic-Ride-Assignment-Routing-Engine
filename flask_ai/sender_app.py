from flask import Flask, request, jsonify
import mysql.connector
import json
import traceback
from datetime import datetime

app = Flask(__name__)

# MySQL Database Configuration
DB_CONFIG = {
    "host": "localhost",  # Your MySQL server address
    "user": "root",  # MySQL user
    "password": "admin",  # MySQL password
    "database": "ai_project_db"  # Your database name
}

# Function to establish MySQL database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        print(f"Database connected successfully: {DB_CONFIG['host']}")
        return conn
    except mysql.connector.Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None

# Function to fetch assignments from the database based on AssignmentRequestID
def get_assignments(assignment_request_id):
    conn = get_db_connection()
    if conn is None:
        print("[ERROR] Database connection failed.")
        return None

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM assignments WHERE AssignmentRequestID = %s"
    cursor.execute(query, (assignment_request_id,))
    
    # Fetch all rows matching the AssignmentRequestID
    rows = cursor.fetchall()
    
    # Log number of assignments found
    print(f"Found {len(rows)} assignments for AssignmentRequestID {assignment_request_id}.")
    
    conn.close()  # Always close the connection after usage
    return rows

# Function to construct the JSON structure for the response
def construct_json(assignments):
    # Constructing the JSON response based on the assignments found
    json_response = {
        "Assignments": []
    }

    for assignment in assignments:
        assignment_data = {
            "AssignmentID": assignment['AssignmentID'],
            "BookingID": assignment['BookingID'],
            "TripSide": assignment['TripSide'],
            "PassengerName": assignment['PassengerName'],
            "PassengerPhone": assignment['PassengerPhone'],
            "NoOfWorkingDays": assignment['NoOfWorkingDays'],
            "PickupLocationName": assignment['PickupLocationName'],
            "PickupLocationLat": assignment['PickupLocationLat'],
            "PickupLocationLon": assignment['PickupLocationLon'],
            "DropoffLocationName": assignment['DropoffLocationName'],
            "DropoffLocationLat": assignment['DropoffLocationLat'],
            "DropoffLocationLon": assignment['DropoffLocationLon'],
            "PickupTime": assignment['PickupTime'],
            "ETA": assignment['ETA'],
            "SuggestedDriverID": assignment['SuggestedDriverID'],
            "AssignmentType": assignment['AssignmentType'],
            "SeatsOccupiedInSchedule": assignment['SeatsOccupiedInSchedule'],
            "FitScore": assignment['FitScore'],
            "SugestionDetail": assignment['SugestionDetail'],
            "SystemRemarks": assignment['SystemRemarks'],
            "RelatedBookingIDs": assignment['RelatedBookingIDs']
        }
        json_response["Assignments"].append(assignment_data)

    return json_response

@app.route("/get_assignments", methods=["GET"])
def fetch_assignments():
    try:
        # Step 1: Get AssignmentRequestID from the query parameters
        assignment_request_id = request.args.get('AssignmentRequestID')
        
        # Log the received request
        print(f"[INFO] Request received from {request.remote_addr} with AssignmentRequestID: {assignment_request_id}")
        
        if not assignment_request_id:
            print("[ERROR] AssignmentRequestID is missing in the request.")
            return jsonify({"status": "error", "message": "AssignmentRequestID is required"}), 400

        # Step 2: Query the database for matching assignments
        assignments = get_assignments(assignment_request_id)
        
        if not assignments:
            print(f"[INFO] No data found for AssignmentRequestID: {assignment_request_id}")
            return jsonify({"status": "error", "message": "No data available for this ID"}), 404
        
        # Step 3: Construct JSON response
        json_response = construct_json(assignments)

        # Step 4: Log and Return the JSON response
        print("[INFO] Assignments found and JSON response successfully constructed.")
        return jsonify(json_response), 200

    except Exception as e:
        print(f"[ERROR] Exception in /get_assignments: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Log that Flask app is starting
    print("[INFO] Flask app starting... Listening for GET requests.")
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
