"""
Fetches real, live data from the World Bank Open Data API (no key required).
Indicators are chosen around entrepreneurship support in fragile and low/middle-income
contexts -- ecosystem readiness, business friction, and digital/economic conditions.

Builds:
  1. wdi_snapshot_latest.csv  -> one row per country, most recent value per indicator
  2. wdi_timeseries.csv       -> country x year panel for trend charts

Run this on your own machine (needs internet):
    python fetch_data_v7.py
"""

import time
import requests
import pandas as pd

BASE = "https://api.worldbank.org/v2"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ecosystem-dashboard-script/1.0)"}

# Indicators framed around entrepreneurial ecosystem readiness in fragile / LMIC contexts
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",         # GDP growth, annual %
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",         # GDP per capita, current US$
    "SP.POP.TOTL": "population",                    # Total population
    "SP.POP.GROW": "pop_growth_pct",                 # Population growth, annual %
    "SP.URB.TOTL.IN.ZS": "urban_pop_pct",            # Urban population, % of total
    "IT.NET.USER.ZS": "internet_users_pct",          # Internet users, % of population
    "IT.CEL.SETS.P2": "mobile_subs_per100",          # Mobile subscriptions per 100 people
    "SP.DYN.LE00.IN": "life_expectancy",             # Life expectancy at birth
    "FP.CPI.TOTL.ZG": "inflation_pct",               # Inflation, consumer prices, annual %
    "SL.UEM.TOTL.ZS": "unemployment_pct",            # Unemployment, % of labor force
    "SL.EMP.SELF.ZS": "self_employed_pct",           # Self-employed, % of total employment (entrepreneurial activity proxy)
    "NV.AGR.TOTL.ZS": "agriculture_pct_gdp",         # Agriculture, value added, % of GDP (agripreneurship relevance)
    "SI.POV.DDAY": "poverty_headcount_pct",          # Poverty headcount ratio at $2.15/day, % of population
    "IQ.CPA.BREG.XQ": "business_reg_rating",         # CPIA business regulatory environment rating, 1 (low) - 6 (high); IDA-eligible countries
}

# Indicators with genuinely sparse annual reporting: widen the lookback window and
# gap-fill so a missing latest year doesn't wipe out the country.
SPARSE_INDICATORS = {"IT.NET.USER.ZS", "IQ.CPA.BREG.XQ", "SL.EMP.SELF.ZS", "SI.POV.DDAY"}

# Full time series pulled for trend charts (kept to a few indicators to keep the file small)
TREND_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "IT.NET.USER.ZS": "internet_users_pct",
}

# World Bank FY24 List of Fragile and Conflict-affected Situations (ISO3 codes).
# NOTE: this is a static snapshot compiled from public World Bank FCS classifications.
# The official list is revised annually -- verify against the latest PDF at
# worldbank.org/en/topic/fragilityconflictviolence before using this for real MEL work.
FCS_ISO3 = {
    "AFG", "BFA", "BDI", "CMR", "CAF", "TCD", "COM", "COD", "COG", "ERI",
    "ETH", "GNB", "HTI", "IRQ", "KIR", "XKX", "LBN", "LBY", "MLI", "MHL",
    "FSM", "MOZ", "MMR", "NER", "NGA", "PNG", "SOM", "SSD", "SDN", "SYR",
    "TLS", "TUV", "UKR", "VEN", "PSE", "YEM", "ZWE",
}


def fetch_json(url, retries=4, backoff=2):
    """GET a URL and parse JSON, retrying on network hiccups or empty responses."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            print(f"    (attempt {attempt}/{retries} failed: {e}, retrying...)")
            time.sleep(backoff * attempt)
    print(f"    (giving up on this request after {retries} attempts: {last_err})")
    return None


def get_country_metadata() -> pd.DataFrame:
    """Country name, region, income level, FCS flag. Drops region aggregates."""
    url = f"{BASE}/country?format=json&per_page=400"
    data = fetch_json(url)
    if not data or len(data) < 2 or data[1] is None:
        raise RuntimeError("Could not fetch country metadata after retries. Check your internet connection.")
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
            "is_fragile_or_conflict": c["id"] in FCS_ISO3,
        })
    return pd.DataFrame(rows)


def get_indicator_latest(code: str, col: str, sparse: bool = False) -> pd.DataFrame:
    """
    Most recent value per country. For well-reported indicators, mrv=1 is enough.
    For sparse indicators, pull the last 6 years with gapfill and keep the newest
    non-null observation per country -- avoids losing countries to a single missing year.
    """
    if sparse:
        url = f"{BASE}/country/all/indicator/{code}?format=json&mrv=6&gapfill=Y&per_page=2000"
    else:
        url = f"{BASE}/country/all/indicator/{code}?format=json&mrv=1&per_page=400"

    data = fetch_json(url)
    if not data or len(data) < 2 or data[1] is None:
        print(f"    (skipping {col}: no data returned)")
        return pd.DataFrame(columns=["country_code", col, f"{col}_year"])

    rows = []
    for r in data[1]:
        if r["value"] is None or not r.get("countryiso3code"):
            continue
        rows.append({"country_code": r["countryiso3code"], col: r["value"], f"{col}_year": int(r["date"])})

    if not rows:
        print(f"    (skipping {col}: all values null)")
        return pd.DataFrame(columns=["country_code", col, f"{col}_year"])

    df = pd.DataFrame(rows)
    # keep only the most recent observation per country
    df = df.sort_values(f"{col}_year", ascending=False).drop_duplicates("country_code", keep="first")
    return df


def get_indicator_timeseries(code: str, col: str, start=2000, end=2024) -> pd.DataFrame:
    url = f"{BASE}/country/all/indicator/{code}?format=json&date={start}:{end}&per_page=20000"
    data = fetch_json(url, retries=4, backoff=3)
    rows = []
    if not data or len(data) < 2 or data[1] is None:
        print(f"    (skipping {col}: no data returned)")
        return pd.DataFrame(columns=["country_code", "year", col])
    for r in data[1]:
        if r["value"] is None or not r.get("countryiso3code"):
            continue
        rows.append({"country_code": r["countryiso3code"], "year": int(r["date"]), col: r["value"]})
    return pd.DataFrame(rows)


def main():
    print("Fetching country metadata...")
    meta = get_country_metadata()
    print(f"  {meta['is_fragile_or_conflict'].sum()} countries flagged as fragile/conflict-affected")

    print("Fetching latest snapshot for each indicator...")
    snapshot = meta[["country_code"]].copy()
    for code, col in INDICATORS.items():
        print(f"  {col} ({code})")
        df = get_indicator_latest(code, col, sparse=(code in SPARSE_INDICATORS))
        snapshot = snapshot.merge(df, on="country_code", how="left")
        time.sleep(0.2)

    snapshot = meta.merge(snapshot, on="country_code", how="left")
    snapshot.to_csv("wdi_snapshot_latest.csv", index=False)
    print(f"Saved wdi_snapshot_latest.csv ({len(snapshot)} countries)")
    print(f"  internet_users_pct coverage: {snapshot['internet_users_pct'].notna().sum()} countries")

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

    print("\nDone. Next: python build_database_v4.py")


if __name__ == "__main__":
    main()
