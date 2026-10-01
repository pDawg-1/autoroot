"""Run monitoring and export an investigation for every detected event."""
from pathlib import Path
import pandas as pd
from charts import timeline, waterfall
from evaluate import run
from generate_data import generate
from root_cause import investigate

ROOT=Path(__file__).resolve().parent

def pipeline():
    if not (ROOT/"data"/"sales.csv").exists():
        generate(output=ROOT/"data")
    run()
    sales=pd.read_csv(ROOT/"data"/"sales.csv",parse_dates=["week"])
    summaries=[]
    for metric in ["revenue","units"]:
        weekly=pd.read_csv(ROOT/"reports"/f"detections_{metric}.csv",parse_dates=["week"])
        for week in weekly.loc[weekly.ensemble,"week"]:
            result=investigate(sales,week,metric)
            stem=f"{metric}-{week:%Y-%m-%d}"
            (ROOT/"reports"/f"{stem}.md").write_text(f"# {metric.title()} investigation · {week:%Y-%m-%d}\n\n{result['narrative']}\n\nBaseline: the previous four-week average. Synthetic sales; business causes require independent validation.\n",encoding="utf-8")
            timeline(weekly,metric,"ensemble",week).write_html(ROOT/"reports"/f"{stem}-timeline.html",include_plotlyjs=True)
            waterfall(result).write_html(ROOT/"reports"/f"{stem}-drivers.html",include_plotlyjs=True)
            summaries.append({"metric":metric,"week":week,"actual":result["actual"],"expected":result["expected"],"gap":result["gap"],"narrative":result["narrative"]})
    pd.DataFrame(summaries).to_csv(ROOT/"reports"/"investigations.csv",index=False,date_format="%Y-%m-%d")
    print(f"Exported {len(summaries)} investigation briefs and chart pairs.")

if __name__=="__main__":
    pipeline()
