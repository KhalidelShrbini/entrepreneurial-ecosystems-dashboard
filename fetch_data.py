"""
Fetches real, live data from the World Bank Open Data API (no key required).
Builds:
  1. wdi_snapshot_latest.csv  -> one row per country, most recent value per indicator
  2. wdi_timeseries.csv       -> country x year panel for trend charts

Run this on your own machine (needs internet):
    python fetch_data.py
"""

import time
import requests
import pandas as pd

BASE = "https://api.worldbank.org/v2"

# Indicators chosen for a "which emerging market should we enter?" story
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",       # GDP growth, annual %
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",       # GDP per capita, current US$
    "SP.POP.TOTL": "population",                  # Total population
    "SP.POP.GROW": "pop_growth_pct",               # Population growth, annual %
    "SP.URB.TOTL.IN.ZS": "urban_pop_pct",          # Urban population, % of total
    "IT.NET.USER.ZS": "internet_users_pct",        # Internet users, % of population
    "IT.CEL.SETS.P2": "mobile_subs_per100",        # Mobile subscriptions per 100 people
    "SP.DYN.LE00.IN": "life_expectancy",           # Life expectancy at birth
    "FP.CPI.TOTL.ZG": "inflation_pct",             # Inflation, consumer prices, annual %
    "SL.UEM.TOTL.ZS": "unemployment_pct",          # Unemployment, % of labor force
    "NE.TRD.GNFS.ZS": "trade_pct_gdp",             # Trade openness, % of GDP
    "BX.KLT.DINV.WD.GD.ZS": "fdi_pct_gdp",         # FDI net inflows, % of GDP
}

# Subset of indicators to pull as a full time series (keeps the file small)
TREND_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "IT.NET.USER.ZS": "internet_users_pct",
}


def get_country_metadata() -> pd.DataFrame:
    """Country name, region, income level. Drops region aggregates (e.g. 'World', 'OECD')."""
    url = f"{BASE}/country?format=json&per_page=400"
    data = requests.get(url, timeout=30).json()
    rows = []
    for c in data[1]:
        if c["region"]["value"] == "Aggregates":
            continue
        rows.append({
            "country_code": c["id"],
            "country_name": c["name"],
            "region": c["region"]["value"],
            "income_level": c["incomeLevel"]["value"],
            "capital_city": c["capitalCity"],
            "longitude": c["longitude"],
            "latitude": c["latitude"],
        })
    return pd.DataFrame(rows)


def get_indicator_latest(code: str, col: str) -> pd.DataFrame:
    """Most recent non-null value per country for one indicator (mrv=1)."""
    url = f"{BASE}/country/all/indicator/{code}?format=json&mrv=1&per_page=400"
    data = requests.get(url, timeout=30).json()
    rows = []
    if len(data) < 2 or data[1] is None:
        return pd.DataFrame(columns=["country_code", col, f"{col}_year"])
    for r in data[1]:
        if r["value"] is None:
            continue
        rows.append({"country_code": r["country"]["id"], col: r["value"], f"{col}_year": r["date"]})
    return pd.DataFrame(rows)


def get_indicator_timeseries(code: str, col: str, start=2000, end=2024) -> pd.DataFrame:
    url = f"{BASE}/country/all/indicator/{code}?format=json&date={start}:{end}&per_page=20000"
    data = requests.get(url, timeout=60).json()
    rows = []
    if len(data) < 2 or data[1] is None:
        return pd.DataFrame(columns=["country_code", "year", col])
    for r in data[1]:
        if r["value"] is None:
            continue
        rows.append({"country_code": r["country"]["id"], "year": int(r["date"]), col: r["value"]})
    return pd.DataFrame(rows)


def main():
    print("Fetching country metadata...")
    meta = get_country_metadata()

    print("Fetching latest snapshot for each indicator...")
    snapshot = meta[["country_code"]].copy()
    for code, col in INDICATORS.items():
        print(f"  {col} ({code})")
        df = get_indicator_latest(code, col)
        snapshot = snapshot.merge(df, on="country_code", how="left")
        time.sleep(0.2)

    snapshot = meta.merge(snapshot, on="country_code", how="left")
    snapshot.to_csv("wdi_snapshot_latest.csv", index=False)
    print(f"Saved wdi_snapshot_latest.csv ({len(snapshot)} countries)")

    print("Fetching time series for trend indicators...")
    ts = None
    for code, col in TREND_INDICATORS.items():
        print(f"  {col} ({code})")
        df = get_indicator_timeseries(code, col)
        ts = df if ts is None else ts.merge(df, on=["country_code", "year"], how="outer")
        time.sleep(0.2)

    ts = ts.merge(meta, on="country_code", how="inner")
    ts.to_csv("wdi_timeseries.csv", index=False)
    print(f"Saved wdi_timeseries.csv ({len(ts)} rows)")

    print("\nDone. Next: python build_database.py")


if __name__ == "__main__":
    main()
