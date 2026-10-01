"""Ingest weekly sales, monitor changes, and export evidence-backed decisions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import pandas as pd
from charts import timeline,waterfall
from decision import recommend,validate_operations
from detector import detect
from evaluate import evaluate
from generate_data import generate
from ingestion import ingest
from warehouse import validate,build_warehouse
from root_cause import investigate
from review_queue import queue

ROOT=Path(__file__).resolve().parent

def pipeline(directory=None,output=None,feed=None,operations_feed=None,source_kind="synthetic"):
    directory=Path(directory or ROOT/"data")
    output=Path(output or ROOT/"reports")
    output.mkdir(parents=True,exist_ok=True)
    if feed is not None:
        sales,state=ingest(feed,directory,source_kind,operations_feed)
        print(json.dumps(state),flush=True)
    elif not (directory/"sales.csv").exists():
        generate(output=directory)
    sales=pd.read_csv(directory/"sales.csv",parse_dates=["week"])
    quality=validate(sales)
    if quality["weeks"]<27:
        raise ValueError("Monitoring needs at least 27 complete weeks")
    with build_warehouse(directory) as conn:
        conn.sql("SELECT * FROM kpi_weekly ORDER BY week").df().to_csv(output/"kpi_weekly.csv",index=False,date_format="%Y-%m-%d")
    labels=None
    if source_kind=="synthetic" and (directory/"ground_truth.csv").exists():
        labels=pd.read_csv(directory/"ground_truth.csv",parse_dates=["week"])
    operations=None
    if (directory/"operations.csv").exists():
        operations=validate_operations(pd.read_csv(directory/"operations.csv",parse_dates=["week"]),sales)
    summaries=[]
    metrics=[]
    for metric in ["revenue","units"]:
        weekly,evidence=detect(sales,metric)
        weekly.to_csv(output/f"detections_{metric}.csv",index=False,date_format="%Y-%m-%d")
        evidence.to_csv(output/f"evidence_{metric}.csv",index=False,date_format="%Y-%m-%d")
        if labels is not None:
            metrics.append(evaluate(weekly,labels,metric))
        for week in weekly.loc[weekly.ensemble,"week"]:
            result=investigate(sales,week,metric)
            action=recommend(result,operations)
            stem=f"{metric}-{week:%Y-%m-%d}"
            queue(evidence,week).to_csv(output/f"{stem}-review-queue.csv",index=False,date_format="%Y-%m-%d")
            brief=f"# {metric.title()} investigation · {week:%Y-%m-%d}\n\n{result['narrative']}\n\n## Decision\n\n**{action['issue']}** · Owner: {action['owner']}\n\n{action['action']}\n\nSuccess measure: {action['success_measure']}\n\nExposed revenue: ${action['exposed_revenue']:,.0f}. Scenario value after intervention cost: ${action['net_value']:,.0f}. Assumptions: {action['recovery_rate']:.0%} recovery, {action['margin_rate']:.0%} contribution margin, ${action['cost']:,.0f} cost. Potential value is not a realized outcome.\n\n"
            brief+="\n".join(f"- {line}" for line in action["evidence"])
            brief+=f"\n\nSource type: {source_kind}. Attribution baseline: prior four-week average. Operational evidence supports an investigation; it does not establish a causal treatment effect.\n"
            (output/f"{stem}.md").write_text(brief,encoding="utf-8")
            timeline(weekly,metric,"ensemble",week).write_html(output/f"{stem}-timeline.html",include_plotlyjs="directory")
            waterfall(result).write_html(output/f"{stem}-drivers.html",include_plotlyjs="directory")
            summaries.append({"metric":metric,"week":week,"actual":result["actual"],"expected":result["expected"],"gap":result["gap"],"narrative":result["narrative"],"issue":action["issue"],"owner":action["owner"],"action":action["action"],"exposed_revenue":action["exposed_revenue"],"scenario_net_value":action["net_value"]})
    pd.DataFrame(summaries,columns=["metric","week","actual","expected","gap","narrative","issue","owner","action","exposed_revenue","scenario_net_value"]).to_csv(output/"investigations.csv",index=False,date_format="%Y-%m-%d")
    if metrics:
        pd.concat(metrics,ignore_index=True).to_csv(output/"evaluation.csv",index=False)
    else:
        (output/"evaluation.csv").unlink(missing_ok=True)
    (output/"quality.json").write_text(json.dumps(quality,indent=2))
    manifest={"generated_at":datetime.now(timezone.utc).isoformat(),"source_kind":source_kind,"last_week":sales.week.max().strftime("%Y-%m-%d"),"sales_sha256":hashlib.sha256((directory/"sales.csv").read_bytes()).hexdigest(),"detector_sha256":hashlib.sha256((ROOT/"detector.py").read_bytes()).hexdigest(),"config_sha256":hashlib.sha256((ROOT/"detector_config.json").read_bytes()).hexdigest(),"labels_available":labels is not None,"operational_context":operations is not None,"quality":quality}
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Exported {len(summaries)} investigations with decision briefs.")
    return manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--feed")
    parser.add_argument("--operations-feed")
    parser.add_argument("--source-kind",choices=["synthetic","external"],default="synthetic")
    args=parser.parse_args()
    pipeline(args.directory,args.output,args.feed,args.operations_feed,args.source_kind)

if __name__=="__main__":
    main()
