import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import matplotlib.ticker as ticker
import random

DATABASE_FILE = "perak_flights.db"

# -----------------------------
# CONFIG
# -----------------------------
USE_FAKE_DISPLAY = True  # Set True to use fake data, False for real database

# Auto-refresh every 60 seconds
st_autorefresh(interval=60 * 1000, key="datarefresh")

# -----------------------------
# DATABASE FUNCTIONS
# -----------------------------
def get_aircraft_counts():
    conn = sqlite3.connect(DATABASE_FILE)
    df = pd.read_sql_query("SELECT * FROM perak_counts ORDER BY timestamp", conn)
    conn.close()
    return df

def get_all_flights():
    conn = sqlite3.connect(DATABASE_FILE)
    df = pd.read_sql_query("SELECT * FROM flights ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# -----------------------------
# FAKE DATA GENERATOR (DISPLAY ONLY)
# -----------------------------
def generate_fake_dataframe():
    records_flights = []
    records_counts = []

    dates = ["2026-03-27", "2026-03-29"]
    for date_str in dates:
        current_time = datetime.strptime(date_str + " 00:00", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(date_str + " 23:59", "%Y-%m-%d %H:%M")

        while current_time <= end_time:
            aircraft_count = random.randint(0, 8)

            for _ in range(aircraft_count):
                records_flights.append({
                    "icao24": ''.join(random.choices('abcdef0123456789', k=6)),
                    "callsign": "FL" + str(random.randint(100, 999)),
                    "latitude": random.uniform(3.5, 5.5),
                    "longitude": random.uniform(100.0, 101.5),
                    "altitude": random.randint(8000, 40000),
                    "timestamp": current_time.isoformat()
                })

            records_counts.append({
                "timestamp": current_time.isoformat(),
                "aircraft_count": aircraft_count
            })

            current_time += timedelta(minutes=15)

    flights_df = pd.DataFrame(records_flights)
    counts_df = pd.DataFrame(records_counts)

    return flights_df, counts_df

# -----------------------------
# DASHBOARD
# -----------------------------
st.set_page_config(page_title="Perak Flight Tracker", layout="wide")
st.title("Perak Flight Tracker Dashboard")

# -----------------------------
# LOAD DATA (FAKE OR REAL)
# -----------------------------
if USE_FAKE_DISPLAY:
    all_flights, counts_df = generate_fake_dataframe()
else:
    counts_df = get_aircraft_counts()
    all_flights = get_all_flights()

# -----------------------------
# Latest timestamp
# -----------------------------
if not counts_df.empty:
    last_update = counts_df["timestamp"].iloc[-1]
    st.subheader(f"Last Update: {last_update}")
else:
    st.subheader("No data yet.")

# -----------------------------
# Side by side: Graphs and Table
# -----------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Aircraft Count in Perak Over Time")

    if not counts_df.empty:
        counts_df["timestamp"] = pd.to_datetime(counts_df["timestamp"])
        counts_df = counts_df.set_index("timestamp")
        counts_df["aircraft_count"] = counts_df["aircraft_count"].astype(int)

        # -----------------------------
        # Line & Area side by side
        # -----------------------------
        chart_col1, chart_col2 = st.columns(2)

        # Line Chart
        with chart_col1:
            st.write("### Line Chart")
            fig1, ax1 = plt.subplots(figsize=(5, 3))
            ax1.plot(counts_df.index, counts_df["aircraft_count"], marker='o')
            ax1.set_xlabel("Time")
            ax1.set_ylabel("Aircraft Count")
            ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            plt.xticks(rotation=45)
            st.pyplot(fig1)

        # Area Chart
        with chart_col2:
            st.write("### Area Chart")
            fig2, ax2 = plt.subplots(figsize=(5, 3))
            ax2.fill_between(counts_df.index, counts_df["aircraft_count"], alpha=0.5)
            ax2.plot(counts_df.index, counts_df["aircraft_count"])
            ax2.set_xlabel("Time")
            ax2.set_ylabel("Aircraft Count")
            ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            plt.xticks(rotation=45)
            st.pyplot(fig2)

        # Column Chart (below)
        st.write("### Column Chart")
        fig3, ax3 = plt.subplots(figsize=(6, 3))

        x = range(len(counts_df.index))
        ax3.bar(x, counts_df["aircraft_count"], width=0.5)

        ax3.set_xticks(x[::max(1, len(x)//10)])
        ax3.set_xticklabels(
            counts_df.index.strftime('%H:%M')[::max(1, len(x)//10)],
            rotation=45
        )

        ax3.set_xlabel("Time")
        ax3.set_ylabel("Aircraft Count")
        ax3.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        st.pyplot(fig3)
    else:
        st.write("No count data available yet.")

with col2:
    st.subheader("All Recorded Flights in Database")
    if not all_flights.empty:
        # Remove 'id' column if exists
        display_df = all_flights.drop(columns=["id"], errors="ignore")
        display_df = display_df.rename(columns={
            "icao24": "ICAO24",
            "callsign": "Callsign",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "altitude": "Altitude (m)",
            "timestamp": "Time"
        })
        st.dataframe(display_df, height=500)
    else:
        st.write("No flight data recorded yet.")

# -----------------------------
# Map (Historical + Latest)
# -----------------------------
st.subheader("All Aircraft Positions in Perak (Historical & Latest)")

m = folium.Map(location=[4.75, 101.0], zoom_start=7)

# Perak boundary
folium.Rectangle(
    bounds=[[3.5, 100.0], [5.5, 101.5]],
    color="blue",
    weight=2,
    fill=False
).add_to(m)

# Flight markers
for _, row in all_flights.iterrows():
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=(
            f"ICAO24: {row['icao24']}\n"
            f"Callsign: {row['callsign']}\n"
            f"Lat: {row['latitude']}\n"
            f"Lon: {row['longitude']}\n"
            f"Altitude: {row['altitude']} m\n"
            f"Timestamp: {row['timestamp']}"
        ),
        icon=folium.Icon(color="red", icon="plane", prefix='fa')
    ).add_to(m)

st_folium(m, width=700, height=500)