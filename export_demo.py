"""Export a standalone interactive report from the Python analytics pipeline."""
from pathlib import Path
import json
import pandas as pd
import plotly.offline
from root_cause import investigate
from decision import recommend
import argparse

ROOT = Path(__file__).resolve().parent

def export(output=None,directory=None,reports=None):
    output = Path(output or ROOT/"site")
    output.mkdir(parents=True,exist_ok=True)
    directory=Path(directory or (ROOT/"data"/"live" if (ROOT/"data"/"live"/"sales.csv").exists() else ROOT/"data"))
    reports=Path(reports or (ROOT/"reports"/"live" if directory.name=="live" else ROOT/"reports"))
    sales = pd.read_csv(directory/"sales.csv",parse_dates=["week"])
    operations=pd.read_csv(directory/"operations.csv",parse_dates=["week"]) if (directory/"operations.csv").exists() else None
    payload = {}
    for metric in ["revenue","units"]:
        weekly = pd.read_csv(reports/f"detections_{metric}.csv",parse_dates=["week"])
        investigations = {}
        for week in weekly.loc[weekly.eligible,"week"]:
            result = investigate(sales,week,metric)
            investigations[week.strftime("%Y-%m-%d")] = {
                "actual":result["actual"],"expected":result["expected"],"gap":result["gap"],"narrative":result["narrative"],
                "volume":result["volume_effect"],"price":result["price_effect"],"decision":recommend(result,operations),
                "drivers":{dim:table.rename(columns={f"{metric}_actual":"actual",f"{metric}_expected":"expected","contribution_pct":"share",dim:"segment"}).fillna(0).to_dict("records") for dim,table in result["marginals"].items()},
                "top":[dict(label=f"{row.region} · {row.sku}<br>{row.channel}",delta=row.delta) for row in result["top"].itertuples()],
            }
        clean = weekly.copy()
        clean["week"] = clean.week.dt.strftime("%Y-%m-%d")
        payload[metric] = {"weekly":json.loads(clean.to_json(orient="records")),"investigations":investigations}
    payload["evaluation"] = pd.read_csv(reports/"evaluation.csv").to_dict("records") if (reports/"evaluation.csv").exists() else []
    payload["scenarios"] = json.loads(pd.read_csv(directory/"ground_truth.csv").to_json(orient="records")) if (directory/"ground_truth.csv").exists() else []
    payload["benchmark"] = pd.read_csv(ROOT/"reports"/"benchmark"/"summary.csv").to_dict("records") if (ROOT/"reports"/"benchmark"/"summary.csv").exists() else []
    payload["metadata"] = json.loads((reports/"manifest.json").read_text()) if (reports/"manifest.json").exists() else {"last_week":sales.week.max().strftime("%Y-%m-%d"),"generated_at":"","source_kind":"synthetic"}
    payload["metadata"].update({"weeks":int(sales.week.nunique()),"regions":int(sales.region.nunique()),"products":int(sales.sku.nunique()),"channels":int(sales.channel.nunique()),"records":len(sales)})
    template = (ROOT/"docs"/"demo_template.html").read_text(encoding="utf-8")
    template=template.replace("Every movement has a story.","Investigate weekly sales changes.")
    decision_panel=(ROOT/"docs"/"decision_panel.html").read_text(encoding="utf-8")
    template=template.replace('<button id="download"',decision_panel+'<button id="download"')
    template=template.replace('<h2>Scenario ledger</h2>','<h2>Frozen future-period benchmark</h2><div id="holdout" class="table-wrap"></div><p class="caption">Five fresh seeds × 52 future weeks. Settings were frozen before testing. All misses are included. Whole-seed bootstrap intervals and per-seed results are in the repository.</p><h2>Scenario ledger</h2>')
    template=template.replace('<div class="metrics"><div class="card">','<p id="freshness" class="caption"></p><div class="metrics"><div class="card">',1)
    template=template.replace('<strong>104 weeks</strong> · 2023–2024',f'<strong>{sales.week.nunique()} weeks</strong> · {sales.week.min():%Y}–{sales.week.max():%Y}')
    template=template.replace('37,440 synthetic sales records',f'{len(sales):,} synthetic sales records')
    template=template.replace('78 monitored weeks',f'{sales.week.nunique()-26} monitored weeks')
    template=template.replace('Synthetic data · 2023–2024',f'Synthetic data · {sales.week.min():%Y}–{sales.week.max():%Y}')
    enhancements=(ROOT/"docs"/"demo_enhancements.js").read_text(encoding="utf-8")
    template=template.replace('weeks();\n</script>','weeks();\n'+enhancements+'\n</script>')
    html = template.replace("__PAYLOAD__",json.dumps(payload,allow_nan=False).replace("</","<\\/"))
    (output/"index.html").write_text(html,encoding="utf-8")
    (output/"plotly.min.js").write_text(plotly.offline.get_plotlyjs(),encoding="utf-8")
    print(f"Exported {len(payload['revenue']['investigations'])} investigation weeks per metric to {output}")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path)
    parser.add_argument("--reports",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    export(args.output,args.directory,args.reports)
