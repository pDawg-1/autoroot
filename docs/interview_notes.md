# Design decisions and interview preparation

## What problem does this solve?

A weekly sales dashboard shows a movement; an analyst still has to identify which segments explain it. AutoRoot monitors sales, detects unusual weeks, reconciles segment contributions, and produces a concise investigation brief with supporting charts.

## Why three detectors?

Rolling Z is interpretable but seasonal drift can create false alerts. Seasonal regression handles predictable changes but can miss small events in company totals. Isolation Forest can catch unusual combinations, but its false-alert count is higher here. The measured scorecard justifies combining seasonal and local monitoring instead of assuming complexity wins.

## How did you prevent leakage?

Rolling windows shift by one week. Every seasonal fit and forest training set ends before the scored week. The scenario ledger is read only for evaluation. A regression test changes future values and checks that previous outputs remain identical. This prevents temporal leakage; it does not replace testing on untouched operational data.

## Is 100% recall a production claim?

No. The old development demonstration finds eight true revenue events plus one false alert. The new frozen benchmark uses five fresh seeds and unseen future weeks: revenue recall is 85%, with six misses retained, and precision is 100% on these simulations. Units recall is 82.9%. Neither result establishes real-world generalization. Individual detectors and the combined monitor also have different monitoring coverage.

## How do you identify the root cause?

Sales-only attribution identifies associated drivers. It cannot prove a stockout, campaign, or weather effect. The brief quantifies the gap, names the largest segment drivers, shows opposing changes, and suggests records to check. Use inventory, campaign, pricing, and operations data to substantiate a business explanation.

## Why can contributions exceed 100%?

Contributions divide signed segment deltas by the net total. If one region falls by $100 and another rises by $80, the net decline is $20: the declining region contributes 500%, and the rising region offsets −400%. Those contributions still sum to 100%. Near-zero net gaps suppress percentages to avoid misleading ratios.

## Why use different detection and investigation baselines?

The seasonal forecast answers whether sales are unusual relative to expected trend and seasonality. The four-week baseline answers which segments changed relative to recent business performance. Both are labeled in the app. The West supply disruption can be a real local decline while seasonal growth raises the company total.

## What would you improve first?

The project now has future-period multi-seed evaluation, a three-signal review budget, comparison-adjusted panel thresholds, operational evidence, idempotent ingestion, and review-record exports. The next priorities are real operational labels, a credible intervention comparison, controlled handling of new products and returns, and a durable shared review system. The scheduled workflow monitors advancing synthetic data with read-only repository access.

## Project bullets after publication

Use these measured figures only for the committed default synthetic benchmark, and add repository and verified demo links before using the project on a resume:

- Built a Python sales monitoring pipeline with a frozen five-seed future benchmark over 260 held-out week observations, achieving 100% precision and 85% recall on synthetic revenue events.
- Developed validated weekly-feed ingestion and a DuckDB-backed investigation workspace with reconciled attribution, operational evidence, review queues, and explicit intervention-cost scenarios.

These notes are preparation material. Be ready to walk through the actual code, explain the false alert, and reproduce the evaluation rather than memorizing the figures.
