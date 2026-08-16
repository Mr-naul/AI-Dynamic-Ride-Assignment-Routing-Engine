import os
import json
import shutil
import traceback
import mysql.connector
from mysql.connector import Error

# =========================
# CONFIGURATION
# =========================
BASE_DIR = r"F:\ai_inbox"

NORMALIZED_DIR = os.path.join(BASE_DIR, "normalized")
INPROGRESS_DIR = os.path.join(BASE_DIR, "inprogressnormalized")
PROCESSED_DIR = os.path.join(BASE_DIR, "processednormalized")
FAILED_DIR = os.path.join(BASE_DIR, "failednormalized")

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
    for d in [NORMALIZED_DIR, INPROGRESS_DIR, PROCESSED_DIR, FAILED_DIR]:
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
def insert_drivers(cursor, drivers):
    debug(f"Inserting {len(drivers)} drivers...")
    sql = """
        INSERT INTO Drivers (
            DriverID, DriverName, DriverPhone, CarType, NoOfSeats,
            DriverStatus, DriverMonthlyMinimum, DriverAssignedCounts,
            DriverPayoutFrequency, DriverStartingLocation,
            DriverStartingLocationLat, DriverStartingLocationLon,
            DriverNotes, AssignmentRequestID
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    for d in drivers:
        cursor.execute(sql, (
            d.get("DriverID"),
            d.get("DriverName"),
            d.get("DriverPhone"),
            d.get("CarType"),
            d.get("NoOfSeats"),
            d.get("DriverStatus"),
            d.get("DriverMonthlyMinimum"),
            d.get("DriverAssignedCounts"),
            d.get("DriverPayoutFrequency"),
            d.get("DriverStartingLocation"),
            d.get("DriverStartingLocationLat"),
            d.get("DriverStartingLocationLon"),
            d.get("DriverNotes"),
            d.get("AssignmentRequestID"),
        ))

def insert_driver_schedules(cursor, schedules):
    debug(f"Inserting {len(schedules)} driver schedules...")
    sql = """
        INSERT INTO DriverSchedules (
            ScheduleID, DriverID, ActiveRideID,
            ScheduleStartTime, ScheduleEndTime,
            ScheduleStartLocationName, ScheduleStartLat, ScheduleStartLon,
            ScheduleEndLocationName, ScheduleEndLat, ScheduleEndLon,
            ScheduleETA, ScheduleTripType, ScheduleSeatsOccupied,
            ScheduleStatus, ScheduleNotes, AssignmentRequestID
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    for s in schedules:
        cursor.execute(sql, (
            s.get("ScheduleID"),
            s.get("DriverID"),
            s.get("ActiveRideID"),
            s.get("ScheduleStartTime"),
            s.get("ScheduleEndTime"),
            s.get("ScheduleStartLocationName"),
            s.get("ScheduleStartLat"),
            s.get("ScheduleStartLon"),
            s.get("ScheduleEndLocationName"),
            s.get("ScheduleEndLat"),
            s.get("ScheduleEndLon"),
            s.get("ScheduleETA"),
            s.get("ScheduleTripType"),
            s.get("ScheduleSeatsOccupied"),
            s.get("ScheduleStatus"),
            s.get("ScheduleNotes"),
            s.get("AssignmentRequestID"),
        ))

def insert_bookings(cursor, bookings):
    debug(f"Inserting {len(bookings)} bookings...")
    sql = """
        INSERT INTO Bookings (
            BookingID, CreatedAt, PassengerName, PassengerPhone,
            NoOfPassengers, DaysPerWeek, PassengerMonthlyFare,
            PassengerNotes, PassengerBookingActiveStatus,
            TripSide, PickupLocation, PickupLat, PickupLon,
            DropoffLocation, DropoffLat, DropoffLon,
            PickupTime, ETA, TripType, AssignmentRequestID
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    for b in bookings:
        cursor.execute(sql, (
            b.get("BookingID"),
            b.get("CreatedAt"),
            b.get("PassengerName"),
            b.get("PassengerPhone"),
            b.get("NoOfPassengers"),
            b.get("DaysPerWeek"),
            b.get("PassengerMonthlyFare"),
            b.get("PassengerNotes"),
            b.get("PassengerBookingActiveStatus"),
            b.get("TripSide"),
            b.get("PickupLocation"),
            b.get("PickupLat"),
            b.get("PickupLon"),
            b.get("DropoffLocation"),
            b.get("DropoffLat"),
            b.get("DropoffLon"),
            b.get("PickupTime"),
            b.get("ETA"),
            b.get("TripType"),
            b.get("AssignmentRequestID"),
        ))

# =========================
# MAIN PROCESSOR
# =========================
def process_file(filename):
    src = os.path.join(NORMALIZED_DIR, filename)
    inprogress = os.path.join(INPROGRESS_DIR, filename)
    processed = os.path.join(PROCESSED_DIR, filename)
    failed = os.path.join(FAILED_DIR, filename)

    debug(f"Claiming file: {filename}")
    shutil.move(src, inprogress)

    conn = None
    try:
        with open(inprogress, "r", encoding="utf-8") as f:
            data = json.load(f)

        conn = get_db_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        debug("DB transaction started.")

        insert_drivers(cursor, data.get("Drivers", []))
        insert_driver_schedules(cursor, data.get("DriverSchedules", []))
        insert_bookings(cursor, data.get("Bookings", []))

        conn.commit()
        debug("DB transaction COMMITTED.")

        shutil.move(inprogress, processed)
        debug(f"File moved to processed: {filename}")

    except Exception as e:
        if conn:
            conn.rollback()
            error("DB transaction ROLLED BACK.")

        error(f"Processing failed for file: {filename}")
        traceback.print_exc()

        if os.path.exists(inprogress):
            shutil.move(inprogress, failed)
            debug(f"File moved to failed: {filename}")

    finally:
        if conn:
            conn.close()
            debug("DB connection closed.")

# =========================
# ENTRY POINT
# =========================
def main():
    ensure_dirs()
    files = [f for f in os.listdir(NORMALIZED_DIR) if f.endswith(".json")]

    if not files:
        debug("No files found to process.")
        return

    debug(f"Found {len(files)} file(s) to process.")
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()
