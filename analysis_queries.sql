-- Run these against market_data.db, e.g.:
--   sqlite3 market_data.db < analysis_queries.sql
-- or open them one at a time in the sqlite3 shell / DB Browser for SQLite.

-- 1. Top 15 emerging markets to watch, by opportunity score
SELECT country_name, region, income_level, opportunity_score,
       ROUND(gdp_growth_pct, 1) AS gdp_growth_pct,
       ROUND(internet_users_pct, 1) AS internet_pct
FROM market_opportunity_score
LIMIT 15;

-- 2. Regional averages: where is growth concentrated?
SELECT region,
       COUNT(*) AS num_countries,
       ROUND(AVG(gdp_growth_pct), 2) AS avg_gdp_growth,
       ROUND(AVG(internet_users_pct), 1) AS avg_internet_pct,
       ROUND(AVG(opportunity_score), 3) AS avg_opportunity_score
FROM market_opportunity_score
GROUP BY region
ORDER BY avg_opportunity_score DESC;

-- 3. Fastest-improving internet penetration, 2010 vs latest available year (window function)
WITH ranked AS (
    SELECT country_code, country_name, region, year, internet_users_pct,
           ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY year ASC)  AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY year DESC) AS rn_last
    FROM country_timeseries
    WHERE internet_users_pct IS NOT NULL AND year >= 2010
)
SELECT f.country_name, f.region,
       f.year AS start_year, f.internet_users_pct AS start_pct,
       l.year AS end_year, l.internet_users_pct AS end_pct,
       ROUND(l.internet_users_pct - f.internet_users_pct, 1) AS pct_point_gain
FROM ranked f
JOIN ranked l ON f.country_code = l.country_code AND l.rn_last = 1
WHERE f.rn_first = 1
ORDER BY pct_point_gain DESC
LIMIT 15;

-- 4. Income-group divide over time: avg GDP per capita by income level, by year
SELECT year, income_level, ROUND(AVG(gdp_per_capita_usd), 0) AS avg_gdp_per_capita
FROM country_timeseries
WHERE gdp_per_capita_usd IS NOT NULL
GROUP BY year, income_level
ORDER BY year, income_level;

-- 5. Year-over-year GDP growth acceleration/deceleration per country (window function: LAG)
SELECT country_name, year, gdp_growth_pct,
       LAG(gdp_growth_pct) OVER (PARTITION BY country_code ORDER BY year) AS prev_year_growth,
       ROUND(gdp_growth_pct - LAG(gdp_growth_pct) OVER (PARTITION BY country_code ORDER BY year), 2) AS yoy_change
FROM country_timeseries
WHERE country_code = 'IN'  -- swap ISO2 code, e.g. 'NG' Nigeria, 'VN' Vietnam, 'BR' Brazil
ORDER BY year;
