"""DuckDB star schema, KPI queries, and fail-fast quality checks."""
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent

def validate(sales):
    required = ["week", "region", "sku", "channel", "units", "revenue"]
    if not set(required).issubset(sales.columns):
        raise ValueError("Missing required sales columns")
    if sales[required].isna().any().any():
        raise ValueError("Null values in sales")
    if sales.duplicated(required[:4]).any():
        raise ValueError("Duplicate segment-week records")
    if (sales[["units", "revenue"]] < 0).any().any():
        raise ValueError("Negative sales")
    if (sales.units % 1 != 0).any():
        raise ValueError("Units must be whole numbers")
    weeks = pd.DatetimeIndex(pd.to_datetime(sales.week).unique()).sort_values()
    if len(weeks) > 1 and not ((weeks[1:] - weeks[:-1]).days == 7).all():
        raise ValueError("Missing or irregular weeks")
    counts = sales.groupby("week").size()
    if counts.nunique() != 1:
        raise ValueError("Incomplete weekly panel")
    if not sales.groupby(required[1:4]).size().eq(len(weeks)).all():
        raise ValueError("Incomplete segment history")
    return {"rows": len(sales), "weeks": len(weeks), "segments_per_week": int(counts.iloc[0]), "status": "passed"}

def build_warehouse(directory=None, database=":memory:"):
    directory = Path(directory or ROOT / "data")
    sales = pd.read_csv(directory / "sales.csv", parse_dates=["week"])
    validate(sales)
    conn = duckdb.connect(str(database))
    conn.execute((ROOT / "schema.sql").read_text())
    for name, table in [("regions", "dim_region"), ("products", "dim_product"), ("channels", "dim_channel"), ("sales", "fact_sales")]:
        frame = sales if name == "sales" else pd.read_csv(directory / f"{name}.csv")
        conn.register("input_frame", frame)
        conn.execute(f"INSERT INTO {table} SELECT * FROM input_frame")
        conn.unregister("input_frame")
    return conn

if __name__ == "__main__":
    with build_warehouse(database=ROOT / "data" / "sales.duckdb") as conn:
        print(conn.sql("SELECT * FROM kpi_weekly ORDER BY week DESC LIMIT 5").df().to_string(index=False))
