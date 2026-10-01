"""Operational evidence and an explicit, assumption-driven intervention model."""
import pandas as pd

KEYS=["week","region","sku","channel"]
REQUIRED=KEYS+["stockout_days","fill_rate","outage_minutes","promo_discount","store_count_change_pct","temperature_c","price_change_pct"]

def validate_operations(operations,sales):
    import numpy as np
    if not set(REQUIRED).issubset(operations.columns):
        raise ValueError("Operational context is missing required columns")
    if operations[REQUIRED].isna().any().any() or operations.duplicated(KEYS).any():
        raise ValueError("Null or duplicate operational context")
    values=operations[REQUIRED[4:]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite operational context")
    if not operations.stockout_days.between(0,7).all() or not operations.fill_rate.between(0,1).all() or not operations.outage_minutes.between(0,10080).all() or not operations.promo_discount.between(0,1).all():
        raise ValueError("Operational rates or durations outside valid ranges")
    if not pd.MultiIndex.from_frame(operations[KEYS]).isin(pd.MultiIndex.from_frame(sales[KEYS])).all():
        raise ValueError("Operational context does not match sales segment-weeks")
    return operations

def recommend(result,operations=None,recovery_rate=.5,margin=.30,cost=500.):
    if not 0<=recovery_rate<=1 or not 0<=margin<=1 or cost<0:
        raise ValueError("Recovery, margin, and cost assumptions are outside valid ranges")
    empty=dict(status="Needs evidence",issue="Unverified sales movement",owner="Sales analyst",action="Check inventory, order availability, prices, and campaign records before intervening.",evidence=[],exposed_revenue=0.,potential_revenue=0.,potential_margin=0.,net_value=-cost,break_even_recovery=None,recovery_rate=recovery_rate,margin_rate=margin,cost=cost,success_measure="Review the next four complete weeks against the seasonal forecast.")
    if operations is None or operations.empty:
        return empty
    context=operations[operations.week.eq(result["week"])].copy()
    if context.empty:
        return empty
    cells=result["cells"].merge(context.drop(columns="week"),on=KEYS[1:],how="inner",validate="one_to_one")
    if cells.empty:
        return empty
    signals=[
        ("Stock availability",(cells.stockout_days>0)&(cells.fill_rate<.90),"Supply planning","Prioritize replenishment for the affected product/region/channel cells; confirm transfer capacity before committing spend.","Restore fill rate to at least 95%; track units recovery over the next two complete weeks."),
        ("Channel outage",cells.outage_minutes>60,"Commerce operations","Restore ordering availability, verify failed orders, and contact affected accounts to recover recoverable demand.","Reduce outage time below 60 minutes per week and reconcile successful versus failed orders."),
        ("Promotion economics",cells.promo_discount>.05,"Commercial finance","Review incremental gross margin and substitution before extending the promotion.","Compare incremental gross margin against discount and campaign costs, with an untreated comparison group."),
        ("Price change",cells.price_change_pct.abs()>.05,"Pricing manager","Separate price uplift from volume response and review retention before rolling out further price changes.","Track unit retention and gross margin for four weeks; compare with unaffected products."),
        ("Distribution expansion",cells.store_count_change_pct>.10,"Regional sales","Validate repeat orders and sell-through before increasing the regional allocation.","Measure repeat orders per added store over the next four weeks."),
        ("Weather exposure",cells.temperature_c>35,"Demand planning","Check weather-linked sell-through and consider a temporary replenishment adjustment rather than changing the annual forecast.","Review availability and sell-through after temperatures normalize."),
    ]
    candidates=[]
    for issue,mask,owner,action,success in signals:
        selected=cells[mask]
        if selected.empty:
            continue
        exposed=float((selected.revenue_expected-selected.revenue_actual).clip(lower=0).sum())
        movement=float((selected.revenue_actual-selected.revenue_expected).abs().sum())
        candidates.append((exposed if issue in ["Stock availability","Channel outage"] else movement,issue,selected,owner,action,success,exposed))
    if not candidates:
        return empty
    _,issue,selected,owner,action,success,exposed=max(candidates,key=lambda x:x[0])
    recoverable=issue in ["Stock availability","Channel outage"]
    if not recoverable:
        exposed=0.
    potential=exposed*recovery_rate
    evidence=[f"{row.region} / {row.sku} / {row.channel}: stockout {row.stockout_days:g} days, fill rate {row.fill_rate:.0%}, outage {row.outage_minutes:,.0f} minutes, promo {row.promo_discount:.0%}, price change {row.price_change_pct:+.0%}" for row in selected.head(3).itertuples()]
    breakeven=cost/(exposed*margin) if exposed*margin>0 else None
    return dict(status="Operational evidence available",issue=issue,owner=owner,action=action,evidence=evidence,affected_cells=len(selected),exposed_revenue=exposed,potential_revenue=potential,potential_margin=potential*margin,net_value=potential*margin-cost,break_even_recovery=breakeven,recovery_rate=recovery_rate,margin_rate=margin,cost=cost,success_measure=success)
