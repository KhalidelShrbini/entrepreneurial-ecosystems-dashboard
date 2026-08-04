"""
Emerging Market Entry Dashboard
Run with:  streamlit run dashboard.py
"""

import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Emerging Market Entry Dashboard", layout="wide")

conn = sqlite3.connect("market_data.db")
scored = pd.read_sql("SELECT * FROM market_opportunity_score", conn)
timeseries = pd.read_sql("SELECT * FROM country_timeseries", conn)
snapshot = pd.read_sql("SELECT * FROM country_snapshot", conn)

st.title("🌍 Emerging Market Entry Dashboard")
st.caption("Live World Bank data · Which developing markets look ready for expansion?")

# --- Sidebar filters ---
st.sidebar.header("Filters")
regions = st.sidebar.multiselect("Region", sorted(scored["region"].unique()), default=None)
income_levels = st.sidebar.multiselect("Income level", sorted(scored["income_level"].unique()), default=None)

filtered = scored.copy()
if regions:
    filtered = filtered[filtered["region"].isin(regions)]
if income_levels:
    filtered = filtered[filtered["income_level"].isin(income_levels)]

st.sidebar.markdown("---")
st.sidebar.subheader("Adjust the scoring model")
w_growth = st.sidebar.slider("Weight: GDP growth", 0.0, 1.0, 0.30)
w_digital = st.sidebar.slider("Weight: Digital access", 0.0, 1.0, 0.25)
w_pop = st.sidebar.slider("Weight: Population growth", 0.0, 1.0, 0.15)
w_stability = st.sidebar.slider("Weight: Price stability", 0.0, 1.0, 0.20)
w_labor = st.sidebar.slider("Weight: Labor market", 0.0, 1.0, 0.10)

# --- KPI row ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Countries analyzed", f"{len(filtered):,}")
col2.metric("Avg GDP growth", f"{filtered['gdp_growth_pct'].mean():.1f}%")
col3.metric("Avg internet penetration", f"{filtered['internet_users_pct'].mean():.1f}%")
col4.metric("Top opportunity score", f"{filtered['opportunity_score'].max():.3f}")

st.markdown("---")

# --- Leaderboard ---
left, right = st.columns([1, 1])
with left:
    st.subheader("Top 15 markets to watch")
    top15 = filtered.sort_values("opportunity_score", ascending=False).head(15)
    fig = px.bar(
        top15, x="opportunity_score", y="country_name", orientation="h",
        color="region", text="opportunity_score",
        labels={"opportunity_score": "Opportunity score", "country_name": ""},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Growth vs. digital readiness")
    fig2 = px.scatter(
        filtered, x="gdp_growth_pct", y="internet_users_pct",
        size="population", color="region", hover_name="country_name",
        labels={"gdp_growth_pct": "GDP growth (%)", "internet_users_pct": "Internet users (%)"},
        size_max=60,
    )
    fig2.update_layout(height=500)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- Trend: income group divide over time ---
st.subheader("GDP per capita over time, by income group")
trend = (
    timeseries.dropna(subset=["gdp_per_capita_usd"])
    .groupby(["year", "income_level"], as_index=False)["gdp_per_capita_usd"].mean()
)
fig3 = px.line(trend, x="year", y="gdp_per_capita_usd", color="income_level",
                labels={"gdp_per_capita_usd": "Avg GDP per capita (US$)"})
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# --- Country deep dive ---
st.subheader("Country deep dive")
country = st.selectbox("Pick a country", sorted(snapshot["country_name"].dropna().unique()))
cdata = snapshot[snapshot["country_name"] == country].iloc[0]
c_ts = timeseries[timeseries["country_name"] == country].sort_values("year")

c1, c2, c3, c4 = st.columns(4)
c1.metric("GDP per capita", f"${cdata['gdp_per_capita_usd']:,.0f}" if pd.notna(cdata['gdp_per_capita_usd']) else "N/A")
c2.metric("GDP growth", f"{cdata['gdp_growth_pct']:.1f}%" if pd.notna(cdata['gdp_growth_pct']) else "N/A")
c3.metric("Internet users", f"{cdata['internet_users_pct']:.1f}%" if pd.notna(cdata['internet_users_pct']) else "N/A")
c4.metric("Life expectancy", f"{cdata['life_expectancy']:.0f} yrs" if pd.notna(cdata['life_expectancy']) else "N/A")

if not c_ts.empty:
    fig4 = px.line(c_ts, x="year", y="gdp_growth_pct", title=f"{country}: GDP growth over time")
    st.plotly_chart(fig4, use_container_width=True)

st.caption("Data: World Bank World Development Indicators (api.worldbank.org). Score is illustrative, weights adjustable in the sidebar.")
