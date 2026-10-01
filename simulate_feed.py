"""Produce an advancing synthetic feed through the last complete week."""
from pathlib import Path
from datetime import date
import argparse
import json
import pandas as pd
from generate_data import generate,scenarios

ROOT=Path(__file__).resolve().parent

def feed(as_of=None,output=None):
    day=pd.Timestamp(as_of or date.today()).normalize()
    last_week=day-pd.Timedelta(days=day.dayofweek+7)
    periods=max(104,int((last_week-pd.Timestamp("2023-01-02")).days//7)+1)
    rules=scenarios()
    # Repeating future availability events produce fresh operational observations.
    for index in range(108,periods,13):
        rules.append(dict(id=f"F{index}",index=index,name="Synthetic availability disruption",kind="stockout" if index%2==0 else "outage",region="West" if index%2==0 else "*",sku="Cola 750ml|Lemon 600ml" if index%2==0 else "*",channel="*" if index%2==0 else "Online",units_multiplier=.60,price_multiplier=1.,hypothesis="Validate the separate operational context."))
    directory=Path(output or ROOT/"data"/"feeds")
    generate(seed=42,periods=periods,event_rules=rules,output=directory)
    print(f"Synthetic feed: {periods} weeks through {last_week:%Y-%m-%d}")
    return directory

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    feed(args.as_of,args.output)
