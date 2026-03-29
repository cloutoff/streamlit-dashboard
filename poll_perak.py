import requests
import sqlite3
import time
import os
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
USERNAME = "woahdammo"  # replace with your OpenSky username
PASSWORD = "Adamcool66?"  # replace with your OpenSky password
POLL_INTERVAL = 900  # 15 minutes, safer for OpenSky limits
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "perak_flights.db")

# -----------------------------
# FUNCTIONS
# -----------------------------
def in_perak(lat, lon):
    """Check if coordinates are within Perak boundary."""
    return lat is not None and lon is not None and (3.5 <= lat <= 5.5) and (100.0 <= lon <= 101.5)

def setup_database():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao24 TEXT,
            callsign TEXT,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perak_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            aircraft_count INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_data(states):
    """Save flights in Perak to database and track count."""
    print(f"Total aircraft fetched: {len(states)}")
    in_perak_count = sum(1 for s in states if in_perak(s[6], s[5]))
    print(f"Aircraft in Perak: {in_perak_count}")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    count = 0
    for state in states:
        lat = state[6]
        lon = state[5]
        if in_perak(lat, lon):
            callsign = state[1] if state[1] else "UNKNOWN"
            cursor.execute("""
                INSERT INTO flights (icao24, callsign, latitude, longitude, altitude, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state[0],
                callsign,
                lat,
                lon,
                state[7],
                datetime.now().isoformat()
            ))
            count += 1

    cursor.execute("""
        INSERT INTO perak_counts (timestamp, aircraft_count)
        VALUES (?, ?)
    """, (datetime.now().isoformat(), count))

    conn.commit()
    conn.close()
    print(f"[{datetime.now()}] Saved {count} flights in Perak.\n")

def fetch_states():
    """Fetch flight states once per poll, skip on rate limit."""
    try:
        response = requests.get(
            "https://opensky-network.org/api/states/all?lamin=3.5&lomin=100.0&lamax=5.5&lomax=101.5",
            auth=(USERNAME, PASSWORD),
            headers={"User-Agent": "PerakFlightTracker/1.0"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("states", [])
        elif response.status_code == 429:
            print(f"Rate limited by OpenSky. Skipping this poll.")
            return []
        else:
            print(f"Error fetching data: {response.status_code}. Skipping this poll.")
            return []
    except Exception as e:
        print(f"Exception occurred: {e}. Skipping this poll.")
        return []

# -----------------------------
# MAIN LOOP
# -----------------------------
setup_database()

print(f"Starting Perak flight tracker. Polling every {POLL_INTERVAL // 60} minutes.\n")

while True:
    states = fetch_states()
    if states:
        save_data(states)
    else:
        print(f"No data saved this poll.\n")

    print(f"Waiting {POLL_INTERVAL // 60} minutes until next poll...\n")
    time.sleep(POLL_INTERVAL)