"""
Loads the fetched CSVs into SQLite and creates a scored view via SQL.
Run after fetch_data.py:
    python build_database.py
"""

import sqlite3
import pandas as pd

DB_PATH = "market_data.db"

conn = sqlite3.connect(DB_PATH)

snapshot = pd.read_csv("wdi_snapshot_latest.csv")
timeseries = pd.read_csv("wdi_timeseries.csv")

snapshot.to_sql("country_snapshot", conn, if_exists="replace", index=False)
timeseries.to_sql("country_timeseries", conn, if_exists="replace", index=False)

conn.execute("CREATE INDEX IF NOT EXISTS idx_ts_country_year ON country_timeseries(country_code, year)")

# Market Opportunity Score: a weighted, min-max-normalized composite built entirely in SQL.
# Growth + digital readiness + population scale, minus macro instability (inflation, unemployment).
conn.executescript("""
DROP VIEW IF EXISTS market_opportunity_score;
CREATE VIEW market_opportunity_score AS
WITH bounds AS (
    SELECT
        MIN(gdp_growth_pct) AS min_growth, MAX(gdp_growth_pct) AS max_growth,
        MIN(internet_users_pct) AS min_net, MAX(internet_users_pct) AS max_net,
        MIN(pop_growth_pct) AS min_popg, MAX(pop_growth_pct) AS max_popg,
        MIN(inflation_pct) AS min_inf, MAX(inflation_pct) AS max_inf,
        MIN(unemployment_pct) AS min_unemp, MAX(unemployment_pct) AS max_unemp
    FROM country_snapshot
    WHERE income_level NOT IN ('High income')
),
scored AS (
    SELECT
        s.country_code,
        s.country_name,
        s.region,
        s.income_level,
        s.population,
        s.gdp_per_capita_usd,
        s.gdp_growth_pct,
        s.internet_users_pct,
        s.mobile_subs_per100,
        s.inflation_pct,
        s.unemployment_pct,
        -- normalize each factor to 0-1, higher = more attractive
        (s.gdp_growth_pct - b.min_growth) * 1.0 / NULLIF(b.max_growth - b.min_growth, 0) AS n_growth,
        (s.internet_users_pct - b.min_net) * 1.0 / NULLIF(b.max_net - b.min_net, 0) AS n_digital,
        (s.pop_growth_pct - b.min_popg) * 1.0 / NULLIF(b.max_popg - b.min_popg, 0) AS n_popgrowth,
        1 - (s.inflation_pct - b.min_inf) * 1.0 / NULLIF(b.max_inf - b.min_inf, 0) AS n_stability,
        1 - (s.unemployment_pct - b.min_unemp) * 1.0 / NULLIF(b.max_unemp - b.min_unemp, 0) AS n_labor
    FROM country_snapshot s CROSS JOIN bounds b
    WHERE s.income_level NOT IN ('High income')
      AND s.gdp_growth_pct IS NOT NULL
)
SELECT
    country_code, country_name, region, income_level, population,
    gdp_per_capita_usd, gdp_growth_pct, internet_users_pct, mobile_subs_per100,
    inflation_pct, unemployment_pct,
    ROUND(
        COALESCE(n_growth, 0.5) * 0.30 +
        COALESCE(n_digital, 0.5) * 0.25 +
        COALESCE(n_popgrowth, 0.5) * 0.15 +
        COALESCE(n_stability, 0.5) * 0.20 +
        COALESCE(n_labor, 0.5) * 0.10
    , 4) AS opportunity_score
FROM scored
ORDER BY opportunity_score DESC;
""")

conn.commit()
conn.close()
print(f"Database built: {DB_PATH}")
print("Tables: country_snapshot, country_timeseries")
print("View:   market_opportunity_score")
