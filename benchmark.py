"""Pre-registered, forward-time, multi-seed synthetic holdout evaluation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd
from detector import detect, METHODS
from evaluate import evaluate
from generate_data import generate,scenarios

ROOT=Path(__file__).resolve().parent

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fingerprints():
    return {name:file_hash(ROOT/name) for name in ["detector.py","detector_config.json","benchmark_protocol.json"]}

def summary(results,protocol):
    rows=[]
    rng=np.random.default_rng(protocol["bootstrap_seed"])
    for (metric,method),group in results.groupby(["metric","method"],sort=False):
        tp,fp,fn,tn=[int(group[column].sum()) for column in ["true_positives","false_positives","false_negatives","true_negatives"]]
        precision=tp/(tp+fp) if tp+fp else 0.
        recall=tp/(tp+fn) if tp+fn else 0.
        counts=group[["true_positives","false_positives","false_negatives"]].to_numpy()
        boot=counts[rng.integers(0,len(counts),size=(protocol["bootstrap_resamples"],len(counts)))].sum(axis=1)
        bp=boot[:,0]/np.maximum(boot[:,0]+boot[:,1],1)
        br=boot[:,0]/np.maximum(boot[:,0]+boot[:,2],1)
        rows.append(dict(metric=metric,method=method,seeds=len(group),holdout_weeks=int(group.eligible_weeks.sum()),precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0.,precision_ci_low=float(np.quantile(bp,.025)),precision_ci_high=float(np.quantile(bp,.975)),recall_ci_low=float(np.quantile(br,.025)),recall_ci_high=float(np.quantile(br,.975)),seed_f1_mean=float(group.f1.mean()),seed_f1_std=float(group.f1.std(ddof=1)),true_positives=tp,false_positives=fp,false_negatives=fn,true_negatives=tn,false_alerts_per_52_weeks=fp/int(group.eligible_weeks.sum())*52))
    return pd.DataFrame(rows)

def run(output=None):
    output=Path(output or ROOT/"reports"/"benchmark")
    output.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/"benchmark_protocol.json").read_text())
    frozen=fingerprints()
    lock=output/"lock.json"
    if lock.exists() and json.loads(lock.read_text())["fingerprints"]!=frozen:
        raise ValueError("The tested detector/protocol changed. Define a new untouched protocol instead of retuning this holdout.")
    if not lock.exists():
        lock.write_text(json.dumps({"frozen_at":datetime.now(timezone.utc).isoformat(),"fingerprints":frozen,"protocol":protocol},indent=2),encoding="utf-8")
    results=[]
    details=[]
    for seed in protocol["holdout_seeds"]:
        sales,labels,*_=generate(seed=seed,periods=protocol["periods"],event_rules=scenarios()+protocol["future_events"])
        dates=sorted(sales.week.unique())
        start=pd.Timestamp(dates[protocol["holdout_start_index"]])
        for metric in ["revenue","units"]:
            predictions,_=detect(sales,metric)
            predictions["eligible"] &= predictions.week.ge(start)
            scored=evaluate(predictions,labels,metric)
            scored.insert(0,"seed",seed)
            results.append(scored)
            relevant=set(labels.loc[labels[f"injected_{metric}_delta"].abs()>1,"week"])
            visible=predictions[predictions.eligible].copy()
            visible["ground_truth"]=visible.week.isin(relevant)
            visible["seed"]=seed
            visible["metric"]=metric
            details.append(visible[["seed","metric","week","ground_truth"]+METHODS])
        print(f"Completed frozen holdout seed {seed}",flush=True)
    if fingerprints()!=frozen:
        raise ValueError("Detector changed during benchmark execution")
    result=pd.concat(results,ignore_index=True)
    result.to_csv(output/"per_seed.csv",index=False)
    pd.concat(details,ignore_index=True).to_csv(output/"predictions.csv",index=False,date_format="%Y-%m-%d")
    aggregate=summary(result,protocol)
    aggregate.to_csv(output/"summary.csv",index=False)
    (output/"methodology.md").write_text("# Prospective synthetic holdout\n\nThe 104-week demonstration was development data. Settings and detector hashes were frozen before this run. Five new seeds each add an unseen 52-week future period, including a two-week disruption and changed event sizes and locations. Models may learn from prior observations as weeks arrive; holdout labels never enter fitting or tuning.\n\nResults include all methods and seeds. Intervals resample entire seeds (2,000 bootstrap samples), rather than pretending weekly observations are independent. Five synthetic worlds cannot establish performance on real data. Individual methods monitor totals; the combined method additionally monitors segments, so coverage differs. Reruns verify reproducibility, not a new untouched evaluation.\n",encoding="utf-8")
    print(aggregate.to_string(index=False))
    return aggregate

if __name__=="__main__":
    run()
