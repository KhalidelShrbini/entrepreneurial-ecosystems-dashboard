"""
Entrepreneurial Ecosystems Dashboard -- Fragile & Emerging Markets
Run with:  streamlit run dashboard_v4.py
"""

import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Entrepreneurial Ecosystems Dashboard", layout="wide")

PALETTE = ["#C9A227", "#4A6FA5", "#7A9E7E", "#B5654A", "#8E7CC3", "#5B8A9A", "#A65959", "#6B7A8F"]
px.defaults.color_discrete_sequence = PALETTE
LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E8E8E8", family="sans serif"),
    margin=dict(t=40, l=10, r=10, b=10),
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 600; }
    [data-testid="stMetricLabel"] { color: #9AA5B1; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
    h1 { font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0; }
    h2, h3 { letter-spacing: -0.01em; }
    .subtitle { color: #7C8896; font-size: 0.95rem; margin-top: 2px; margin-bottom: 1.5rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 8px 16px; }
    .fcs-badge {
        background: #B5654A; color: white; padding: 2px 10px; border-radius: 3px;
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .insight-item { border-left: 3px solid #C9A227; padding: 4px 0 4px 14px; margin-bottom: 10px; color: #D5DAE0; }
    .section-note { color: #7C8896; font-size: 0.88rem; margin-top: -6px; }
</style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("market_data.db")
scored = pd.read_sql("SELECT * FROM ecosystem_readiness_score", conn)
timeseries = pd.read_sql("SELECT * FROM country_timeseries", conn)
snapshot = pd.read_sql("SELECT * FROM country_snapshot", conn)

st.title("Entrepreneurial Ecosystems Dashboard")
st.markdown('<p class="subtitle">Fragile &amp; emerging markets · World Bank data, updated live</p>', unsafe_allow_html=True)

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
st.sidebar.subheader("Readiness score weights")
w_growth = st.sidebar.slider("GDP growth", 0.0, 1.0, 0.20)
w_digital = st.sidebar.slider("Digital access", 0.0, 1.0, 0.20)
w_selfemp = st.sidebar.slider("Entrepreneurial activity", 0.0, 1.0, 0.25)
w_ease = st.sidebar.slider("Business regulatory environment", 0.0, 1.0, 0.15)
w_stability = st.sidebar.slider("Price stability", 0.0, 1.0, 0.10)
w_labor = st.sidebar.slider("Labor market", 0.0, 1.0, 0.10)
st.sidebar.caption("Fragile/conflict status is a filter, not a score penalty.")


# ---------- helper: auto-generated insight bullets ----------
def build_insights(df: pd.DataFrame) -> list[str]:
    insights = []
    d = df.dropna(subset=["ecosystem_readiness_score"])
    if d.empty:
        return ["No countries match the current filters."]

    top = d.sort_values("ecosystem_readiness_score", ascending=False).iloc[0]
    insights.append(
        f"<b>{top['country_name']}</b> leads on ecosystem readiness ({top['ecosystem_readiness_score']:.3f}), "
        f"driven by a {top['self_employed_pct']:.0f}% self-employment rate and {top['gdp_growth_pct']:.1f}% GDP growth."
        if pd.notna(top['self_employed_pct']) else
        f"<b>{top['country_name']}</b> leads on ecosystem readiness at {top['ecosystem_readiness_score']:.3f}."
    )

    if d["self_employed_pct"].notna().sum() >= 5:
        se = d.dropna(subset=["self_employed_pct"]).sort_values("self_employed_pct", ascending=False).iloc[0]
        insights.append(
            f"<b>{se['country_name']}</b> has the highest measured self-employment rate in view "
            f"({se['self_employed_pct']:.0f}% of total employment) -- a strong proxy for informal entrepreneurial density."
        )

    if d["business_reg_rating"].notna().sum() >= 5:
        best = d.dropna(subset=["business_reg_rating"]).sort_values("business_reg_rating", ascending=False).iloc[0]
        worst = d.dropna(subset=["business_reg_rating"]).sort_values("business_reg_rating").iloc[0]
        insights.append(
            f"Business regulatory environment (World Bank CPIA rating, 1-6) varies sharply among IDA-eligible "
            f"countries: <b>{best['country_name']}</b> rates {best['business_reg_rating']:.1f}, versus "
            f"{worst['business_reg_rating']:.1f} in <b>{worst['country_name']}</b>."
        )

    corr_cols = ["self_employed_pct", "internet_users_pct", "gdp_growth_pct", "business_reg_rating"]
    corr_df = d[corr_cols].dropna()
    if len(corr_df) >= 8:
        c = corr_df["self_employed_pct"].corr(corr_df["internet_users_pct"])
        direction = "inversely" if c < -0.2 else ("positively" if c > 0.2 else "not strongly")
        insights.append(
            f"Self-employment and internet penetration are {direction} correlated (r={c:.2f}) across the current view -- "
            f"{'high informal entrepreneurship often coincides with lower digital access, a possible digital-skills gap' if c < -0.2 else 'digitally connected markets tend to show more formal entrepreneurial activity' if c > 0.2 else 'no clear pattern emerges from the current sample'}."
        )

    fcs_count = int(d["is_fragile_or_conflict"].sum())
    if fcs_count > 0:
        fcs_avg = d[d["is_fragile_or_conflict"] == 1]["ecosystem_readiness_score"].mean()
        nonfcs_avg = d[d["is_fragile_or_conflict"] == 0]["ecosystem_readiness_score"].mean()
        gap = nonfcs_avg - fcs_avg
        insights.append(
            f"{fcs_count} fragile/conflict-affected states are in the current view, averaging a readiness score of "
            f"{fcs_avg:.3f} versus {nonfcs_avg:.3f} elsewhere -- a gap of {gap:.3f} that reflects structural, not "
            f"opportunity-related, constraints."
        )

    return insights


def build_recommendations(df: pd.DataFrame) -> list[str]:
    d = df.dropna(subset=["ecosystem_readiness_score"])
    recs = []
    if d.empty:
        return recs

    top5 = d.sort_values("ecosystem_readiness_score", ascending=False).head(5)["country_name"].tolist()
    recs.append(f"<b>Priority shortlist:</b> {', '.join(top5)} rank highest on the composite readiness score "
                f"and warrant deeper qualitative validation (local partner capacity, safety, programme fit).")

    if d["business_reg_rating"].notna().sum() >= 5:
        reg = d.dropna(subset=["business_reg_rating"])
        weak_reg = reg[reg["business_reg_rating"] < reg["business_reg_rating"].median()]
        weak_reg_high_potential = weak_reg[
            weak_reg["self_employed_pct"] > weak_reg["self_employed_pct"].median()
        ] if weak_reg["self_employed_pct"].notna().any() else pd.DataFrame()
        if not weak_reg_high_potential.empty:
            names = weak_reg_high_potential.sort_values("ecosystem_readiness_score", ascending=False).head(3)["country_name"].tolist()
            recs.append(f"<b>Regulatory-support opportunity:</b> {', '.join(names)} combine above-median entrepreneurial "
                        f"activity with a below-median business regulatory environment rating -- a training/advocacy "
                        f"programme on formalization could unlock latent activity here.")

    fcs_count = int(d["is_fragile_or_conflict"].sum())
    if fcs_count > 0:
        recs.append(f"<b>Fragile-context track:</b> {fcs_count} FCS-classified states are represented; review the "
                    f"Fragile Contexts tab separately, since standard readiness scoring under-weights the resilience "
                    f"and adaptability factors that matter most in these markets.")

    recs.append("<b>Data caveat:</b> self-employment and business-registration-time indicators have partial "
                "country coverage. Treat rankings as a screening layer, not a final decision input -- pair with "
                "local ecosystem mapping before committing programme resources.")
    return recs


tab_exec, tab_readiness, tab_regional, tab_fragile, tab_country, tab_data = st.tabs(
    ["Executive Summary", "Market Readiness", "Regional Comparison", "Fragile Contexts", "Country Deep Dive", "Data & Methodology"]
)

# ============================== EXECUTIVE SUMMARY ==============================
with tab_exec:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Countries analyzed", f"{len(filtered):,}")
    c2.metric("Avg GDP growth", f"{filtered['gdp_growth_pct'].mean():.1f}%")
    c3.metric("Avg self-employment", f"{filtered['self_employed_pct'].mean():.1f}%" if filtered['self_employed_pct'].notna().any() else "N/A")
    c4.metric("Top readiness score", f"{filtered['ecosystem_readiness_score'].max():.3f}")
    c5.metric("Fragile/conflict states", int(filtered["is_fragile_or_conflict"].sum()))

    st.markdown("---")
    left, right = st.columns([1.1, 0.9])

    with left:
        st.subheader("Key insights")
        for point in build_insights(filtered):
            st.markdown(f'<div class="insight-item">{point}</div>', unsafe_allow_html=True)

        st.subheader("Recommendations")
        for point in build_recommendations(filtered):
            st.markdown(f'<div class="insight-item">{point}</div>', unsafe_allow_html=True)

    with right:
        st.subheader("Top 10 markets by readiness")
        top10 = filtered.sort_values("ecosystem_readiness_score", ascending=False).head(10)
        fig = px.bar(top10, x="ecosystem_readiness_score", y="country_name", orientation="h",
                      color="region", labels={"ecosystem_readiness_score": "Score", "country_name": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=420, showlegend=False, **LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("GDP per capita, by income group")
        trend = (timeseries.dropna(subset=["gdp_per_capita_usd"])
                 .groupby(["year", "income_level"], as_index=False)["gdp_per_capita_usd"].mean())
        fig2 = px.line(trend, x="year", y="gdp_per_capita_usd", color="income_level",
                        labels={"gdp_per_capita_usd": "Avg GDP per capita (US$)"})
        fig2.update_layout(height=300, **LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

# ============================== MARKET READINESS ==============================
with tab_readiness:
    st.subheader("Full readiness ranking")
    top15 = filtered.sort_values("ecosystem_readiness_score", ascending=False).head(15)
    fig3 = px.bar(top15, x="ecosystem_readiness_score", y="country_name", orientation="h",
                   color="region", text="ecosystem_readiness_score",
                   labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""})
    fig3.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, **LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Activity vs. regulatory environment quadrant")
        st.markdown('<p class="section-note">Self-employment rate (entrepreneurial activity) vs. World Bank CPIA '
                    'business regulatory environment rating. Bottom-right: high activity despite a weak regulatory '
                    'environment -- often the strongest case for policy-focused support.</p>',
                    unsafe_allow_html=True)
        qd = filtered.dropna(subset=["self_employed_pct", "business_reg_rating"])
        if not qd.empty:
            x_med, y_med = qd["business_reg_rating"].median(), qd["self_employed_pct"].median()
            fig_q = px.scatter(qd, x="business_reg_rating", y="self_employed_pct", color="region",
                                size="population", hover_name="country_name", size_max=45,
                                labels={"business_reg_rating": "Business regulatory environment (CPIA, 1-6)", "self_employed_pct": "Self-employment (%)"})
            fig_q.add_vline(x=x_med, line_dash="dot", line_color="#7C8896")
            fig_q.add_hline(y=y_med, line_dash="dot", line_color="#7C8896")
            fig_q.update_layout(height=430, **LAYOUT)
            st.plotly_chart(fig_q, use_container_width=True)
        else:
            st.info("Not enough overlapping data for this view under the current filters.")

    with col_b:
        st.subheader("Indicator correlation")
        st.markdown('<p class="section-note">How readiness-score inputs move together across the current selection.</p>',
                    unsafe_allow_html=True)
        corr_cols = {
            "gdp_growth_pct": "GDP growth", "internet_users_pct": "Internet access",
            "self_employed_pct": "Self-employment", "business_reg_rating": "Biz reg. environment",
            "inflation_pct": "Inflation", "unemployment_pct": "Unemployment",
        }
        cdf = filtered[list(corr_cols.keys())].rename(columns=corr_cols).dropna(thresh=4)
        if len(cdf) >= 8:
            corr = cdf.corr(numeric_only=True).round(2)
            fig_h = px.imshow(corr, text_auto=True, color_continuous_scale=["#B5654A", "#16202E", "#4A6FA5"],
                               zmin=-1, zmax=1)
            fig_h.update_layout(height=430, **LAYOUT)
            st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.info("Not enough overlapping data for a correlation matrix under the current filters.")

# ============================== REGIONAL COMPARISON ==============================
with tab_regional:
    st.subheader("Region-level comparison")
    metric_options = {
        "GDP growth (%)": "gdp_growth_pct", "Self-employment (%)": "self_employed_pct",
        "Internet users (%)": "internet_users_pct", "Business regulatory environment (CPIA)": "business_reg_rating",
        "Ecosystem readiness score": "ecosystem_readiness_score",
    }
    metric_label = st.selectbox("Metric", list(metric_options.keys()), index=4)
    metric_col = metric_options[metric_label]

    reg_avg = filtered.groupby("region", as_index=False)[metric_col].mean().sort_values(metric_col, ascending=False)
    fig_r = px.bar(reg_avg, x=metric_col, y="region", orientation="h", labels={metric_col: metric_label, "region": ""})
    fig_r.update_traces(marker_color=PALETTE[0])
    fig_r.update_layout(yaxis={"categoryorder": "total ascending"}, height=380, **LAYOUT)
    st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")
    st.subheader("Regional trend over time")
    ts_metric_options = {"GDP growth (%)": "gdp_growth_pct", "GDP per capita (US$)": "gdp_per_capita_usd",
                          "Internet users (%)": "internet_users_pct"}
    ts_label = st.selectbox("Trend metric", list(ts_metric_options.keys()))
    ts_col = ts_metric_options[ts_label]
    reg_trend = timeseries.dropna(subset=[ts_col]).groupby(["year", "region"], as_index=False)[ts_col].mean()
    if regions:
        reg_trend = reg_trend[reg_trend["region"].isin(regions)]
    fig_rt = px.line(reg_trend, x="year", y=ts_col, color="region", labels={ts_col: ts_label})
    fig_rt.update_layout(height=420, **LAYOUT)
    st.plotly_chart(fig_rt, use_container_width=True)

# ============================== FRAGILE CONTEXTS ==============================
with tab_fragile:
    fcs = scored[scored["is_fragile_or_conflict"] == 1]
    if regions:
        fcs = fcs[fcs["region"].isin(regions)]

    st.subheader("Fragile & conflict-affected states")
    st.markdown('<p class="section-note">World Bank FCS classification. This segment structurally scores lower on '
                'standard readiness metrics -- treat as a distinct analytical lens, not a lower-priority list.</p>',
                unsafe_allow_html=True)

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
        fig5 = px.bar(fcs.sort_values("ecosystem_readiness_score", ascending=False),
                       x="ecosystem_readiness_score", y="country_name", orientation="h", color="region",
                       labels={"ecosystem_readiness_score": "Readiness score", "country_name": ""})
        fig5.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(320, 28 * len(fcs)), **LAYOUT)
        st.plotly_chart(fig5, use_container_width=True)

# ============================== COUNTRY DEEP DIVE ==============================
with tab_country:
    country = st.selectbox("Pick a country", sorted(snapshot["country_name"].dropna().unique()))
    cdata = snapshot[snapshot["country_name"] == country].iloc[0]
    c_ts = timeseries[timeseries["country_name"] == country].sort_values("year")

    if bool(cdata.get("is_fragile_or_conflict", False)):
        st.markdown('<span class="fcs-badge">Fragile / conflict-affected</span>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GDP per capita", f"${cdata['gdp_per_capita_usd']:,.0f}" if pd.notna(cdata['gdp_per_capita_usd']) else "N/A")
    c2.metric("GDP growth", f"{cdata['gdp_growth_pct']:.1f}%" if pd.notna(cdata['gdp_growth_pct']) else "N/A")
    c3.metric("Self-employment", f"{cdata['self_employed_pct']:.1f}%" if pd.notna(cdata['self_employed_pct']) else "N/A")
    c4.metric("Business reg. environment", f"{cdata['business_reg_rating']:.1f}/6" if pd.notna(cdata['business_reg_rating']) else "N/A")

    c5, c6, c7 = st.columns(3)
    c5.metric("Internet users", f"{cdata['internet_users_pct']:.1f}%" if pd.notna(cdata['internet_users_pct']) else "N/A")
    c6.metric("Agriculture (% GDP)", f"{cdata['agriculture_pct_gdp']:.1f}%" if pd.notna(cdata['agriculture_pct_gdp']) else "N/A")
    c7.metric("Life expectancy", f"{cdata['life_expectancy']:.0f} yrs" if pd.notna(cdata['life_expectancy']) else "N/A")

    if not c_ts.empty:
        fig6 = px.line(c_ts, x="year", y="gdp_growth_pct", title=f"{country}: GDP growth over time")
        fig6.update_layout(**LAYOUT)
        st.plotly_chart(fig6, use_container_width=True)

# ============================== DATA & METHODOLOGY ==============================
with tab_data:
    st.subheader("Dataset")
    display_cols = ["country_name", "region", "income_level", "is_fragile_or_conflict",
                     "gdp_growth_pct", "gdp_per_capita_usd", "internet_users_pct", "self_employed_pct",
                     "business_reg_rating", "agriculture_pct_gdp", "poverty_headcount_pct",
                     "ecosystem_readiness_score"]
    st.dataframe(filtered[display_cols].sort_values("ecosystem_readiness_score", ascending=False),
                 use_container_width=True, height=460)

    st.markdown("---")
    st.subheader("Methodology")
    st.markdown("""
- **Source:** World Bank World Development Indicators, pulled live via the public API (`api.worldbank.org`).
- **Readiness score:** min-max normalized, weighted composite of GDP growth, internet penetration, self-employment
  rate, business regulatory environment (CPIA rating), inflation, and unemployment. Weights are adjustable in the sidebar and default
  to the values shown there. Missing indicator values are scored as neutral (0.5) rather than excluding the country.
- **FCS flag:** static reference list based on the World Bank's Fragile and Conflict-affected Situations
  classification. Verify against the current official list before use in formal reporting.
- **Limitation:** self-employment and business regulatory environment indicators have partial country coverage
  (the latter is only rated for IDA-eligible countries); rankings should be treated as a screening layer, not a
  standalone decision input.
- **Note:** an earlier version of this scoring model used the World Bank's "Doing Business" days-to-register
  metric. That report was discontinued in 2021 following an internal ethics review, so this version uses the
  actively-maintained CPIA Business Regulatory Environment rating instead.
""")
