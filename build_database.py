"""
Loads the fetched CSVs into SQLite and builds the Ecosystem Readiness scoring view.
The scoring logic itself lives in schema.sql, this script just loads data and runs it.

Run after fetch_data.py:
    python build_database.py
"""

import sqlite3
import pandas as pd

DB_PATH = "market_data.db"
SCHEMA_PATH = "schema.sql"

conn = sqlite3.connect(DB_PATH)

snapshot = pd.read_csv("wdi_snapshot_latest.csv")
timeseries = pd.read_csv("wdi_timeseries.csv")

snapshot.to_sql("country_snapshot", conn, if_exists="replace", index=False)
timeseries.to_sql("country_timeseries", conn, if_exists="replace", index=False)

conn.execute("CREATE INDEX IF NOT EXISTS idx_ts_country_year ON country_timeseries(country_code, year)")

with open(SCHEMA_PATH) as f:
    conn.executescript(f.read())

conn.commit()
conn.close()
print(f"Database built: {DB_PATH}")
print("Tables: country_snapshot, country_timeseries")
print("View:   ecosystem_readiness_score (defined in schema.sql)")
