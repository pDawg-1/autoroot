# Running and reviewing sales monitoring

## Sources

`data/sales.csv` is the original development demonstration. `data/live/sales.csv` is the latest saved synthetic feed snapshot. `simulate_feed.py` produces history through the last complete Monday-start week; `prepare_live.py` validates and appends it before rebuilding the reports. Reprocessing the same source adds zero duplicate sales records.

The CLI accepts local files and HTTPS snapshots or complete later-week batches. Remote downloads have a 30-second timeout and 30 MB cap. Required sales columns are `week,region,sku,channel,units,revenue`; dates must be Monday dates in `YYYY-MM-DD` format. Units must be nonnegative whole numbers; revenue must be finite and nonnegative. A fixed, complete region × product × channel panel is required.

```powershell
python pipeline.py --directory data/custom --output reports/custom --feed incoming/weekly-sales.csv --operations-feed incoming/operations.csv --source-kind external
```

The first load requires enough complete history to monitor; later loads can contain one or more complete subsequent weeks. Identical historical overlaps are harmless. Conflicts, missing cells, skipped weeks, non-finite values, and changing the panel universe fail. Review corrections explicitly instead of silently rewriting history. External sources are not given synthetic labels and are not automatically published.

## Operational evidence

Use one record per week/region/product/channel, with these additional fields:

| Field | Meaning / allowed range |
| --- | --- |
| `stockout_days` | 0–7 unavailable days |
| `fill_rate` | 0–1 fulfilled order share |
| `outage_minutes` | 0–10,080 minutes unavailable during a week |
| `promo_discount` | 0–1 promotional discount share |
| `store_count_change_pct` | Fractional distribution change |
| `temperature_c` | Observed temperature in Celsius |
| `price_change_pct` | Fractional price change |

Partial context is allowed only for keys present in the sales panel. Missing context never becomes an invented explanation. Context with impossible rates, duplicate keys, or unrelated segment-weeks fails before ingestion commits new sales. The supplied samples are synthetic records generated alongside the sales process, separate from the evaluation ledger.

## Reports and freshness

Reports include weekly SQL KPIs, all detector outputs, local evidence, an additive driver bridge, an intervention scenario, and a ranked review queue. `manifest.json` records the latest observed week, source hash, detector hash, configuration hash, and generation time. The Streamlit app uses saved detector results only if those hashes match; otherwise it recomputes from the selected sales panel. Uploads also compute through the Python detector.

Every Monday at 13:30 UTC, the monitoring workflow refreshes **synthetic** reports as downloadable artifacts, and the Pages workflow rebuilds and publishes the public report through the latest complete week. Both read the repository without committing changes. Pages retains its existing deployment permissions. The repository's saved feed snapshot changes only when a maintainer commits a validated update. No uploaded or external source is configured in either scheduled job.

## Analyst review

The review queue takes at most three signals for the selected week, ranked by absolute anomaly score × absolute KPI gap. The full evidence table remains accessible. These marginal signals can overlap; their monetary gaps are not independent and must not be summed.

Record one of: unreviewed, confirmed movement, dismissed alert, or needs more evidence, with a reason. Export the JSON disposition as an audit record. This demo does not pretend an ephemeral Streamlit session is a durable shared ticket system and does not silently retrain from feedback.

## Full-app hosting

Deploy `app.py` from the `main` branch on Streamlit Community Cloud using Python 3.11. The application serves interactive Python computation and CSV uploads; the Pages report serves exported investigations. Do not substitute a Pages URL for a full-app deployment claim.

A Docker deployment uses port 8501 and checks `/_stcore/health`. Container deployment is provided as an option; the local environment does not include a container engine for a build test.
