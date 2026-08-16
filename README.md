AI Dynamic Ride Assignment & Routing Engine
1. Description

This system is an AI-powered backend designed for large-scale monthly passenger transportation management.

It receives operational data containing:

Passenger bookings
Pickup and drop-off locations
Pickup/drop-off timings
Passenger schedules
Driver availability
Existing driver assignments
Active/ongoing rides
Location coordinates

The AI normalizes this data, stores it in a database, analyzes possible passenger-driver combinations, and generates an optimized assignment plan.

The primary objective is to maximize the number of passengers that can be served using the available drivers, while considering:

Geographic location
Pickup and drop-off routes
Working days
Pickup times
Drop-off times
Driver availability
Existing passengers
Ride capacity
Rerouting possibilities
Route compatibility

Instead of relying on an expensive external routing API, the system uses a locally hosted UAE OpenStreetMap road network in PBF format, processed through OSRM inside Docker.

2. Main Architecture

The complete system is divided into three major stages:

                  GOOGLE SHEETS
                       │
                       ▼
              ┌─────────────────┐
              │    AI INBOX     │
              │ Receive JSON    │
              └────────┬────────┘
                       │
                       ▼
                Normalize Data
                       │
                       ▼
                 MySQL Database
                       │
                       ▼
              ┌─────────────────┐
              │  AI ASSIGNMENT  │
              │     ENGINE      │
              └────────┬────────┘
                       │
                       ▼
                 OSRM Routing
                       │
                       ▼
              Optimized Assignment
                       │
                       ▼
                Output JSON
                       │
                       ▼
                 AI OUTBOX
                       │
              ┌────────┴─────────┐
              ▼                  ▼
       Remote Transfer      Manual Upload
              │                  │
              └────────┬─────────┘
                       ▼
                  GOOGLE SHEETS
3. System Components
Part 1 — AI Inbox

The AI Inbox is responsible for receiving operational data.

Google Sheets exports the required data as JSON.

The receiving system accepts the JSON and places it into the processing pipeline.

Components
receiver_app.py
db_loader_app.py
manual_normalizer.py
Remote workflow
Google Sheets
      ↓
receiver_app.py
      ↓
Raw JSON
      ↓
Normalization
      ↓
db_loader_app.py
      ↓
Database
Manual workflow

When remote transfer isn't being used:

Google Sheets
      ↓
Download JSON
      ↓
Manualinbox/raw
      ↓
manual_normalizer.py
      ↓
db_loader_app.py
      ↓
Database

Every assignment request has its own unique ID, allowing the system to keep different datasets and generated assignments separated.

4. Part 2 — AI Assignment Engine

This is the core intelligence of the system.

The frontend provides an AssignmentRequestID.

The backend retrieves the corresponding operational data from the database and generates an optimized assignment plan.

The engine analyzes:

Passengers
Drivers
Existing Rides
Schedules
Pickup Locations
Drop-off Locations
Pickup Times
Drop-off Times
Driver Availability

It then determines:

Which passengers can share?
Which driver should receive them?
Which existing passenger can be rerouted?
Which driver has the best route?
Which passengers cannot currently be assigned?

The objective is to maximize passenger coverage while maintaining practical route and timing constraints.

5. Routing Engine

A major part of the project is the local routing infrastructure.

Instead of repeatedly calling an external Google Maps or routing API, the system uses:

OpenStreetMap → PBF → OSRM → Docker

UAE OSM PBF
     ↓
OSRM Extract
     ↓
OSRM Partition
     ↓
OSRM Customize
     ↓
OSRM Routing Server
     ↓
AI Assignment Engine

The routing server calculates realistic road distances and travel routes between coordinates.

This significantly reduces dependency on paid external routing APIs.

6. Part 2.2 — Output Database

After the assignment engine generates a solution, the resulting JSON is stored with the same AssignmentRequestID.

AssignmentRequestID
        ↓
AI Assignment Engine
        ↓
Assignment JSON
        ↓
Output Database

This makes it possible for the frontend to retrieve the generated assignment later without regenerating it.

7. Part 3 — AI Outbox

The AI Outbox handles the final assignment data.

There are two ways to transfer the result back.

Automatic
Output Database
      ↓
sender_app.py
      ↓
Internet / Tunnel
      ↓
Google Sheets
Manual
Output Database
      ↓
manual_export_app.py
      ↓
JSON File
      ↓
Google Sheets Upload

This gives the dispatcher a fallback method if remote communication is unavailable.

8. Project Organization

A recommended structure is:

mrcarlift-ai/
│
├── backend/
│   │
│   ├── run.py
│   │
│   ├── app.py
│   │
│   ├── assignment_engine/
│   │
│   ├── requirements.txt
│   │
│   └── data/
│       └── osm/
│           └── uae/
│               └── uae.osm.pbf
│
├── flask_ai_project/
│   │
│   ├── receiver_app.py
│   ├── sender_app.py
│   ├── db_loader_app.py
│   ├── db_loader_output.py
│   ├── manual_normalizer.py
│   ├── manual_export_app.py
│   │
│   ├── ai_inbox/
│   ├── ai_outbox/
│   └── manualinbox/
│
└── frontend/
    └── index.html

