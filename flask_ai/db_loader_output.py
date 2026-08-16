import os
import json
import shutil
import traceback
import mysql.connector
from mysql.connector import Error

# =========================
# CONFIGURATION
# =========================
BASE_DIR = r"F:/ai_outbox"  # Correct base directory

# Folder paths (updated to correct directories)
ASSIGNMENTS_IN_DIR = r"F:/mrcarlift-ai-backend/output/assignments"  # Input directory
INPROGRESS_DIR = os.path.join(BASE_DIR, "inprocessing")  # Corrected path
PROCESSED_DIR  = os.path.join(BASE_DIR, "addedtodb")   # Corrected path
FAILED_DIR     = os.path.join(BASE_DIR, "failed")       # Corrected path

# DB Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "admin",
    "database": "ai_project_db",
}

# =========================
# UTILITY / DEBUG HELPERS
# =========================
def debug(msg):
    print(f"[DEBUG] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")

def ensure_dirs():
    for d in [ASSIGNMENTS_IN_DIR, INPROGRESS_DIR, PROCESSED_DIR, FAILED_DIR]:
        os.makedirs(d, exist_ok=True)

# =========================
# DB CONNECTION
# =========================
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        debug("Connected to MySQL successfully.")
        return conn
    except Error as e:
        error("Failed to connect to MySQL.")
        raise e

# =========================
# INSERT FUNCTIONS
# =========================
def insert_assignments(cursor, assignments, assignment_request_id):
    debug(f"Inserting {len(assignments)} assignments...")
    sql = """
        INSERT INTO Assignments (
            AssignmentID, AssignmentRequestID, BookingID, TripSide, PassengerName,
            PassengerPhone, NoOfWorkingDays, PickupLocationName, PickupLocationLat,
            PickupLocationLon, DropoffLocationName, DropoffLocationLat, DropoffLocationLon,
            PickupTime, ETA, SuggestedDriverID, AssignmentType, SeatsOccupiedInSchedule,
            FitScore, SugestionDetail, SystemRemarks, RelatedBookingIDs
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    
    for assignment in assignments:
        # Prepare values with NULL for missing data
        data = (
            assignment.get("AssignmentID", None),  # If not found, insert NULL
            assignment_request_id,  # AssignmentRequestID comes from the folder name
            assignment.get("BookingID", None),
            assignment.get("TripSide", None),
            assignment.get("PassengerName", None),
            assignment.get("PassengerPhone", None),
            assignment.get("NoOfWorkingDays", None),
            assignment.get("PickupLocationName", None),
            assignment.get("PickupLocationLat", None),
            assignment.get("PickupLocationLon", None),
            assignment.get("DropoffLocationName", None),
            assignment.get("DropoffLocationLat", None),
            assignment.get("DropoffLocationLon", None),
            assignment.get("PickupTime", None),
            assignment.get("ETA", None),
            assignment.get("SuggestedDriverID", None),
            assignment.get("AssignmentType", None),
            assignment.get("SeatsOccupiedInSchedule", None),
            assignment.get("FitScore", None),
            assignment.get("SugestionDetail", None),  # Correct spelling based on your DB
            assignment.get("SystemRemarks", None),
            assignment.get("RelatedBookingIDs", None),
        )

        # Debug the length of the data
        debug(f"Inserting data: {data}")
        debug(f"Data length: {len(data)} (Expected 22)")

        # Check if the data length matches the number of placeholders in the SQL query
        if len(data) != 22:
            error(f"Error: Data length does not match the expected number of columns. Expected 22, got {len(data)}")
            return  # Skip this insert if there's an issue

        # Execute the insert
        cursor.execute(sql, data)

# =========================
# MAIN PROCESSOR
# =========================
def process_folder(assignment_request_id):
    folder_path = os.path.join(ASSIGNMENTS_IN_DIR, assignment_request_id)
    inprogress_path = os.path.join(INPROGRESS_DIR, assignment_request_id)  # folder itself
    addedtodb_path = os.path.join(PROCESSED_DIR, assignment_request_id)  # Correct destination path
    failed_path = os.path.join(FAILED_DIR, assignment_request_id)  # Correct destination path

    debug(f"Claiming folder: {assignment_request_id}")
    
    # Move folder to inprogress
    shutil.move(folder_path, inprogress_path)
    debug(f"Folder moved to inprogress: {assignment_request_id}")

    conn = None
    try:
        # Read the JSON file inside the folder
        json_file_path = os.path.join(inprogress_path, "assignments.json")
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"{json_file_path} not found.")
        
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Connect to DB
        conn = get_db_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        debug("DB transaction started.")

        # Insert assignments into the database
        insert_assignments(cursor, data.get("Assignments", []), assignment_request_id)

        # Commit the transaction if everything is successful
        conn.commit()
        debug("DB transaction COMMITTED.")

        # Move the folder to addedtodb if success
        shutil.move(inprogress_path, addedtodb_path)
        debug(f"Folder moved to addedtodb: {assignment_request_id}")

    except Exception as e:
        if conn:
            conn.rollback()
            error("DB transaction ROLLED BACK.")

        error(f"Processing failed for folder: {assignment_request_id}")
        traceback.print_exc()

        # Move folder to failed if there's an error
        if os.path.exists(inprogress_path):
            shutil.move(inprogress_path, failed_path)
            debug(f"Folder moved to failed: {assignment_request_id}")

    finally:
        if conn:
            conn.close()
            debug("DB connection closed.")

# =========================
# ENTRY POINT
# =========================
def main():
    ensure_dirs()
    folders = [f for f in os.listdir(ASSIGNMENTS_IN_DIR) if os.path.isdir(os.path.join(ASSIGNMENTS_IN_DIR, f))]

    if not folders:
        debug("No folders found to process.")
        return

    debug(f"Found {len(folders)} folder(s) to process.")
    for folder in folders:
        process_folder(folder)

if __name__ == "__main__":
    main()