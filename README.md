# Entrepreneurial Ecosystems Dashboard

An interactive dashboard analyzing entrepreneurial ecosystem readiness across fragile and emerging
markets, built on live World Bank data.

**Live app:** https://entrepreneurial-ecosystems-dashboard.streamlit.app

## Overview

The dashboard scores countries on a composite Ecosystem Readiness Score, weighing GDP growth, digital
access, self-employment rate (a proxy for entrepreneurial activity), business regulatory environment,
price stability, and labor market conditions. It includes a dedicated view for World Bank-classified
Fragile and Conflict-affected States, regional comparisons, and a country-level deep dive.

Insights and recommendations on the Executive Summary tab are generated programmatically from the
underlying data, not hardcoded, so they update as the filters and score weights change.

## Stack

- **Data:** World Bank Open Data API (`requests`, `pandas`), pulled live, no key required
- **Modeling:** SQLite with SQL views, CTEs, and window functions (`LAG`, `ROW_NUMBER`) for the scoring logic
- **Visualization:** Streamlit + Plotly (choropleth map, treemap, correlation heatmap, quadrant analysis)

## Files

- `fetch_data_v7.py` -- pulls 14 World Bank indicators (GDP growth, self-employment, business regulatory
  rating, agriculture share of GDP, etc.) for every country, with gap-filling for sparsely-reported indicators
- `build_database_v4.py` -- loads data into SQLite, builds the `ecosystem_readiness_score` SQL view
- `analysis_queries.sql` -- SQL queries: rankings, regional averages, year-over-year growth, trend deltas
- `dashboard_v4.py` -- the Streamlit app
- `export_html_report_v2.py` -- generates a standalone, self-contained HTML report for offline sharing

## Running it locally

```bash
cd market_dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python fetch_data_v7.py
python build_database_v4.py
streamlit run dashboard_v4.py
```

Opens at `http://localhost:8501`.

## Exploring the SQL

```bash
sqlite3 market_data.db
.schema ecosystem_readiness_score
```

Or run the example analyst queries directly:

```bash
sqlite3 market_data.db < analysis_queries.sql
```

## Notes

- The Fragile and Conflict-affected States classification is a static reference list; verify against
  the current official World Bank list before use in formal reporting.
- Business regulatory environment data (CPIA rating) is only available for IDA-eligible countries.
- The World Bank's "Doing Business" report, an earlier source for business-friction indicators, was
  discontinued in 2021 following an internal ethics review. This project uses the CPIA Business
  Regulatory Environment rating instead, which is still actively maintained.
# redeploy
