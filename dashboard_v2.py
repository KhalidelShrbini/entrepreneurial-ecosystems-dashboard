"""
Entrepreneurial Ecosystems Dashboard -- Fragile & Emerging Markets
Run with:  streamlit run dashboard_v2.py
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Entrepreneurial Ecosystems Dashboard", layout="wide")

# -- Professional color palette (navy / charcoal / gold) applied to every chart --
PALETTE = ["#C9A227", "#4A6FA5", "#7A9E7E", "#B5654A", "#8E7CC3", "#5B8A9A", "#A65959"]
px.defaults.color_discrete_sequence = PALETTE
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E8E8E8", family="sans serif"),
    margin=dict(t=30, l=10, r=10, b=10),
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 600; }
    h1, h2, h3 { letter-spacing: -0.02em; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 8px 18px; }
    .subtitle { color: #9AA5B1; font-size: 1.05rem; margin-top: -8px; }
    .fcs-badge {
        background: #B5654A; color: white; padding: 2px 10px; border-radius: 3px;
        font-size: 0.8rem; font-weight: 600; letter-spacing: 0.03em;
    }
</style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("market_data.db")
scored = pd.read_sql("SELECT * FROM ecosystem_readiness_score", conn)
timeseries = pd.read_sql("SELECT * FROM country_timeseries", conn)
snapshot = pd.read_sql("SELECT * FROM country_snapshot", conn)

st.title("Entrepreneurial Ecosystems Dashboard")
st.markdown(
    '<p class="subtitle">Fragile &amp; emerging markets · World Bank data · '
    'Built for entrepreneurship-support programme research and MEL reporting</p>',
    unsafe_allow_html=True,
)

# --- Sidebar filters ---
st.sidebar.header("Filters")
regions = st.sidebar.multiselect("Region", sorted(scored["region"].unique()))
income_levels = st.sidebar.multiselect("Income level", sorted(scored["income_level"].unique()))
fcs_only = st.sidebar.checkbox("Fragile & conflict-affected states only", value=False)

filtered = scored.copy()
if regions:
    filtered = filtered[filtered["region"].isin(regions)]
if income_levels:
    filtered = filtered[filtered["income_level"].isin(income_levels)]
if fcs_only:
    filtered = filtered[filtered["is_fragile_or_conflict"] == 1]

st.sidebar.markdown("---")
st.sidebar.subheader("Ecosystem Readiness Score weights")
w_growth = st.sidebar.slider("GDP growth", 0.0, 1.0, 0.20)
w_digital = st.sidebar.slider("Digital access", 0.0, 1.0, 0.20)
w_selfemp = st.sidebar.slider("Entrepreneurial activity (self-employment)", 0.0, 1.0, 0.25)
w_ease = st.sidebar.slider("Ease of starting a business", 0.0, 1.0, 0.15)
w_stability = st.sidebar.slider("Price stability", 0.0, 1.0, 0.10)
w_labor = st.sidebar.slider("Labor market", 0.0, 1.0, 0.10)
st.sidebar.caption("Fragile/conflict status is shown as a filter, not a score penalty -- "
                    "fragile contexts are a deliberate focus area, not a disqualifier.")

tab_overview, tab_readiness, tab_fragile, tab_country, tab_data = st.tabs(
    ["Overview", "Ecosystem Readiness", "Fragile Contexts", "Country Deep Dive", "Data Table"]
)

# ============================== OVERVIEW ==============================
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Countries analyzed", f"{len(filtered):,}")
    c2.metric("Avg GDP growth", f"{filtered['gdp_growth_pct'].mean():.1f}%")
    c3.metric("Avg self-employment rate", f"{filtered['self_employed_pct'].mean():.1f}%"
              if filtered['self_employed_pct'].notna().any() else "N/A")
    c4.metric("Fragile/conflict-affected in view", f"{int(filtered['is_fragile_or_conflict'].sum())}")

    st.markdown("---")
    left, right = st.columns([1, 1])

    with left:
        st.subheader("GDP per capita over time, by income group")
        trend = (
            timeseries.dropna(subset=["gdp_per_capita_usd"])
            .groupby(["year", "income_level"], as_index=False)["gdp_per_capita_usd"].mean()
        )
        fig = px.line(trend, x="year", y="gdp_per_capita_usd", color="income_level",
                       labels={"gdp_per_capita_usd": "Avg GDP per capita (US$)"})
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Countries by region in current view")
        region_counts = filtered["region"].value_counts().reset_index()
        region_counts.columns = ["region", "count"]
        fig2 = px.bar(region_counts, x="count", y="region", orientation="h")
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, **PLOTLY_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

# ============================== ECOSYSTEM READINESS ==============================
with tab_readiness:
    st.subheader("Top markets by Ecosystem Readiness Score")
    top15 = filtered.sort_values("ecosystem_readiness_score", ascending=False).head(15)
    fig3 = px.bar(
        top15, x="ecosystem_readiness_score", y="country_name", orientation="h",
        color="region", text="ecosystem_readiness_score",
        labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""},
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, **PLOTLY_LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("Explore relationships between indicators")
    axis_options = {
        "GDP growth (%)": "gdp_growth_pct",
        "GDP per capita (US$)": "gdp_per_capita_usd",
        "Internet users (%)": "internet_users_pct",
        "Self-employment (%)": "self_employed_pct",
        "Days to start a business": "days_to_start_business",
        "Agriculture (% of GDP)": "agriculture_pct_gdp",
        "Inflation (%)": "inflation_pct",
        "Unemployment (%)": "unemployment_pct",
    }
    ax1, ax2, ax3 = st.columns(3)
    x_label = ax1.selectbox("X axis", list(axis_options.keys()), index=0)
    y_label = ax2.selectbox("Y axis", list(axis_options.keys()), index=2)
    size_label = ax3.selectbox("Bubble size", ["Population", "None"], index=0)

    plot_df = filtered.dropna(subset=[axis_options[x_label], axis_options[y_label]])
    fig4 = px.scatter(
        plot_df, x=axis_options[x_label], y=axis_options[y_label],
        size="population" if size_label == "Population" else None,
        color="region", hover_name="country_name",
        labels={axis_options[x_label]: x_label, axis_options[y_label]: y_label},
        size_max=55,
    )
    fig4.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig4, use_container_width=True)

# ============================== FRAGILE CONTEXTS ==============================
with tab_fragile:
    fcs = scored[scored["is_fragile_or_conflict"] == 1]
    if regions:
        fcs = fcs[fcs["region"].isin(regions)]

    st.subheader("Fragile & Conflict-affected States (World Bank FCS classification)")
    st.caption(
        "One of Orange Corners' four research focus areas is entrepreneurship in fragile contexts. "
        "This view isolates World Bank-classified fragile/conflict-affected states for that lens."
    )

    if fcs.empty:
        st.info("No fragile/conflict-affected states match the current region filter.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("FCS countries in view", len(fcs))
        c2.metric("Avg poverty headcount ($2.15/day)",
                   f"{fcs['poverty_headcount_pct'].mean():.1f}%" if fcs['poverty_headcount_pct'].notna().any() else "N/A")
        c3.metric("Avg self-employment rate",
                   f"{fcs['self_employed_pct'].mean():.1f}%" if fcs['self_employed_pct'].notna().any() else "N/A")

        st.markdown("---")
        fig5 = px.bar(
            fcs.sort_values("ecosystem_readiness_score", ascending=False),
            x="ecosystem_readiness_score", y="country_name", orientation="h",
            color="region",
            labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""},
        )
        fig5.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(320, 28 * len(fcs)), **PLOTLY_LAYOUT)
        st.plotly_chart(fig5, use_container_width=True)

# ============================== COUNTRY DEEP DIVE ==============================
with tab_country:
    country = st.selectbox("Pick a country", sorted(snapshot["country_name"].dropna().unique()))
    cdata = snapshot[snapshot["country_name"] == country].iloc[0]
    c_ts = timeseries[timeseries["country_name"] == country].sort_values("year")

    if bool(cdata.get("is_fragile_or_conflict", False)):
        st.markdown('<span class="fcs-badge">FRAGILE / CONFLICT-AFFECTED</span>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GDP per capita", f"${cdata['gdp_per_capita_usd']:,.0f}" if pd.notna(cdata['gdp_per_capita_usd']) else "N/A")
    c2.metric("GDP growth", f"{cdata['gdp_growth_pct']:.1f}%" if pd.notna(cdata['gdp_growth_pct']) else "N/A")
    c3.metric("Self-employment", f"{cdata['self_employed_pct']:.1f}%" if pd.notna(cdata['self_employed_pct']) else "N/A")
    c4.metric("Days to start a business", f"{cdata['days_to_start_business']:.0f}" if pd.notna(cdata['days_to_start_business']) else "N/A")

    c5, c6, c7 = st.columns(3)
    c5.metric("Internet users", f"{cdata['internet_users_pct']:.1f}%" if pd.notna(cdata['internet_users_pct']) else "N/A")
    c6.metric("Agriculture (% GDP)", f"{cdata['agriculture_pct_gdp']:.1f}%" if pd.notna(cdata['agriculture_pct_gdp']) else "N/A")
    c7.metric("Life expectancy", f"{cdata['life_expectancy']:.0f} yrs" if pd.notna(cdata['life_expectancy']) else "N/A")

    if not c_ts.empty:
        fig6 = px.line(c_ts, x="year", y="gdp_growth_pct", title=f"{country}: GDP growth over time")
        fig6.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig6, use_container_width=True)

# ============================== DATA TABLE ==============================
with tab_data:
    st.subheader("Full dataset (sortable, searchable)")
    display_cols = [
        "country_name", "region", "income_level", "is_fragile_or_conflict",
        "gdp_growth_pct", "gdp_per_capita_usd", "internet_users_pct",
        "self_employed_pct", "days_to_start_business", "agriculture_pct_gdp",
        "poverty_headcount_pct", "ecosystem_readiness_score",
    ]
    st.dataframe(
        filtered[display_cols].sort_values("ecosystem_readiness_score", ascending=False),
        use_container_width=True,
        height=560,
    )
    st.caption(
        "Data: World Bank World Development Indicators (api.worldbank.org). "
        "FCS classification is a static reference list -- verify against the latest official "
        "World Bank list before use in reporting. Score weights are adjustable in the sidebar."
    )
