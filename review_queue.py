"""Rank segment signals within an explicit weekly analyst review budget."""
import pandas as pd
from detector import CONFIG

def queue(evidence,week,budget=None):
    budget=CONFIG["review_budget_per_week"] if budget is None else budget
    if budget<1:
        raise ValueError("Review budget must be positive")
    rows=evidence[evidence.week.eq(pd.Timestamp(week))].copy()
    if rows.empty:
        return rows
    rows["absolute_gap"]=(rows.actual-rows.expected).abs()
    rows["priority"]=rows.score.abs()*rows.absolute_gap
    rows=rows.sort_values("priority",ascending=False)
    rows["review_status"]= "Queued"
    return rows.head(budget)
