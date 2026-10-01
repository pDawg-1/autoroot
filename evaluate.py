"""Evaluate exact week-level event detection; ground truth never enters detectors."""
from pathlib import Path
import json
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support
from detector import detect, METHODS, WARMUP
from warehouse import validate

ROOT = Path(__file__).resolve().parent

def evaluate(weekly, labels, metric):
    eligible = weekly[weekly.eligible].copy()
    relevant = labels[labels[f"injected_{metric}_delta"].abs() > 1]
    truth = eligible.week.isin(set(relevant.week))
    rows = []
    for method in METHODS:
        pred = eligible[method].astype(bool)
        p, r, f, _ = precision_recall_fscore_support(truth, pred, average="binary",zero_division=0)
        rows.append(dict(metric=metric,method=method,precision=float(p),recall=float(r),f1=float(f),true_positives=int((truth & pred).sum()),false_positives=int((~truth & pred).sum()),false_negatives=int((truth & ~pred).sum()),true_negatives=int((~truth & ~pred).sum()),eligible_weeks=len(eligible),labeled_weeks=int(truth.sum())))
    return pd.DataFrame(rows)

def run(directory=None, output=None):
    directory = Path(directory or ROOT/"data")
    output = Path(output or ROOT/"reports")
    output.mkdir(parents=True,exist_ok=True)
    sales = pd.read_csv(directory/"sales.csv",parse_dates=["week"])
    labels = pd.read_csv(directory/"ground_truth.csv",parse_dates=["week"])
    quality = validate(sales)
    metrics = []
    for metric in ["revenue", "units"]:
        weekly, evidence = detect(sales,metric)
        metrics.append(evaluate(weekly,labels,metric))
        weekly.to_csv(output/f"detections_{metric}.csv",index=False,date_format="%Y-%m-%d")
        evidence.to_csv(output/f"evidence_{metric}.csv",index=False,date_format="%Y-%m-%d")
    results = pd.concat(metrics,ignore_index=True)
    results.to_csv(output/"evaluation.csv",index=False)
    (output/"quality.json").write_text(json.dumps(quality,indent=2))
    print(results.to_string(index=False))
    return results

if __name__=="__main__":
    run()
