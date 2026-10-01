"""Shared Python analysis entrypoint for browser-selected CSV files."""
import io
import json
import pandas as pd
from detector import detect
from root_cause import investigate
from sales_validation import validate

def analyze(csv_text, metric="revenue"):
    if metric not in ("revenue", "units"):
        raise ValueError("Choose revenue or units")
    sales = pd.read_csv(io.StringIO(csv_text), dtype={"region":str,"sku":str,"channel":str})
    if "week" not in sales:
        raise ValueError("Missing required sales columns")
    sales["week"] = pd.to_datetime(sales.week, format="%Y-%m-%d", errors="raise")
    quality = validate(sales)
    if not 27 <= quality["weeks"] <= 260 or quality["rows"] > 100000:
        raise ValueError("Use 27–260 complete weeks and at most 100,000 rows")
    if sum(sales[d].nunique() for d in ("region","sku","channel")) > 60:
        raise ValueError("Browser analysis supports at most 60 marginal segments")
    weekly, evidence = detect(sales, metric)
    investigations = {}
    for week in weekly.loc[weekly.eligible,"week"]:
        result = investigate(sales,week,metric)
        investigations[week.strftime("%Y-%m-%d")] = {
            "actual":result["actual"],"expected":result["expected"],"gap":result["gap"],
            "narrative":result["narrative"],"volume":result["volume_effect"],"price":result["price_effect"],
            "drivers": {d:json.loads(t.to_json(orient="records")) for d,t in result["marginals"].items()}}
    weekly["week"] = weekly.week.dt.strftime("%Y-%m-%d")
    evidence["week"] = evidence.week.dt.strftime("%Y-%m-%d") if len(evidence) else evidence.week
    return json.dumps({"metric":metric,"quality":quality,"weekly":json.loads(weekly.to_json(orient="records")),
                       "evidence":json.loads(evidence.to_json(orient="records")),"investigations":investigations},allow_nan=False)
