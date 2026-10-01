# Design decisions and interview preparation

## What problem does this solve?

A weekly sales dashboard shows a movement; an analyst still has to identify which segments explain it. AutoRoot monitors sales, detects unusual weeks, reconciles segment contributions, and produces a concise investigation brief with supporting charts.

## Why three detectors?

Rolling Z is interpretable but seasonal drift can create false alerts. Seasonal regression handles predictable changes but can miss small events in company totals. Isolation Forest can catch unusual combinations, but its false-alert count is higher here. The measured scorecard justifies combining seasonal and local monitoring instead of assuming complexity wins.

## How did you prevent leakage?

Rolling windows shift by one week. Every seasonal fit and forest training set ends before the scored week. The scenario ledger is read only for evaluation. A regression test changes future values and checks that previous outputs remain identical. This prevents temporal leakage; it does not replace testing on untouched operational data.

## Is 100% recall a production claim?

No. The default synthetic panel contains eight known, one-week revenue events and a clean calibration period. Combined monitoring finds eight true events plus one false alert across 78 eligible weeks. Units has seven relevant events. Additional seeds and real holdout data are required to establish generalization. Individual detectors and the combined monitor have different monitoring coverage.

## How do you identify the root cause?

Sales-only attribution identifies associated drivers. It cannot prove a stockout, campaign, or weather effect. The brief quantifies the gap, names the largest segment drivers, shows opposing changes, and suggests records to check. Use inventory, campaign, pricing, and operations data to substantiate a business explanation.

## Why can contributions exceed 100%?

Contributions divide signed segment deltas by the net total. If one region falls by $100 and another rises by $80, the net decline is $20: the declining region contributes 500%, and the rising region offsets −400%. Those contributions still sum to 100%. Near-zero net gaps suppress percentages to avoid misleading ratios.

## Why use different detection and investigation baselines?

The seasonal forecast answers whether sales are unusual relative to expected trend and seasonality. The four-week baseline answers which segments changed relative to recent business performance. Both are labeled in the app. The West supply disruption can be a real local decline while seasonal growth raises the company total.

## What would you improve first?

Obtain more history, define an acceptable weekly alert budget, test on an untouched time period, control multiple testing, and incorporate holiday, promotion, inventory, and pricing features. Then add scheduled ingestion, analyst feedback, and persistent alert history.

## Project bullets after publication

Use these measured figures only for the committed default synthetic benchmark, and add repository and verified demo links before using the project on a resume:

- Built a Python sales monitoring pipeline over 37,440 records, combining statistical detection and segment monitoring to identify eight injected revenue events at 88.9% precision and 100% recall.
- Developed a DuckDB-backed investigation workspace with reconciled region/product/channel attribution, volume–price decomposition, interactive Plotly charts, and downloadable narrative reports.

These notes are preparation material. Be ready to walk through the actual code, explain the false alert, and reproduce the evaluation rather than memorizing the figures.
