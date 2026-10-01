"""Additive sales attribution; contributions describe association, not causality."""
import numpy as np
import pandas as pd

DIMENSIONS = ["region", "sku", "channel"]

def investigate(sales, week, metric="revenue"):
    week = pd.Timestamp(week)
    history = sales[(sales.week < week) & (sales.week >= week-pd.Timedelta(weeks=4))]
    actual = sales[sales.week.eq(week)]
    if history.week.nunique() < 4 or actual.empty:
        raise ValueError("Investigation requires a selected week and four prior weeks")
    expected = history.groupby(DIMENSIONS)[["units", "revenue"]].sum() / 4
    cells = actual.groupby(DIMENSIONS)[["units", "revenue"]].sum().join(expected, lsuffix="_actual", rsuffix="_expected", how="outer").fillna(0).reset_index()
    cells["delta"] = cells[f"{metric}_actual"]-cells[f"{metric}_expected"]
    total_gap = float(cells.delta.sum())
    net_is_small = abs(total_gap) < max(float(cells[f"{metric}_expected"].sum())*.001, 1.)
    cells["contribution_pct"] = np.nan if net_is_small else cells.delta / total_gap * 100
    sign = 1 if total_gap >= 0 else -1
    cells["aligned_delta"] = cells.delta * sign
    cells = cells.sort_values("aligned_delta", ascending=False)
    marginals = {}
    for dimension in DIMENSIONS:
        grouped = cells.groupby(dimension)[[f"{metric}_actual", f"{metric}_expected", "delta"]].sum().reset_index()
        grouped["contribution_pct"] = np.nan if net_is_small else grouped.delta/total_gap*100
        marginals[dimension] = grouped.sort_values("delta", ascending=sign < 0)
    top = cells[cells.aligned_delta > 0].head(3)
    total_actual = float(cells[f"{metric}_actual"].sum())
    total_expected = float(cells[f"{metric}_expected"].sum())
    fmt = (lambda n: f"${n:,.0f}") if metric == "revenue" else (lambda n: f"{n:,.0f} units")
    if net_is_small:
        narrative = f"{metric.title()} was close to the prior four-week baseline ({fmt(total_actual)} versus {fmt(total_expected)}). The net gap is too small for stable contribution percentages. Inspect offsetting segment movements."
    else:
        driver = marginals["region"].iloc[0]
        movement = "increase" if total_gap > 0 else "decrease"
        rate = total_gap/total_expected if total_expected else 0
        narrative = f"{metric.title()} recorded a {fmt(abs(total_gap))} {movement} ({rate:+.1%}) versus the prior four-week average. {driver.region} contributed {driver.contribution_pct:.1f}% of the net gap. "
        if not top.empty:
            lead = top.iloc[0]
            base = lead.units_expected
            change = (lead.units_actual/base-1) if base else 0
            narrative += f"The largest individual driver was {lead.sku} in {lead.region} / {lead.channel}, with units changing {change:+.1%}. "
        regional = marginals["region"]
        opposing = regional[regional.delta * sign < 0].sort_values("delta", ascending=sign > 0)
        if not opposing.empty:
            opposite = opposing.iloc[0]
            narrative += f"An offsetting {'decline' if sign > 0 else 'gain'} of {fmt(abs(opposite.delta))} occurred in {opposite.region}. "
        narrative += "Validate inventory, pricing, and campaign records before assigning a business cause."
    # Exact revenue bridge: volume at expected price + price/mix at actual volume.
    expected_price = cells.revenue_expected.div(cells.units_expected.replace(0, np.nan)).fillna(0)
    actual_price = cells.revenue_actual.div(cells.units_actual.replace(0, np.nan)).fillna(expected_price)
    volume_effect = float(((cells.units_actual-cells.units_expected)*expected_price).sum())
    price_effect = float((cells.units_actual*(actual_price-expected_price)).sum())
    return {"week": week, "metric": metric, "actual": total_actual, "expected": total_expected, "gap": total_gap, "cells": cells, "marginals": marginals, "top": top, "narrative": narrative, "volume_effect": volume_effect, "price_effect": price_effect, "small_gap": net_is_small}
