# Emerging Market Entry Dashboard

A business-analyst-style dashboard built with **Python, SQLite, and SQL** (no Power BI, no Kaggle account) —
answering: *"Which developing countries look most attractive for market expansion right now?"*

Data comes live from the [World Bank Open Data API](https://data.worldbank.org) — free, no key or login required.

## What this proves
- Pulling and cleaning real data via an API (`requests`, `pandas`)
- Modeling data in SQL: CTEs, window functions (`LAG`, `ROW_NUMBER`), views, normalized scoring
- Building your own composite metric (Market Opportunity Score) — not just plotting existing columns
- An interactive, deployable dashboard (Streamlit) with filters and a live-adjustable model

## Setup (run in your Mac terminal)

```bash
cd market_dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Pull live data from the World Bank API
python fetch_data.py

# 2. Load it into SQLite + build the scoring view
python build_database.py

# 3. Launch the dashboard
streamlit run dashboard.py
```

Your browser will open automatically at `http://localhost:8501`.

## Explore the SQL directly

```bash
sqlite3 market_data.db
.tables
.schema market_opportunity_score
```

Or run the example analyst queries:

```bash
sqlite3 market_data.db < analysis_queries.sql
```

## Deploying it live (optional, free)

Push this folder to a GitHub repo, then deploy at [share.streamlit.io](https://share.streamlit.io)
(Streamlit Community Cloud) — you'll get a public URL to put on your resume/LinkedIn instead of just a screenshot.
Note: you'll need to run `fetch_data.py` + `build_database.py` once and commit the resulting
`market_data.db` (or the CSVs) to the repo, since Streamlit Cloud won't run your fetch script for you.

## Files
- `fetch_data.py` — pulls 12 World Bank indicators (GDP growth, internet penetration, inflation, etc.) for every country
- `build_database.py` — loads data into SQLite, builds the `market_opportunity_score` SQL view
- `analysis_queries.sql` — example analyst SQL: rankings, regional averages, YoY growth, trend deltas
- `dashboard.py` — the Streamlit app itself
