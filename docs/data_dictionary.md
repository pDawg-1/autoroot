# Data dictionary

## Grain and coverage

One record represents a Monday-start week, region, product, and channel. Coverage starts 2023-01-02 and ends 2024-12-23: 104 consecutive weeks × 8 regions × 15 products × 3 channels = 37,440 records. Product labels are illustrative retail SKUs, not actual brand sales. Currency is USD.

That fixed coverage describes the original development dataset. The `data/live` source extends through the most recent complete week when refreshed. Its state and report manifests identify the actual coverage, row counts, and source hash. The separate future benchmark uses 156-week panels and scores only the last 52 weeks.

| Table | Key | Attributes |
| --- | --- | --- |
| `fact_sales` | week, region, sku, channel | units (integer), revenue (USD) |
| `dim_region` | region | demand_factor |
| `dim_product` | sku | base_demand, list_price |
| `dim_channel` | channel | demand_factor, price_factor |

`kpi_weekly` aggregates units and revenue and exposes their WoW and 52-week YoY changes. First-week WoW and first-year YoY are null, preserving unavailable comparisons.

## Demand formula

```text
season = 1 + 0.14 sin(2πt/52) + 0.035 cos(4πt/52)
trend = 1 + 0.0015t
demand = SKU base × region factor × channel factor × season × trend
units = round(demand × lognormal(−0.5 × 0.06², 0.06))
revenue = units × SKU list price × channel price factor
```

The lognormal noise has approximately unit mean. Units are rounded and clamped to at least one before injections; revenue is rounded to cents. Demand parameters are visible in the dimension CSVs.

## Scenario ledger

`ground_truth.csv` is deliberately outside the four-table sales model. It records the event ID, week, affected dimension filters (`*` means all), unit/price multipliers, affected row count, and actual injected deltas. Hypotheses document the simulated scenario; they are never inputs to detection or the generated investigation brief.

Eight one-week scenarios start after the initial clean calibration period. The promotion scenario increases units while reducing price, illustrating that units and revenue move differently. The price-only event changes no units.

## Operational context

`operations.csv` is a separate operational feed at the same segment-week grain. It provides stockout days, fill rate, outage minutes, promotion discount, distribution change, temperature, and price change. Decisions read these records rather than the ground-truth ledger. The demonstration context is synthetic; a custom source can provide independently recorded facts. See [operations.md](operations.md) for ranges and ingestion rules.

## Checks

Warehouse loading rejects missing columns, nulls, duplicate grain, negative units/revenue, fractional units, nonconsecutive weeks, incomplete panels, and broken dimension references. DuckDB enforces primary and foreign keys. These checks cover this fixed synthetic panel; real transaction feeds need explicit missingness and returns policies.
