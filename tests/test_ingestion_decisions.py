import io
import numpy as np
import pandas as pd
import pytest
from generate_data import generate
from ingestion import parse_sales,merge_sales,ingest
from decision import recommend,validate_operations
from root_cause import investigate
from benchmark import fingerprints,summary

def test_append_idempotent_and_conflicts_fail(tmp_path):
    sales=generate()[0]
    existing=sales[sales.week<sales.week.max()].copy()
    incoming=sales[sales.week.eq(sales.week.max())].copy()
    combined,result=merge_sales(existing,incoming)
    assert len(combined)==len(sales)
    assert result["added_weeks"]==1
    again,result=merge_sales(combined,incoming)
    assert result["added_rows"]==0
    assert result["duplicate_rows"]==360
    bad=incoming.copy()
    bad.iloc[0,bad.columns.get_loc("units")]+=1
    with pytest.raises(ValueError,match="Conflicting"):
        merge_sales(again,bad)

def test_bad_batch_does_not_change_stored_sales(tmp_path):
    sales=generate()[0]
    raw=sales.to_csv(index=False).encode()
    ingest(io.BytesIO(raw),tmp_path)
    before=(tmp_path/"sales.csv").read_bytes()
    bad=sales.iloc[-360:-1]
    with pytest.raises(ValueError):
        ingest(io.BytesIO(bad.to_csv(index=False).encode()),tmp_path)
    assert (tmp_path/"sales.csv").read_bytes()==before

def test_nonfinite_and_bad_dates_rejected():
    frame=generate()[0].iloc[:360].copy()
    frame.iloc[0,frame.columns.get_loc("revenue")]=np.inf
    with pytest.raises(ValueError,match="Non-finite"):
        parse_sales(frame.to_csv(index=False).encode())
    frame["revenue"]=1.
    frame["week"]+=pd.Timedelta(days=1)
    with pytest.raises(ValueError,match="Monday"):
        parse_sales(frame.to_csv(index=False).encode())

def test_decision_requires_independent_context_and_assumptions(tmp_path):
    sales,labels,*_=generate(output=tmp_path)
    ops=pd.read_csv(tmp_path/"operations.csv",parse_dates=["week"])
    validate_operations(ops,sales)
    week=labels.loc[labels.id.eq("S03"),"week"].iloc[0]
    result=investigate(sales,week)
    no_context=recommend(result)
    assert no_context["status"]=="Needs evidence"
    assert no_context["exposed_revenue"]==0
    action=recommend(result,ops,recovery_rate=.5,margin=.3,cost=200.)
    assert action["issue"]=="Stock availability"
    assert action["affected_cells"]==6
    assert action["exposed_revenue"]>0
    assert action["potential_revenue"]==pytest.approx(action["exposed_revenue"]*.5)
    assert action["net_value"]==pytest.approx(action["potential_revenue"]*.3-200)
    assert action["break_even_recovery"]==pytest.approx(200/(action["exposed_revenue"]*.3))
    price_week=labels.loc[labels.id.eq("S05"),"week"].iloc[0]
    assert recommend(investigate(sales,price_week),ops)["exposed_revenue"]==0

def test_invalid_context_rejected_before_sales_write(tmp_path):
    sales,labels,*_=generate(output=tmp_path/"source")
    ops=pd.read_csv(tmp_path/"source"/"operations.csv")
    ops.loc[0,"fill_rate"]=1.5
    target=tmp_path/"target"
    with pytest.raises(ValueError,match="outside valid"):
        ingest(tmp_path/"source"/"sales.csv",target,operations_source=io.BytesIO(ops.to_csv(index=False).encode()))
    assert not (target/"sales.csv").exists()

def test_holdout_fingerprint_matches_frozen_run():
    import json
    from pathlib import Path
    lock=Path(__file__).resolve().parents[1]/"reports"/"benchmark"/"lock.json"
    if lock.exists():
        assert json.loads(lock.read_text())["fingerprints"]==fingerprints()

def test_missing_label_data_not_scored_as_normal(tmp_path):
    from evaluate import evaluate
    frame=pd.DataFrame({"week":pd.date_range("2025-01-06",periods=2,freq="W-MON"),"eligible":True,"rolling_z":False,"seasonal":False,"isolation_forest":False,"ensemble":False})
    with pytest.raises((ValueError,AttributeError,TypeError)):
        evaluate(frame,None,"revenue")

def test_review_budget_caps_queue_without_erasing_evidence():
    from review_queue import queue
    evidence=pd.DataFrame({"week":[pd.Timestamp("2025-01-06")]*5,"score":[4.,5.,6.,7.,8.],"actual":[50.]*5,"expected":[100.]*5,"segment":["a","b","c","d","e"]})
    selected=queue(evidence,"2025-01-06")
    assert len(selected)==3
    assert selected.segment.tolist()==["e","d","c"]
    assert len(evidence)==5

def test_advancing_source_appends_exactly_one_new_week(tmp_path):
    first=generate(periods=104)[0]
    second=generate(periods=105)[0]
    ingest(io.BytesIO(first.to_csv(index=False).encode()),tmp_path,source_kind="synthetic")
    combined,state=ingest(io.BytesIO(second.to_csv(index=False).encode()),tmp_path,source_kind="synthetic")
    assert state["added_weeks"]==1
    assert state["added_rows"]==360
    assert len(combined)==37800
    assert state["last_week"]=="2024-12-30"

def test_insecure_remote_feed_is_rejected_without_download():
    from ingestion import read_feed
    with pytest.raises(ValueError,match="HTTPS"):
        read_feed("http://example.com/sales.csv")
