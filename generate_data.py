"""Create a reproducible retail sales panel and a separate scenario ledger."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REGIONS = ["North", "South", "East", "West", "Central", "Northeast", "Northwest", "Southeast"]
SKUS = ["Cola 750ml", "Lemon 600ml", "Orange 500ml", "Water 1L", "Water 500ml", "Tonic 250ml", "Ginger 330ml", "Apple 1L", "Mango 1L", "Tea 500ml", "Coffee 250ml", "Energy 250ml", "Soda 1L", "Lime 330ml", "Berry 500ml"]
CHANNELS = ["Modern trade", "Convenience", "Online"]

def scenarios():
    # All injections occur after a 26-week clean calibration period.
    return [
        dict(id="S01", index=32, name="Regional heatwave", region="North", sku="*", channel="*", units_multiplier=1.35, price_multiplier=1., hypothesis="Weather-driven demand; validate against local weather records."),
        dict(id="S02", index=50, name="Promotion cannibalization", region="*", sku="Cola 750ml|Lemon 600ml", channel="Modern trade", units_multiplier=1.8, price_multiplier=.70, hypothesis="Promotion uplift with a discount; validate promotion calendar and substitution."),
        dict(id="S03", index=56, name="Supply disruption", region="West", sku="Cola 750ml|Lemon 600ml", channel="*", units_multiplier=.60, price_multiplier=1., hypothesis="Possible stockout; validate inventory and fill-rate records."),
        dict(id="S04", index=63, name="Online channel outage", region="*", sku="*", channel="Online", units_multiplier=.35, price_multiplier=1., hypothesis="Possible checkout disruption; validate order logs and uptime."),
        dict(id="S05", index=72, name="Price reset", region="*", sku="*", channel="*", units_multiplier=1., price_multiplier=1.22, hypothesis="Price increase rather than volume growth; validate price master."),
        dict(id="S06", index=81, name="Regional distribution expansion", region="South", sku="*", channel="Modern trade", units_multiplier=1.65, price_multiplier=1., hypothesis="Possible distribution gain; validate active store count."),
        dict(id="S07", index=91, name="National demand contraction", region="*", sku="*", channel="*", units_multiplier=.78, price_multiplier=1., hypothesis="Broad demand weakness; validate market and calendar context."),
        dict(id="S08", index=99, name="Convenience restocking", region="*", sku="*", channel="Convenience", units_multiplier=1.45, price_multiplier=1., hypothesis="Possible inventory restocking; validate sell-through versus shipments."),
    ]

def generate(seed=42, output=None, periods=104, event_rules=None):
    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2023-01-02", periods=periods, freq="W-MON")
    regions = pd.DataFrame({"region": REGIONS, "demand_factor": [1.20, 1.12, 1.05, 1.15, .95, .90, .82, 1.0]})
    products = pd.DataFrame({"sku": SKUS, "base_demand": [950, 820, 650, 880, 730, 320, 430, 520, 480, 550, 380, 420, 700, 360, 440], "list_price": [2.8, 2.4, 2.2, 1.6, 1.1, 2.5, 2.3, 3.2, 3.6, 2.7, 3.8, 3.3, 1.9, 2.0, 2.6]})
    channels = pd.DataFrame({"channel": CHANNELS, "demand_factor": [.55, .28, .17], "price_factor": [1., 1.08, .96]})
    records = []
    for i, week in enumerate(weeks):
        season = 1 + .14 * np.sin(2 * np.pi * i / 52) + .035 * np.cos(4 * np.pi * i / 52)
        trend = 1 + .0015 * i
        for region in regions.itertuples(index=False):
            for product in products.itertuples(index=False):
                for channel in channels.itertuples(index=False):
                    demand = product.base_demand * region.demand_factor * channel.demand_factor * season * trend
                    units = max(1, int(round(demand * rng.lognormal(-.5*.06**2, .06))))
                    price = product.list_price * channel.price_factor
                    records.append((week, region.region, product.sku, channel.channel, units, price))
    sales = pd.DataFrame(records, columns=["week", "region", "sku", "channel", "units", "price"])
    context = sales[["week", "region", "sku", "channel"]].copy()
    context["stockout_days"] = 0
    context["fill_rate"] = .98
    context["outage_minutes"] = 0
    context["promo_discount"] = 0.
    context["store_count_change_pct"] = 0.
    context["temperature_c"] = 24.
    context["price_change_pct"] = 0.
    ledger = []
    for event in (scenarios() if event_rules is None else event_rules):
        if event["index"] >= periods:
            continue
        week = weeks[event["index"]]
        mask = sales.week.eq(week)
        for dim in ["region", "sku", "channel"]:
            if event[dim] != "*":
                mask &= sales[dim].isin(event[dim].split("|"))
        before_units = sales.loc[mask, "units"].sum()
        before_rev = (sales.loc[mask, "units"] * sales.loc[mask, "price"]).sum()
        sales.loc[mask, "units"] = (sales.loc[mask, "units"] * event["units_multiplier"]).round().astype(int)
        sales.loc[mask, "price"] *= event["price_multiplier"]
        kind = event.get("kind", event["id"])
        if kind in ["S01", "heatwave"]:
            context.loc[mask,"temperature_c"] = 41.
        elif kind in ["S02", "promotion"]:
            context.loc[mask,"promo_discount"] = 1-event["price_multiplier"]
        elif kind in ["S03", "stockout"]:
            context.loc[mask,"stockout_days"] = 3
            context.loc[mask,"fill_rate"] = event["units_multiplier"]
        elif kind in ["S04", "outage"]:
            context.loc[mask,"outage_minutes"] = 7*24*60*(1-event["units_multiplier"])
        elif kind in ["S05", "price"]:
            context.loc[mask,"price_change_pct"] = event["price_multiplier"]-1
        elif kind in ["S06", "distribution"]:
            context.loc[mask,"store_count_change_pct"] = event["units_multiplier"]-1
        ledger.append({**event, "week": week, "affected_rows": int(mask.sum()), "injected_units_delta": int(sales.loc[mask, "units"].sum()-before_units), "injected_revenue_delta": round((sales.loc[mask, "units"]*sales.loc[mask, "price"]).sum()-before_rev, 2)})
    sales["revenue"] = (sales.units * sales.price).round(2)
    sales = sales.drop(columns="price")
    labels = pd.DataFrame(ledger).drop(columns="index")
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        for name, frame in {"sales": sales, "ground_truth": labels, "regions": regions, "products": products, "channels": channels, "operations": context}.items():
            frame.to_csv(output / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return sales, labels, regions, products, channels

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    sales, labels, *_ = generate(args.seed, args.output)
    print(f"Generated {len(sales):,} rows, {sales.week.nunique()} weeks, {len(labels)} scenarios.")
