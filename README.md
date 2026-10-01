# AutoRoot

**Monitor weekly sales. Investigate unusual movements. Explain the drivers.**

AutoRoot is a Python sales investigation workspace that follows the analyst workflow from a weekly alert to a reconciled explanation. It combines past-only anomaly detection, DuckDB KPI queries, segment attribution, and interactive Plotly charts in Streamlit.

The demo uses **37,440 reproducible synthetic records**, covering 104 weeks, eight regions, 15 products, and three channels. Eight labeled scenarios include a regional demand spike, supply disruption, channel outage, and a price change. All amounts are USD.

## Results

Measured on the default seed (42), across 78 monitored weeks after a 26-week clean calibration period:

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
python -m pytest -q
python -m streamlit run app.py
```

On macOS/Linux, activate with `source .venv/bin/activate`. The committed dataset and reports let the app start immediately; generation and evaluation commands rebuild them. If no dataset or reports exist, the app computes them. To refresh cached results during development, clear Streamlit's cache after rebuilding reports.

## What you can explore

- Switch between revenue and units and compare detection methods.
- Select an alert or any monitored week on the timeline.
- Read a generated investigation brief with gains and offsetting losses.
- Drill into regions, products, and channels.
- Reconcile the three leading segment cells and all remaining cells in a waterfall.
- Separate revenue changes into volume and price/mix effects.
- Inspect precision, recall, confusion counts, and the scenario ledger.
- Download a driver CSV or plain-text investigation brief.

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

## Methodology

**Rolling Z-score:** compare each value with the previous 12-week mean and standard deviation; flag absolute Z above three. The current week is excluded from its baseline. A one-percent standard deviation floor avoids division by nearly zero variation.

**Seasonal decomposition:** robust log-space regression separates trend and annual Fourier components. Each forecast fits only prior weeks using iteratively reweighted least squares. A 2.5% log-residual noise floor and an absolute score threshold of three keep small deviations from generating alerts. Unlike a centered decomposition of the full dataset, this can run as new weeks arrive. Only two annual cycles are available; seasonality estimates are uncertain early in the series.

**Isolation Forest:** fit 80 trees on prior log levels, WoW changes, and YoY changes, with contamination 0.04 and fixed random state. YoY is filled with zero before 52 weeks; this transition and evolving trend can generate false alerts. The modest precision is retained in the scorecard to show that a more complex method is not automatically more useful.

**Combined monitor:** seasonal total alerts OR agreement between rolling Z and Isolation Forest OR a seasonal marginal alert in any region, product, or channel. Marginal alerts recover events diluted in totals. Testing multiple panels raises false-alert risk; the demo does not implement formal false-discovery control.

**Attribution:** calculate expected sales for each region/product/channel cell from the previous four weeks. `delta = actual − expected`; `contribution = delta / total_gap`. Marginal views describe the same total from different dimensions and must not be added together. Negative contributions offset the net movement; shares above 100% are possible. Near-zero gaps suppress unstable percentages.

**Revenue bridge:** sum `(actual_units − expected_units) × expected_price` for volume and `actual_units × (actual_price − expected_price)` for price/mix. This reconciles exactly to the revenue gap. Attribution's four-week baseline differs from the seasonal detection forecast: a local decrease can coexist with a company-wide increase.

Sales data show **where** a change occurred, not a verified business cause. Narrative suggestions require inventory, promotion, pricing, or operational evidence before a causal claim.

## Deploy

The included Pages workflow publishes a standalone interactive demo from the Python pipeline after tests pass. It supports both metrics, all four detection methods, week selection, segment drill-down, scorecards, and downloads. It explores precomputed results and does not execute Python on the web. The Streamlit app runs the complete Python workspace.

The intended public deployment is Streamlit Community Cloud. Push the repository to GitHub, connect the account at [Streamlit Community Cloud](https://share.streamlit.io/), and create an app with branch `main` and entrypoint `app.py`. Choose Python 3.10 in advanced settings. The requirements file and theme are included. Follow the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

Deployment status and verified links belong in this README only after publishing succeeds. No live URL is claimed before that verification.

## Validation and further work

GitHub Actions rebuilds the panel, runs evaluation, tests the app and pipeline, and uploads evaluation artifacts. Tests verify that future mutations cannot change earlier scores, all attribution dimensions reconcile, the revenue bridge balances, invalid panels fail, and units labels exclude the price event.

Before operational use: validate more years of real history, reserve untouched holdout periods, test additional random seeds, tune alert budgets without viewing test labels, account for holidays and missing segments, add multiplicity controls, and review alerts with business owners. The synthetic generator intentionally provides a clean initial calibration period and one-week events; real systems rarely offer that convenience.

See [the interview notes](docs/interview_notes.md) for design tradeoffs and [the data dictionary](docs/data_dictionary.md) for the model.

MIT license.
