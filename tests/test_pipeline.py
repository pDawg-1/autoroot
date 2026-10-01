import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest
from generate_data import generate
from detector import monitor_series, seasonal_residual
from evaluate import evaluate
from root_cause import investigate
from warehouse import validate,build_warehouse

@pytest.fixture(scope="module")
def panel():
    return generate()

def test_reproducible_complete_panel(panel):
    sales,labels,*_ = panel
    pd.testing.assert_frame_equal(sales,generate()[0])
    assert validate(sales)==dict(rows=37440,weeks=104,segments_per_week=360,status="passed")
    assert len(labels)==8

def test_warehouse_totals_and_foreign_keys(tmp_path,panel):
    generate(output=tmp_path)
    with build_warehouse(tmp_path) as conn:
        weekly=conn.sql("SELECT * FROM kpi_weekly ORDER BY week").df()
        assert len(weekly)==104
        assert weekly.revenue.sum()==pytest.approx(panel[0].revenue.sum())
        assert weekly.revenue_yoy.iloc[:52].isna().all()

def test_invalid_data_rejected(panel):
    sales=panel[0]
    with pytest.raises(ValueError,match="Duplicate"):
        validate(pd.concat([sales,sales.iloc[:1]]))
    with pytest.raises(ValueError,match="Incomplete"):
        validate(sales.iloc[1:])

def test_root_cause_reconciles_every_event(panel):
    sales,labels,*_=panel
    for week in labels.week:
        for metric in ["revenue","units"]:
            report=investigate(sales,week,metric)
            assert report["cells"].delta.sum()==pytest.approx(report["gap"])
            for dim,table in report["marginals"].items():
                assert table.delta.sum()==pytest.approx(report["gap"])
            assert report["volume_effect"]+report["price_effect"]==pytest.approx(report["cells"].revenue_actual.sum()-report["cells"].revenue_expected.sum())
    event=labels[labels.id.eq("S03")].week.iloc[0]
    report=investigate(sales,event)
    assert report["marginals"]["region"].sort_values("delta").iloc[0].region=="West"
    assert "West" in report["narrative"]

def test_future_mutation_does_not_change_past_scores(panel):
    weekly=panel[0].groupby("week",as_index=False).revenue.sum().iloc[:45].copy()
    before=monitor_series(weekly)
    changed=weekly.copy()
    changed.loc[40:,"revenue"]*=10
    after=monitor_series(changed)
    pd.testing.assert_frame_equal(before.iloc[:40],after.iloc[:40])
    assert not before.iloc[:26].eligible.any()

def test_metric_specific_labels_and_confusion_counts(panel):
    labels=panel[1]
    weekly=panel[0].groupby("week",as_index=False).units.sum()
    weekly["eligible"]=weekly.index>=26
    for method in ["rolling_z","seasonal","isolation_forest","ensemble"]:
        weekly[method]=False
    result=evaluate(weekly,labels,"units")
    assert result.labeled_weeks.eq(7).all()
    assert result.false_negatives.eq(7).all()
    assert result.true_negatives.eq(71).all()

def test_zero_gap_safe():
    weeks=pd.date_range("2024-01-01",periods=5,freq="W-MON")
    sales=pd.DataFrame(dict(week=weeks,region="West",sku="Cola",channel="Online",units=100,revenue=200.))
    result=investigate(sales,weeks[-1])
    assert result["small_gap"]
    assert result["cells"].contribution_pct.isna().all()