The exact folder names can be adjusted, but keeping input, processing, output, and routing infrastructure separated makes the system much easier to maintain.

9. Requirements

Part 2 uses:

Flask==3.0.3
flask-cors==4.0.1
python-dotenv==1.0.1
mysql-connector-python==9.0.0
cachetools==5.4.0

Install them using:

pip install -r requirements.txt

Create and activate the virtual environment:

python -m venv venv
venv\Scripts\activate
10. Database Setup

The system uses a database to separate incoming operational data from generated assignment results.

The basic flow is:

Incoming JSON
     ↓
Normalizer
     ↓
Database
     ↓
Assignment Engine
     ↓
Generated JSON
     ↓
Output Database

Database credentials should be stored in environment variables rather than hardcoded into Python files.

Example:

DB_HOST=
DB_USER=
DB_PASSWORD=
DB_NAME=
DB_PORT=

The database should contain the required tables for:

Assignment requests
Passengers
Drivers
Driver schedules
Active rides
Assignments
Generated output

The actual table structure should match the queries used by the assignment engine.

11. OSRM / PBF Setup
Step 1 — Prepare UAE PBF

Place the UAE OpenStreetMap PBF file here:

F:\mrcarlift-ai-backend\data\osm\uae\uae.osm.pbf
Step 2 — Extract Road Network

Run:

docker run --rm -t -v "F:\mrcarlift-ai-backend\data\osm\uae:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/uae.osm.pbf
Step 3 — Partition
docker run --rm -t -v "F:\mrcarlift-ai-backend\data\osm\uae:/data" osrm/osrm-backend osrm-partition /data/uae.osrm
Step 4 — Customize
docker run --rm -t -v "F:\mrcarlift-ai-backend\data\osm\uae:/data" osrm/osrm-backend osrm-customize /data/uae.osrm
Step 5 — Start OSRM

Remove an existing container if required:

docker rm -f osrm-uae

Start the routing server:

docker run -d --name osrm-uae -p 5001:5000 -v "F:\mrcarlift-ai-backend\data\osm\uae:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/uae.osrm

Check:

docker ps
12. Test OSRM

Test the routing server using:

curl "http://127.0.0.1:5001/route/v1/driving/55.2088,25.0609;55.3531,25.1605?overview=false"

If the server returns route information, the local routing engine is operational.

13. Starting the System

Activate the virtual environment:

venv\Scripts\activate

Start the required Flask services:

python receiver_app.py
python db_loader_app.py
python db_loader_output.py
python sender_app.py

These services handle the different stages of the data pipeline.

14. Assignment Generation

Start Docker:

docker start osrm-uae

Verify:

docker ps

Start the AI backend:

.\.venv\Scripts\activate
python run.py

Then start the frontend and provide:

AssignmentRequestID

The frontend sends the ID to the AI backend.

The backend:

ID
 ↓
Database
 ↓
Passenger + Driver Data
 ↓
Assignment Engine
 ↓
OSRM Route Calculation
 ↓
Optimization
 ↓
Assignment JSON
 ↓
Output Database
15. Remote Data Transfer

For remote Google Sheets communication, the Flask receiver/sender can be exposed through ngrok.

Start:

python receiver_app.py

Then:

ngrok http 5000

The generated tunnel URL can be configured in the Google Sheets integration.

The same approach can be used for the sender.

16. Manual Fallback

The system also supports completely manual operation.

Receiving

Place the downloaded raw JSON inside:

manualinbox/raw

Run:

venv\Scripts\activate
python manual_normalizer.py

Then load it:

python db_loader_app.py
Exporting

Run:

python manual_export_app.py

Then request:

/export_assignments?AssignmentRequestID=YOUR_ID

The generated JSON will be available inside:

ai_outbox/manualupload

This file can then be uploaded to Google Sheets manually.

17. Complete System Flow
             GOOGLE SHEETS
                   │
                   ▼
             JSON EXPORT
                   │
          ┌────────┴────────┐
          │                 │
       Remote             Manual
          │                 │
          ▼                 ▼
 receiver_app       manual_normalizer
          │                 │
          └────────┬────────┘
                   ▼
             db_loader_app
                   │
                   ▼
              MYSQL DB
                   │
                   ▼
        AssignmentRequestID
                   │
                   ▼
          AI ASSIGNMENT ENGINE
                   │
                   ├──────────────┐
                   │              │
                   ▼              ▼
             Passenger Data    Driver Data
                   │              │
                   └──────┬───────┘
                          ▼
                     OSRM ROUTER
                          │
                          ▼
                   Route Analysis
                          │
                          ▼
                 Optimized Assignment
                          │
                          ▼
                   Output JSON
                          │
                          ▼
               db_loader_output
                          │
                          ▼
                  OUTPUT DATABASE
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          sender_app.py      manual_export
                │                   │
                ▼                   ▼
         GOOGLE SHEETS        JSON DOWNLOAD
Key Value of the System

The main advantage is that the system turns a large transportation operation into a data-driven assignment problem.

Rather than manually deciding which driver should take which passenger, the system combines real operational data + geographic routing + timing constraints + existing rides to generate an optimized assignment plan while keeping the expensive routing infrastructure completely local.
