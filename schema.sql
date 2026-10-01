CREATE OR REPLACE TABLE dim_region (region VARCHAR PRIMARY KEY, demand_factor DOUBLE);
CREATE OR REPLACE TABLE dim_product (sku VARCHAR PRIMARY KEY, base_demand INTEGER, list_price DOUBLE);
CREATE OR REPLACE TABLE dim_channel (channel VARCHAR PRIMARY KEY, demand_factor DOUBLE, price_factor DOUBLE);
CREATE OR REPLACE TABLE fact_sales (
    week DATE NOT NULL,
    region VARCHAR REFERENCES dim_region(region),
    sku VARCHAR REFERENCES dim_product(sku),
    channel VARCHAR REFERENCES dim_channel(channel),
    units INTEGER CHECK (units >= 0),
    revenue DOUBLE CHECK (revenue >= 0),
    PRIMARY KEY (week, region, sku, channel)
);
CREATE OR REPLACE VIEW kpi_weekly AS
WITH weekly AS (
    SELECT week, SUM(revenue) AS revenue, SUM(units) AS units
    FROM fact_sales GROUP BY week
)
SELECT *,
    revenue / NULLIF(LAG(revenue) OVER (ORDER BY week), 0) - 1 AS revenue_wow,
    units / NULLIF(LAG(units) OVER (ORDER BY week), 0) - 1 AS units_wow,
    revenue / NULLIF(LAG(revenue, 52) OVER (ORDER BY week), 0) - 1 AS revenue_yoy,
    units / NULLIF(LAG(units, 52) OVER (ORDER BY week), 0) - 1 AS units_yoy
FROM weekly;
