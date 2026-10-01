"""Export a standalone interactive report from the Python analytics pipeline."""
from pathlib import Path
import json
import pandas as pd
import plotly.offline
from root_cause import investigate

ROOT = Path(__file__).resolve().parent

def export(output=None):
    output = Path(output or ROOT/"site")
    output.mkdir(parents=True,exist_ok=True)
    sales = pd.read_csv(ROOT/"data"/"sales.csv",parse_dates=["week"])
    payload = {}
    for metric in ["revenue","units"]:
        weekly = pd.read_csv(ROOT/"reports"/f"detections_{metric}.csv",parse_dates=["week"])
        investigations = {}
        for week in weekly.loc[weekly.eligible,"week"]:
            result = investigate(sales,week,metric)
            investigations[week.strftime("%Y-%m-%d")] = {
                "actual":result["actual"],"expected":result["expected"],"gap":result["gap"],"narrative":result["narrative"],
                "volume":result["volume_effect"],"price":result["price_effect"],
                "drivers":{dim:table.rename(columns={f"{metric}_actual":"actual",f"{metric}_expected":"expected","contribution_pct":"share",dim:"segment"}).fillna(0).to_dict("records") for dim,table in result["marginals"].items()},
                "top":[dict(label=f"{row.region} · {row.sku}<br>{row.channel}",delta=row.delta) for row in result["top"].itertuples()],
            }
        clean = weekly.copy()
        clean["week"] = clean.week.dt.strftime("%Y-%m-%d")
        payload[metric] = {"weekly":json.loads(clean.to_json(orient="records")),"investigations":investigations}
    payload["evaluation"] = pd.read_csv(ROOT/"reports"/"evaluation.csv").to_dict("records")
    ledger = pd.read_csv(ROOT/"data"/"ground_truth.csv")
    payload["scenarios"] = ledger.to_dict("records")
    template = (ROOT/"docs"/"demo_template.html").read_text(encoding="utf-8")
    html = template.replace("__PAYLOAD__",json.dumps(payload,allow_nan=False).replace("</","<\\/"))
    (output/"index.html").write_text(html,encoding="utf-8")
    (output/"plotly.min.js").write_text(plotly.offline.get_plotlyjs(),encoding="utf-8")
    print(f"Exported {len(payload['revenue']['investigations'])} investigation weeks per metric to {output}")

if __name__ == "__main__":
    export()
