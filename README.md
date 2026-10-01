# AutoRoot

**Monitor weekly sales. Investigate unusual movements. Explain the drivers.**

[**Open the live demo**](https://pdawg-1.github.io/autoroot/) · [Source repository](https://github.com/pDawg-1/autoroot) · [Pipeline checks](https://github.com/pDawg-1/autoroot/actions/workflows/verify.yml)

AutoRoot is a Python sales investigation workspace that follows the analyst workflow from a weekly alert to a reconciled explanation. It combines past-only anomaly detection, DuckDB KPI queries, segment attribution, and interactive Plotly charts in Streamlit.

The original development panel has **37,440 reproducible synthetic records** across 104 weeks, eight regions, 15 products, and three channels. An advancing synthetic feed extends coverage through the last complete week. The full app also accepts uploaded sales and optional operational-context CSVs and computes their results in Python. All amounts are USD.

## Results

The existing demonstration was already inspected and is **development data**. A prospective holdout adds 52 unseen future weeks in each of five fresh seeds, using changed event locations and sizes and a two-week supply disruption. Configuration and detector hashes were frozen before testing; each prediction fits only earlier observations.

| Holdout metric | Precision | Recall | F1 | True alerts | False alerts | Missed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Revenue, combined + segments | **100.0%** | **85.0%** | **91.9%** | 34 | 0 | 6 |
| Units, combined + segments | **100.0%** | **82.9%** | **90.6%** | 29 | 0 | 6 |

Each metric covers 260 held-out week observations. The misses concentrate in the small localized supply disruption, especially its second week. No threshold was retuned after viewing these results. Whole-seed bootstrap intervals, every method/seed, every prediction, and the frozen protocol are in [reports/benchmark](reports/benchmark). Zero observed false alerts is not a guarantee of zero future errors; bootstrap intervals can be degenerate when all five seeds behave identically.

For comparison, the **development** seed (42) scores below cover 78 monitored weeks after a 26-week clean history period:

| Metric | Monitor | Precision | Recall | F1 | True alerts | False alerts |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Revenue | Rolling Z-score | 50.0% | 37.5% | 42.9% | 3 | 3 |
| Revenue | Seasonal decomposition | 100.0% | 50.0% | 66.7% | 4 | 0 |
| Revenue | Isolation Forest | 33.3% | 62.5% | 43.5% | 5 | 10 |
| Revenue | Combined + segments | **88.9%** | **100.0%** | **94.1%** | **8** | **1** |
| Units | Combined + segments | **87.5%** | **100.0%** | **93.3%** | **7** | **1** |

The price-only scenario is excluded from units ground truth because it changes revenue without changing demand. Scores measure exact event weeks, with no tolerance window. They demonstrate behavior on a controlled dataset; they do not establish performance on real sales data. Combined monitoring includes segment tests while the individual rows measure company totals, so the coverage comparison is not an equal-budget model benchmark.

Full confusion counts are in [reports/evaluation.csv](reports/evaluation.csv). The scenario ledger is in [data/ground_truth.csv](data/ground_truth.csv). Labels never enter the detection functions.

## Run locally

Use Python 3.10 or 3.11. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python generate_data.py
python evaluate.py
python pipeline.py
python prepare_live.py
python -m pytest -q
python -m streamlit run app.py
```

On macOS/Linux, activate with `source .venv/bin/activate`. The committed dataset and reports let the app start immediately; generation and evaluation commands rebuild them. If no dataset or reports exist, the app computes them. To refresh cached results during development, clear Streamlit's cache after rebuilding reports.

On Windows, `./run_local.ps1` starts the app using the project's environment, a system Python, or the local portable runtime when present. The portable runtime is a local convenience and is not included in the repository; cloned copies need the setup above.

Run `python benchmark.py` to reproduce the frozen future-period evaluation. A rerun verifies reproducibility; it is not a new untouched evaluation. If detector settings change, the fingerprint check rejects reuse of this holdout protocol.

## Feed ingestion

The Streamlit sidebar offers the original demo, the latest monitored synthetic feed, and a sales CSV upload. Uploads are validated and computed for the session, with no assumed outcome labels. The upload view includes sample sales and operational-context downloads.

For persistent local ingestion, supply a local CSV or HTTPS source:

```powershell
python pipeline.py --directory data/custom --output reports/custom --feed path/to/sales.csv --source-kind external
```

Add `--operations-feed path/to/operations.csv` for independent business evidence. Complete history is required for a new store; subsequent runs can append complete later weeks. Identical overlaps are skipped, conflicting records fail, and incomplete weeks cannot enter the validated store. Sales snapshots are replaced atomically after validation. Historical corrections and a changed segment universe require explicit data review. At least 27 complete weeks are needed to produce monitored results.

HTTPS feeds are limited to 30 MB and have a 30-second timeout. The CLI does not assume that unlabeled external weeks are normal and does not publish an external feed to the public demo. See [the operations guide](docs/operations.md).

## What you can explore

- Switch between revenue and units and compare detection methods.
- Select an alert or any monitored week on the timeline.
- Read a generated investigation brief with gains and offsetting losses.
- Drill into regions, products, and channels.
- Reconcile the three leading segment cells and all remaining cells in a waterfall.
- Separate revenue changes into volume and price/mix effects.
- Inspect precision, recall, confusion counts, and the scenario ledger.
- Download a driver CSV or plain-text investigation brief.
- Upload another sales panel and optional inventory, pricing, and availability evidence.
- Explore a proposed action's recovery rate, contribution margin, cost, and break-even point.
- Review a bounded signal queue and export an analyst disposition record.

## Pipeline

```text
Seeded sales generator → quality checks → DuckDB star schema
                                             ↓
                              weekly and segment monitoring
                                             ↓
                    four-week attribution + revenue bridge
                                             ↓
                       Streamlit investigation + exports

Separate scenario ledger → evaluation only → measured reports

Validated new-week feed → idempotent append → monitoring → decision brief
Operational records ────────────────────────────────────→ evidence
```

| File | Responsibility |
| --- | --- |
| `generate_data.py` | Sales panel, dimensions, and eight scenario injections |
| `schema.sql` | One fact table, three dimensions, weekly WoW/YoY view |
| `warehouse.py` | Fail-fast quality checks and DuckDB loading |
| `detector.py` | Causal rolling, seasonal, forest, and segment monitoring |
| `root_cause.py` | Signed contribution attribution and volume/price bridge |
| `evaluate.py` | Label-based precision, recall, F1, and confusion counts |
| `charts.py` | Timeline and additive waterfall |
| `app.py` | Interactive investigation workspace |
| `pipeline.py` | Batch monitoring with per-alert narrative and chart exports |
| `export_demo.py` | Public interactive report built from Python results |
| `tests/` | Reconciliation, leakage, quality, SQL, and app checks |
| `ingestion.py` | CSV/HTTPS loading, validation, conflict detection, atomic snapshots |
| `simulate_feed.py`, `prepare_live.py` | Advancing synthetic source and monitored feed refresh |
| `decision.py` | Independent operational evidence and intervention economics |
| `benchmark.py` | Frozen five-seed future evaluation and seed-bootstrap intervals |
| `review_queue.py` | Three-signal weekly review budget without hiding evidence |

## Methodology

**Rolling Z-score:** compare each value with the previous 12-week mean and standard deviation; flag absolute Z above three. The current week is excluded from its baseline. A one-percent standard deviation floor avoids division by nearly zero variation.

**Seasonal decomposition:** robust log-space regression separates trend and annual Fourier components. Each forecast fits only prior weeks using iteratively reweighted least squares. A 2.5% log-residual noise floor and an absolute score threshold of three keep small deviations from generating alerts. Unlike a centered decomposition of the full dataset, this can run as new weeks arrive. Only two annual cycles are available; seasonality estimates are uncertain early in the series.

**Isolation Forest:** fit 80 trees on prior log levels, WoW changes, and YoY changes, with contamination 0.04 and fixed random state. YoY is filled with zero before 52 weeks; this transition and evolving trend can generate false alerts. The modest precision is retained in the scorecard to show that a more complex method is not automatically more useful.

**Combined monitor:** seasonal total alerts OR agreement between rolling Z and Isolation Forest OR a seasonal marginal alert in any region, product, or channel. Marginal thresholds increase with the number of panels: `max(3, normal_quantile(1 − 0.01 / (2 × panels)))`, about 3.55 for 26 panels. This conservative adjustment limits noisy local alerts, but robust seasonal scores are approximate rather than calibrated p-values, so formal family-wise error control is not claimed. Thresholds and the three-signal review budget are versioned in `detector_config.json`.

**Attribution:** calculate expected sales for each region/product/channel cell from the previous four weeks. `delta = actual − expected`; `contribution = delta / total_gap`. Marginal views describe the same total from different dimensions and must not be added together. Negative contributions offset the net movement; shares above 100% are possible. Near-zero gaps suppress unstable percentages.

**Revenue bridge:** sum `(actual_units − expected_units) × expected_price` for volume and `actual_units × (actual_price − expected_price)` for price/mix. This reconciles exactly to the revenue gap. Attribution's four-week baseline differs from the seasonal detection forecast: a local decrease can coexist with a company-wide increase.

Sales data show **where** a change occurred, not a verified business cause. Narrative suggestions require inventory, promotion, pricing, or operational evidence before a causal claim.

Operational context is a separate feed, not the ground-truth ledger. Supported records include stockout days, fill rate, outage minutes, promotion discounts, store-count changes, temperature, and price changes. Decisions name an owner and a success measure. The value calculator reports potential recovery and contribution margin after intervention cost, rather than fabricated realized gains. The [West availability case](docs/business_case.md) demonstrates an intervention that does **not** pay back at the default cost.

## Deploy

The included Pages workflow publishes a standalone interactive demo from the Python pipeline after tests pass. It supports both metrics, all four detection methods, week selection, segment drill-down, scorecards, and downloads. It explores precomputed results and does not execute Python on the web. The Streamlit app runs the complete Python workspace.

The full workspace can run on Streamlit Community Cloud. Connect the account at [Streamlit Community Cloud](https://share.streamlit.io/) and create an app from `pDawg-1/autoroot`, branch `main`, entrypoint `app.py`, using Python 3.11. The requirements file and theme are included. Follow the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). A Dockerfile and health check are also included for other Python hosts.

The [public demo](https://pdawg-1.github.io/autoroot/) is deployed on GitHub Pages. Its HTML and bundled chart library were verified to return HTTP 200. The Pages workflow runs pipeline tests and exported-demo control checks before deployment.

## Validation and further work

Weekly monitoring and public report refresh are scheduled every Monday at 13:30 UTC, with manual run options in GitHub Actions. They generate an advancing synthetic source through the previous complete Monday-start week, validate new records against the stored snapshot, and export investigation briefs, charts, decision estimates, and review queues. The Pages workflow publishes the refreshed report using its existing deployment permissions; neither workflow commits data. Uploaded and external sources are excluded from scheduled publishing. The repository's saved feed snapshot advances through maintainer commits. Run `python prepare_live.py` locally for the same feed refresh.

GitHub Actions rebuilds the panel, runs evaluation, tests the app and pipeline, and uploads evaluation artifacts. Tests verify that future mutations cannot change earlier scores, all attribution dimensions reconcile, the revenue bridge balances, invalid panels fail, and units labels exclude the price event.

Remaining scope: all business data are synthetic, and estimated intervention value is not a realized outcome. The new holdout covers five seeded future worlds, not real-data generalization. Initial warmup weeks are excluded, YoY is unavailable during the first year, and the strict panel model requires controlled handling of new products, returns, missingness, and structural changes. Use operational labels and controlled comparisons before relying on the decisions in a business setting.

See [the interview notes](docs/interview_notes.md) for design tradeoffs and [the data dictionary](docs/data_dictionary.md) for the model.

MIT license.
