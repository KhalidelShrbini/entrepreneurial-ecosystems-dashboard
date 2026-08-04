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

chart_html = lambda fig: pio.to_html(fig, include_plotlyjs="inline", full_html=False, config={"displaylogo": False})

# --- Assemble page ---
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Entrepreneurial Ecosystems Report</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ background:#0A0F18; color:#E8E8E8; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
          margin: 0; padding: 0; }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 0 24px 80px; }}
  header {{ background: linear-gradient(135deg, #16202E 0%, #0E1420 100%);
            border-bottom: 1px solid #263241; padding: 48px 24px 36px; margin-bottom: 8px; }}
  header .wrap {{ padding: 0 24px; }}
  h1 {{ font-weight:700; letter-spacing:-0.02em; margin: 0; font-size: 2.1rem; color: #F2F2F2; }}
  .subtitle {{ color:#8FA0B3; margin-top:8px; font-size: 1.02rem; }}
  h2 {{ margin-top:3.2rem; margin-bottom: 1.2rem; font-size: 1.3rem; font-weight: 600;
        border-bottom: 1px solid #263241; padding-bottom:10px; color: #F2F2F2; }}
  .kpi-row {{ display:flex; gap:16px; flex-wrap:wrap; margin: 28px 0 8px; }}
  .kpi {{ flex: 1 1 160px; background: #131B27; border: 1px solid #263241; border-radius: 8px;
          padding: 18px 20px; }}
  .kpi-label {{ color:#8FA0B3; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em; margin-bottom: 6px; }}
  .kpi-value {{ font-size:1.9rem; font-weight:700; color: #F2F2F2; }}
  .kpi-value.gold {{ color: #C9A227; }}
  .insight-item {{ background: #131B27; border-left:3px solid #C9A227; border-radius: 0 6px 6px 0;
                    padding:12px 16px; margin-bottom:10px; color:#D5DAE0; line-height: 1.5; }}
  .section-note {{ color:#8FA0B3; font-size:0.88rem; margin-bottom: 14px; }}
  .chart-card {{ background: #0E1420; border: 1px solid #1C2733; border-radius: 8px; padding: 8px; margin-bottom: 8px; }}
  footer {{ color:#5A6572; font-size:0.8rem; margin-top:4rem; border-top:1px solid #263241; padding-top:16px; }}
  a {{ color: #C9A227; }}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <h1>Entrepreneurial Ecosystems Report</h1>
    <p class="subtitle">Fragile &amp; emerging markets · World Bank data snapshot</p>
  </div>
</header>

<div class="wrap">

<div class="kpi-row">
  <div class="kpi"><div class="kpi-label">Countries analyzed</div><div class="kpi-value">{n_countries}</div></div>
  <div class="kpi"><div class="kpi-label">Avg GDP growth</div><div class="kpi-value">{avg_growth:.1f}%</div></div>
  <div class="kpi"><div class="kpi-label">Avg self-employment</div><div class="kpi-value">{avg_selfemp:.1f}%</div></div>
  <div class="kpi"><div class="kpi-label">Top readiness score</div><div class="kpi-value gold">{top_score:.3f}</div></div>
  <div class="kpi"><div class="kpi-label">Fragile/conflict states</div><div class="kpi-value">{fcs_count}</div></div>
</div>

<h2>Key insights</h2>
{''.join(f'<div class="insight-item">{i}</div>' for i in insights)}

<h2>Recommendation</h2>
<div class="insight-item">{recommendation}</div>

<h2>Top 15 markets by readiness score</h2>
<div class="chart-card">{chart_html(fig1)}</div>

<h2>GDP per capita over time, by income group</h2>
<div class="chart-card">{chart_html(fig2)}</div>

<h2>Entrepreneurial activity vs. business regulatory environment</h2>
<p class="section-note">Self-employment rate vs. World Bank CPIA business regulatory environment rating.</p>
<div class="chart-card">{chart_html(fig3)}</div>

<h2>Fragile &amp; conflict-affected states</h2>
<div class="chart-card">{chart_html(fig4)}</div>

<footer>
  Data: World Bank World Development Indicators (api.worldbank.org). FCS classification is a static reference
  list -- verify against the latest official World Bank list before use in formal reporting.
  Report generated from a live pull; figures reflect the most recent available year per indicator.
</footer>

</div>
</body>
</html>
"""

with open("entrepreneurial_ecosystems_report.html", "w") as f:
    f.write(html)

print("Saved entrepreneurial_ecosystems_report.html")
print("Open it by double-clicking, or drag it into a browser window.")
