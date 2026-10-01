# Prospective holdout evaluation

The original 104-week seed-42 panel was already reviewed during development. Relabeling its tail would not create an untouched test.

The new protocol freezes detector settings and source hashes, creates five fresh seeded panels with 156 weeks each, and scores only weeks 104–155 (2024-12-30 through 2025-12-22). Each forecast trains on earlier observations; online fitting may incorporate earlier holdout values but never their labels. The test injects eight future event weeks, including a two-week regional supply disruption, changed locations, and changed effect sizes. Units excludes the price-only event.

## Observed combined-monitor results

- Revenue: 34 of 40 event weeks detected, zero false alerts across 220 normal weeks; precision 100%, recall 85%, F1 91.9%.
- Units: 29 of 35 event weeks detected, zero false alerts across 225 normal weeks; precision 100%, recall 82.9%, F1 90.6%.

The missed localized events occur on 2025-03-31 (one seed) and 2025-04-07 (all five seeds), for both metrics. Conservative panel thresholds trade sensitivity to small regional changes for fewer noisy alerts. The implementation remains frozen after observing these misses.

`reports/benchmark/per_seed.csv` retains every method and seed. `predictions.csv` contains every held-out prediction. `summary.csv` pools confusion counts and reports macro F1 variation and 2,000 whole-seed bootstrap resamples. Five seeds is a small sample; intervals can collapse when all seeds have identical outcomes. They describe this simulation's variability, not uncertainty about real-world error rates.

`lock.json` records the protocol and hashes before the run. Reproduction refuses a changed detector or configuration. A rerun is a reproducibility check, not another untouched test. A future semantic detector change requires a new pre-registered set of unseen seeds and periods.

Individual detectors monitor totals; combined monitoring additionally tests marginal panels. Keep that coverage distinction visible when comparing methods. The test measures exact event weeks, not a tolerance-window score or proof of causal explanation.
