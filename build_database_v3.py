"""
Loads the fetched CSVs into SQLite and builds the Ecosystem Readiness scoring view.
Run after fetch_data_v6.py:
    python build_database_v3.py
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

# Entrepreneurial Ecosystem Readiness Score: a weighted, min-max-normalized composite.
# Fragile/conflict-affected status is exposed as a filterable flag, not scored down --
# fragile contexts are a deliberate target segment for entrepreneurship support programmes,
# not a disqualifier.
conn.executescript("""
DROP VIEW IF EXISTS ecosystem_readiness_score;
CREATE VIEW ecosystem_readiness_score AS
WITH bounds AS (
    SELECT
        MIN(gdp_growth_pct) AS min_growth, MAX(gdp_growth_pct) AS max_growth,
        MIN(internet_users_pct) AS min_net, MAX(internet_users_pct) AS max_net,
        MIN(self_employed_pct) AS min_selfemp, MAX(self_employed_pct) AS max_selfemp,
        MIN(days_to_start_business) AS min_days, MAX(days_to_start_business) AS max_days,
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
        s.is_fragile_or_conflict,
        s.population,
        s.gdp_per_capita_usd,
        s.gdp_growth_pct,
        s.internet_users_pct,
        s.mobile_subs_per100,
        s.self_employed_pct,
        s.agriculture_pct_gdp,
        s.poverty_headcount_pct,
        s.days_to_start_business,
        s.inflation_pct,
        s.unemployment_pct,
        (s.gdp_growth_pct - b.min_growth) * 1.0 / NULLIF(b.max_growth - b.min_growth, 0) AS n_growth,
        (s.internet_users_pct - b.min_net) * 1.0 / NULLIF(b.max_net - b.min_net, 0) AS n_digital,
        (s.self_employed_pct - b.min_selfemp) * 1.0 / NULLIF(b.max_selfemp - b.min_selfemp, 0) AS n_selfemp,
        1 - (s.days_to_start_business - b.min_days) * 1.0 / NULLIF(b.max_days - b.min_days, 0) AS n_ease,
        1 - (s.inflation_pct - b.min_inf) * 1.0 / NULLIF(b.max_inf - b.min_inf, 0) AS n_stability,
        1 - (s.unemployment_pct - b.min_unemp) * 1.0 / NULLIF(b.max_unemp - b.min_unemp, 0) AS n_labor
    FROM country_snapshot s CROSS JOIN bounds b
    WHERE s.income_level NOT IN ('High income')
      AND s.gdp_growth_pct IS NOT NULL
)
SELECT
    country_code, country_name, region, income_level, is_fragile_or_conflict, population,
    gdp_per_capita_usd, gdp_growth_pct, internet_users_pct, mobile_subs_per100,
    self_employed_pct, agriculture_pct_gdp, poverty_headcount_pct, days_to_start_business,
    inflation_pct, unemployment_pct,
    ROUND(
        COALESCE(n_growth, 0.5)   * 0.20 +
        COALESCE(n_digital, 0.5)  * 0.20 +
        COALESCE(n_selfemp, 0.5)  * 0.25 +
        COALESCE(n_ease, 0.5)     * 0.15 +
        COALESCE(n_stability, 0.5) * 0.10 +
        COALESCE(n_labor, 0.5)    * 0.10
    , 4) AS ecosystem_readiness_score
FROM scored
ORDER BY ecosystem_readiness_score DESC;
""")

conn.commit()
conn.close()
print(f"Database built: {DB_PATH}")
print("Tables: country_snapshot, country_timeseries")
print("View:   ecosystem_readiness_score")
