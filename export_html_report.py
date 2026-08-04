"""
Exports a standalone HTML report from market_data.db -- a single file with
interactive charts (hover/zoom/legend toggle) that opens in any browser,
no Streamlit server required.

Run after build_database_v4.py:
    python export_html_report.py

Output: entrepreneurial_ecosystems_report.html
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.io as pio

PALETTE = ["#C9A227", "#4A6FA5", "#7A9E7E", "#B5654A", "#8E7CC3", "#5B8A9A", "#A65959", "#6B7A8F"]
px.defaults.color_discrete_sequence = PALETTE
LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E8E8E8", family="sans serif"),
    margin=dict(t=40, l=10, r=10, b=10),
)

conn = sqlite3.connect("market_data.db")
scored = pd.read_sql("SELECT * FROM ecosystem_readiness_score", conn)
timeseries = pd.read_sql("SELECT * FROM country_timeseries", conn)
conn.close()

d = scored.dropna(subset=["ecosystem_readiness_score"])

# --- KPIs ---
n_countries = len(d)
avg_growth = d["gdp_growth_pct"].mean()
avg_selfemp = d["self_employed_pct"].mean()
top_score = d["ecosystem_readiness_score"].max()
fcs_count = int(d["is_fragile_or_conflict"].sum())

# --- Insights (same logic as the live dashboard) ---
insights = []
top = d.sort_values("ecosystem_readiness_score", ascending=False).iloc[0]
insights.append(f"<b>{top['country_name']}</b> leads on ecosystem readiness ({top['ecosystem_readiness_score']:.3f}).")

if d["self_employed_pct"].notna().sum() >= 5:
    se = d.dropna(subset=["self_employed_pct"]).sort_values("self_employed_pct", ascending=False).iloc[0]
    insights.append(f"<b>{se['country_name']}</b> has the highest measured self-employment rate "
                     f"({se['self_employed_pct']:.0f}% of total employment).")

if fcs_count > 0:
    fcs_avg = d[d["is_fragile_or_conflict"] == 1]["ecosystem_readiness_score"].mean()
    nonfcs_avg = d[d["is_fragile_or_conflict"] == 0]["ecosystem_readiness_score"].mean()
    insights.append(f"{fcs_count} fragile/conflict-affected states are in the dataset, averaging a readiness "
                     f"score of {fcs_avg:.3f} versus {nonfcs_avg:.3f} elsewhere.")

top5 = d.sort_values("ecosystem_readiness_score", ascending=False).head(5)["country_name"].tolist()
recommendation = (f"<b>Priority shortlist:</b> {', '.join(top5)} rank highest on the composite readiness score "
                   f"and warrant deeper qualitative validation before programme resourcing decisions.")

# --- Charts ---
top15 = d.sort_values("ecosystem_readiness_score", ascending=False).head(15)
fig1 = px.bar(top15, x="ecosystem_readiness_score", y="country_name", orientation="h",
              color="region", text="ecosystem_readiness_score",
              labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""})
fig1.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, **LAYOUT)

trend = (timeseries.dropna(subset=["gdp_per_capita_usd"])
         .groupby(["year", "income_level"], as_index=False)["gdp_per_capita_usd"].mean())
fig2 = px.line(trend, x="year", y="gdp_per_capita_usd", color="income_level",
               labels={"gdp_per_capita_usd": "Avg GDP per capita (US$)"})
fig2.update_layout(height=380, **LAYOUT)

qd = d.dropna(subset=["self_employed_pct", "business_reg_rating"])
fig3 = px.scatter(qd, x="business_reg_rating", y="self_employed_pct", color="region",
                   size="population", hover_name="country_name", size_max=45,
                   labels={"business_reg_rating": "Business regulatory environment (CPIA, 1-6)",
                           "self_employed_pct": "Self-employment (%)"})
fig3.update_layout(height=420, **LAYOUT)

fcs = d[d["is_fragile_or_conflict"] == 1].sort_values("ecosystem_readiness_score", ascending=False)
fig4 = px.bar(fcs, x="ecosystem_readiness_score", y="country_name", orientation="h", color="region",
              labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""})
fig4.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(320, 28 * len(fcs)), **LAYOUT)

chart_html = lambda fig: pio.to_html(fig, include_plotlyjs="cdn", full_html=False, config={"displaylogo": False})

# --- Assemble page ---
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Entrepreneurial Ecosystems Report</title>
<style>
  body {{ background:#0E1420; color:#E8E8E8; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
          max-width: 980px; margin: 0 auto; padding: 40px 24px 80px; }}
  h1 {{ font-weight:700; letter-spacing:-0.02em; margin-bottom:0; }}
  .subtitle {{ color:#7C8896; margin-top:4px; margin-bottom:2rem; }}
  h2 {{ margin-top:3rem; border-bottom: 1px solid #263241; padding-bottom:8px; }}
  .kpi-row {{ display:flex; gap:32px; flex-wrap:wrap; margin: 20px 0 10px; }}
  .kpi {{ min-width:150px; }}
  .kpi-label {{ color:#9AA5B1; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.04em; }}
  .kpi-value {{ font-size:1.7rem; font-weight:600; }}
  .insight-item {{ border-left:3px solid #C9A227; padding:4px 0 4px 14px; margin-bottom:10px; color:#D5DAE0; }}
  .section-note {{ color:#7C8896; font-size:0.88rem; }}
  footer {{ color:#5A6572; font-size:0.8rem; margin-top:4rem; border-top:1px solid #263241; padding-top:16px; }}
</style>
</head>
<body>

<h1>Entrepreneurial Ecosystems Report</h1>
<p class="subtitle">Fragile &amp; emerging markets · World Bank data snapshot</p>

<div class="kpi-row">
  <div class="kpi"><div class="kpi-label">Countries analyzed</div><div class="kpi-value">{n_countries}</div></div>
  <div class="kpi"><div class="kpi-label">Avg GDP growth</div><div class="kpi-value">{avg_growth:.1f}%</div></div>
  <div class="kpi"><div class="kpi-label">Avg self-employment</div><div class="kpi-value">{avg_selfemp:.1f}%</div></div>
  <div class="kpi"><div class="kpi-label">Top readiness score</div><div class="kpi-value">{top_score:.3f}</div></div>
  <div class="kpi"><div class="kpi-label">Fragile/conflict states</div><div class="kpi-value">{fcs_count}</div></div>
</div>

<h2>Key insights</h2>
{''.join(f'<div class="insight-item">{i}</div>' for i in insights)}

<h2>Recommendation</h2>
<div class="insight-item">{recommendation}</div>

<h2>Top 15 markets by readiness score</h2>
{chart_html(fig1)}

<h2>GDP per capita over time, by income group</h2>
{chart_html(fig2)}

<h2>Entrepreneurial activity vs. business regulatory environment</h2>
<p class="section-note">Self-employment rate vs. World Bank CPIA business regulatory environment rating.</p>
{chart_html(fig3)}

<h2>Fragile &amp; conflict-affected states</h2>
{chart_html(fig4)}

<footer>
  Data: World Bank World Development Indicators (api.worldbank.org). FCS classification is a static reference
  list -- verify against the latest official World Bank list before use in formal reporting.
  Report generated from a live pull; figures reflect the most recent available year per indicator.
</footer>

</body>
</html>
"""

with open("entrepreneurial_ecosystems_report.html", "w") as f:
    f.write(html)

print("Saved entrepreneurial_ecosystems_report.html")
print("Open it by double-clicking, or drag it into a browser window.")
