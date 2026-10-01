import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def test_saved_reports_match_exact_sales_and_detector():
    for source,output in [(ROOT/"data",ROOT/"reports"),(ROOT/"data"/"live",ROOT/"reports"/"live")]:
        if not (output/"manifest.json").exists():
            continue
        metadata=json.loads((output/"manifest.json").read_text())
        assert metadata["sales_sha256"]==hashlib.sha256((source/"sales.csv").read_bytes()).hexdigest()
        assert metadata["detector_sha256"]==hashlib.sha256((ROOT/"detector.py").read_bytes()).hexdigest()
        assert metadata["config_sha256"]==hashlib.sha256((ROOT/"detector_config.json").read_bytes()).hexdigest()
        sales=pd.read_csv(source/"sales.csv")
        assert metadata["quality"]["rows"]==len(sales)
        assert metadata["last_week"]==sales.week.max()
