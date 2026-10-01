"""Bootstrap and incrementally ingest the advancing synthetic feed."""
from pathlib import Path
import argparse
import shutil
from simulate_feed import feed
from monitor import pipeline

ROOT=Path(__file__).resolve().parent

def refresh(as_of=None):
    source=feed(as_of)
    live=ROOT/"data"/"live"
    live.mkdir(parents=True,exist_ok=True)
    for name in ["regions.csv","products.csv","channels.csv","ground_truth.csv"]:
        shutil.copyfile(source/name,live/name)
    return pipeline(live,ROOT/"reports"/"live",source/"sales.csv",source/"operations.csv","synthetic")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of")
    refresh(parser.parse_args().as_of)
