# Prospective synthetic holdout

The 104-week demonstration was development data. Settings and detector hashes were frozen before this run. Five new seeds each add an unseen 52-week future period, including a two-week disruption and changed event sizes and locations. Models may learn from prior observations as weeks arrive; holdout labels never enter fitting or tuning.

Results include all methods and seeds. Intervals resample entire seeds (2,000 bootstrap samples), rather than pretending weekly observations are independent. Five synthetic worlds cannot establish performance on real data. Individual methods monitor totals; the combined method additionally monitors segments, so coverage differs. Reruns verify reproducibility, not a new untouched evaluation.
