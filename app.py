"""AutoRoot: weekly sales monitoring and investigation workspace."""
from pathlib import Path
import json
import hashlib
import html
import pandas as pd
import streamlit as st
from charts import timeline, waterfall
from detector import detect, METHODS
from evaluate import evaluate
from generate_data import generate
from root_cause import investigate
from warehouse import build_warehouse, validate
from ingestion import parse_sales
from decision import recommend,validate_operations
from review_queue import queue

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="AutoRoot | Sales investigation",page_icon="◉",layout="wide")
st.markdown("""<style>
.block-container{padding-top:2.3rem;max-width:1440px}
h1{font-size:3.1rem!important;letter-spacing:-.06em;font-weight:750!important}
h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{background:#fff;border:1px solid #e2e8e0;border-radius:12px;padding:20px}
[data-testid="stSidebar"]{border-right:1px solid #e2e8e0}
.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:700;color:#087f73}
.brief{background:#e8f2eb;border-left:3px solid #087f73;padding:20px 24px;border-radius:0 10px 10px 0;line-height:1.75}
.badge{display:inline-block;padding:5px 11px;border-radius:20px;font-size:12px;font-weight:700;background:#fbe9e2;color:#ab4431}
.clear{background:#e2eee7;color:#087f73}
</style>""",unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(directory,fingerprint):
    directory=Path(directory)
    sales = parse_sales((directory/"sales.csv").read_bytes())
    labels=pd.read_csv(directory/"ground_truth.csv",parse_dates=["week"]) if (directory/"ground_truth.csv").exists() else None
    operations=pd.read_csv(directory/"operations.csv",parse_dates=["week"]) if (directory/"operations.csv").exists() else None
    if operations is not None:
        validate_operations(operations,sales)
    with build_warehouse(directory) as conn:
        kpis = conn.sql("SELECT * FROM kpi_weekly ORDER BY week").df()
    return sales,labels,kpis,validate(sales),operations

@st.cache_data(ttl=300)
def analysis(sales,metric,reports=None,sales_hash=None,detector_version=None):
    if reports:
        reports=Path(reports)
        manifest=reports/"manifest.json"
        if manifest.exists():
            metadata=json.loads(manifest.read_text())
            match=metadata.get("sales_sha256")==sales_hash and metadata.get("detector_sha256")==hashlib.sha256((ROOT/"detector.py").read_bytes()).hexdigest() and metadata.get("config_sha256")==hashlib.sha256((ROOT/"detector_config.json").read_bytes()).hexdigest()
            if match and (reports/f"detections_{metric}.csv").exists() and (reports/f"evidence_{metric}.csv").exists():
                return pd.read_csv(reports/f"detections_{metric}.csv",parse_dates=["week"]),pd.read_csv(reports/f"evidence_{metric}.csv",parse_dates=["week"])
    return detect(sales,metric)

with st.sidebar:
    st.markdown("## ◉ AutoRoot")
    st.caption("SALES INTELLIGENCE WORKSPACE")
    sources=["Synthetic demo","Upload sales CSV"]
    if (ROOT/"data"/"live"/"sales.csv").exists():
        sources.insert(0,"Latest monitored feed")
    source=st.selectbox("Data source",sources,key="source")
    sales_upload=st.file_uploader("Sales CSV",type="csv",key="sales_upload") if source=="Upload sales CSV" else None
    ops_upload=st.file_uploader("Operational context CSV (optional)",type="csv",key="ops_upload") if source=="Upload sales CSV" else None
    if source=="Upload sales CSV":
        st.download_button("Download sample sales CSV",(ROOT/"data"/"sales.csv").read_bytes(),file_name="sample-sales.csv",mime="text/csv")
        if (ROOT/"data"/"operations.csv").exists():
            st.download_button("Download sample operational context",(ROOT/"data"/"operations.csv").read_bytes(),file_name="sample-operations.csv",mime="text/csv")
if source=="Upload sales CSV":
    if sales_upload is None:
        st.title("Investigate a sales feed")
        st.info("Upload a complete Monday-based sales panel with at least 27 weeks. Required columns: week, region, sku, channel, units, revenue. Uploaded sales are processed for this session; the scheduled public demo uses its separate synthetic feed.")
        st.stop()
    try:
        sales=parse_sales(sales_upload.getvalue())
        labels=None
        operations=pd.read_csv(ops_upload,parse_dates=["week"]) if ops_upload else None
        if operations is not None:
            validate_operations(operations,sales)
        quality=validate(sales)
        with build_warehouse(sales_data=sales) as conn:
            kpis=conn.sql("SELECT * FROM kpi_weekly ORDER BY week").df()
    except (ValueError,TypeError,KeyError) as exc:
        st.error(f"The feed could not be loaded: {exc}")
        st.stop()
    reports=None
    sales_hash=hashlib.sha256(sales_upload.getvalue()).hexdigest()
else:
    directory=ROOT/"data"/"live" if source=="Latest monitored feed" else ROOT/"data"
    reports=ROOT/"reports"/"live" if source=="Latest monitored feed" else ROOT/"reports"
    if not (directory/"sales.csv").exists():
        generate(output=directory)
    sales_hash=hashlib.sha256((directory/"sales.csv").read_bytes()).hexdigest()
    context_hash=hashlib.sha256((directory/"operations.csv").read_bytes()).hexdigest() if (directory/"operations.csv").exists() else "none"
    sales,labels,kpis,quality,operations=load_data(str(directory),sales_hash+context_hash)
if sales.week.nunique()<27:
    st.warning("Monitoring needs at least 27 complete weeks: 26 history weeks and one scored week.")
    st.stop()
with st.sidebar:
    st.divider()
    metric = st.selectbox("Performance metric",["revenue","units"],format_func=str.title,key="metric")
    method = st.selectbox("Detection method",METHODS,index=3,key="method",format_func=lambda x:{"rolling_z":"Rolling Z-score","seasonal":"Seasonal decomposition","isolation_forest":"Isolation Forest","ensemble":"Combined + segment monitoring"}[x])
    with st.spinner("Checking weekly signals..."):
        version=hashlib.sha256((ROOT/"detector.py").read_bytes()+(ROOT/"detector_config.json").read_bytes()).hexdigest()
        weekly,evidence = analysis(sales,metric,str(reports) if reports else None,sales_hash,version)
    alerts_only = st.toggle("Show alert weeks only",value=True,key="alerts_only")
    options = weekly.loc[weekly[method] if alerts_only else weekly.eligible,"week"].tolist()
    if not options:
        st.info("No alerts for this method. Showing monitored weeks.")
        options = weekly.loc[weekly.eligible,"week"].tolist()
    default_week = pd.Timestamp("2024-03-18")
    default_index = options.index(default_week) if default_week in options else len(options)-1
    week = st.selectbox("Investigation week",options,index=default_index,key="week",format_func=lambda w:w.strftime("%d %b %Y"))
    st.divider()
    st.caption("DATA COVERAGE")
    st.markdown(f"**{quality['weeks']} weeks** · {sales.week.min():%Y}–{sales.week.max():%Y}\n\n{sales.region.nunique()} regions · {sales.sku.nunique()} products · {sales.channel.nunique()} channels")
    st.caption("Uploaded sales · USD" if source=="Upload sales CSV" else "Reproducible synthetic retail dataset · USD")
    st.caption(f"Latest complete week: {sales.week.max():%d %b %Y}")

selected = weekly.loc[weekly.week.eq(week)].iloc[0]
result = investigate(sales,week,metric)
is_alert = bool(selected[method])
st.markdown('<p class="eyebrow">MONITOR → INVESTIGATE → EXPLAIN</p>',unsafe_allow_html=True)
left,right = st.columns([4,1])
with left:
    st.title("Investigate weekly sales changes.")
    st.caption("Detect unusual weeks, reconcile segment drivers, and review the operational evidence.")
with right:
    st.markdown(f'<span class="badge {"" if is_alert else "clear"}">{"● Anomaly detected" if is_alert else "● Within range"}</span>',unsafe_allow_html=True)
    st.caption(f"Week of {week:%d %b %Y}")
st.write("")
fmt = (lambda n:f"${n:,.0f}") if metric=="revenue" else (lambda n:f"{n:,.0f}")
a,b,c,d = st.columns(4)
a.metric(f"Weekly {metric}",fmt(result["actual"]))
b.metric("Four-week baseline",fmt(result["expected"]))
c.metric("Change vs baseline",fmt(result["gap"]),f'{result["gap"]/result["expected"]:+.1%}',delta_color="off")
d.metric("Alert weeks",str(int(weekly[method].sum())),f'{int(weekly.eligible.sum())} monitored weeks',delta_color="off")
st.write("")
investigation,validation,methodology = st.tabs(["Investigation","Detection scorecard","How it works"])
with investigation:
    st.subheader("The signal")
    st.plotly_chart(timeline(weekly,metric,method,week),use_container_width=True)
    st.caption("Dotted line: past-only seasonal forecast. Investigation attribution uses the prior four-week average, a separate baseline.")
    st.subheader("Investigation brief")
    st.markdown(f'<div class="brief">{html.escape(result["narrative"])}</div>',unsafe_allow_html=True)
    st.write("")
    first,second = st.columns([1.35,1])
    with first:
        st.subheader("Where the gap came from")
        st.plotly_chart(waterfall(result),use_container_width=True)
        st.caption("Three leading non-overlapping segment cells plus all remaining cells reconcile exactly to the net change.")
    with second:
        st.subheader("Drill into the drivers")
        dim = st.radio("Dimension",["region","sku","channel"],horizontal=True,format_func=str.title)
        table = result["marginals"][dim].rename(columns={f"{metric}_actual":"Actual",f"{metric}_expected":"Expected","delta":"Change","contribution_pct":"Net gap %",dim:"Segment"})
        st.dataframe(table,hide_index=True,use_container_width=True,column_config={"Actual":st.column_config.NumberColumn(format="%.0f"),"Expected":st.column_config.NumberColumn(format="%.0f"),"Change":st.column_config.NumberColumn(format="%.0f"),"Net gap %":st.column_config.NumberColumn(format="%.1f%%")})
        st.caption("Each dimension is a separate view of the same gap. Do not add region, product, and channel percentages together. Offsetting movements can produce shares above 100%.")
    if metric=="revenue":
        st.subheader("Volume or price?")
        v,p = st.columns(2)
        v.metric("Volume effect",fmt(result["volume_effect"]))
        p.metric("Price / mix effect",fmt(result["price_effect"]))
    st.subheader("Decision and next steps")
    recovery,margin,cost=st.columns(3)
    recovery_rate=recovery.slider("Recoverable share of exposed sales",0,100,50,step=5,key="recovery")/100
    margin_rate=margin.slider("Contribution margin assumption",0,100,30,step=5,key="margin")/100
    intervention_cost=cost.number_input("Intervention cost (USD)",min_value=0.,value=500.,step=100.,key="cost")
    action=recommend(result,operations,recovery_rate,margin_rate,intervention_cost)
    st.markdown(f"**{action['issue']}** · Owner: {action['owner']}")
    st.write(action["action"])
    st.caption(action["success_measure"])
    if action["evidence"]:
        with st.expander("Operational evidence supporting the decision"):
            for line in action["evidence"]:
                st.text(line)
    exposed,potential,net=st.columns(3)
    exposed.metric("Exposed revenue",f"${action['exposed_revenue']:,.0f}")
    potential.metric("Potential recovered revenue",f"${action['potential_revenue']:,.0f}")
    net.metric("Scenario value after cost",f"${action['net_value']:,.0f}")
    if action["break_even_recovery"] is not None:
        st.caption(f"Break-even recovery: {action['break_even_recovery']:.1%}. Above 100% means the intervention does not pay back under these assumptions.")
    st.caption("Scenario estimates, not realized gains. Exposed revenue uses the four-week baseline and only cells with corroborating availability evidence. Synthetic operational records demonstrate the workflow; causal impact requires a controlled comparison.")
    with st.expander("Segment evidence and investigation export"):
        st.caption("Weekly analyst review budget: three segment signals, ranked by score × absolute KPI gap. Remaining evidence stays visible; it is not removed from detection.")
        st.dataframe(queue(evidence,week),hide_index=True,use_container_width=True)
        st.dataframe(evidence[evidence.week.eq(week)],hide_index=True,use_container_width=True)
        st.download_button("Download driver detail",result["cells"].drop(columns="aligned_delta").to_csv(index=False),file_name=f"autoroot-drivers-{week:%Y-%m-%d}.csv",mime="text/csv")
        st.download_button("Download investigation brief",result["narrative"],file_name=f"autoroot-brief-{week:%Y-%m-%d}.txt")
        review=st.selectbox("Analyst disposition",["Unreviewed","Confirmed movement","Dismissed alert","Needs more evidence"],key="review")
        review_note=st.text_input("Review reason",key="review_note")
        review_record={"week":week.strftime("%Y-%m-%d"),"metric":metric,"method":method,"status":review,"reason":review_note,"source_sha256":sales_hash}
        st.download_button("Download review record",json.dumps(review_record,indent=2),file_name=f"autoroot-review-{week:%Y-%m-%d}.json",mime="application/json")
        st.caption("Review records are exported for your audit trail. This session does not write them into the public dataset or retrain the detector.")
with validation:
    st.subheader("Measured against known events")
    st.caption("Exact week-level scoring after 26 clean calibration weeks. Labels are used only here, never by the detector. Units evaluation excludes the price-only event.")
    if labels is not None:
        scores = evaluate(weekly,labels,metric)
        st.dataframe(scores,hide_index=True,use_container_width=True,column_config={name:st.column_config.NumberColumn(format="%.3f") for name in ["precision","recall","f1"]})
        st.subheader("Scenario ledger")
        ledger = labels[["id","week","name","region","sku","channel",f"injected_{metric}_delta"]].copy()
        ledger["Detected"] = ledger.week.isin(weekly.loc[weekly[method],"week"])
        st.dataframe(ledger,hide_index=True,use_container_width=True)
    else:
        st.info("No labeled outcomes are supplied for this feed. Precision and recall are not available; unreviewed weeks are not assumed to be normal.")
    benchmark=ROOT/"reports"/"benchmark"/"summary.csv"
    if benchmark.exists():
        st.subheader("Frozen future-period benchmark")
        st.dataframe(pd.read_csv(benchmark).query("metric == @metric"),hide_index=True,use_container_width=True)
        st.caption("Five fresh seeds × 52 future weeks. The old demo is development data. Settings were frozen before testing; intervals resample whole seeds. All misses remain in the scorecard.")
    st.caption("Known simulation scenarios demonstrate detection behavior; these scores are not a guarantee on operational data.")
with methodology:
    st.subheader("A reproducible analyst workflow")
    st.markdown("""1. **Model the sales panel.** Seeded demand, annual seasonality, trend, regional factors, channel mix, and independent noise produce 37,440 segment-week records.
2. **Check the data.** Nulls, duplicates, negative values, missing weeks, and incomplete histories stop the warehouse load. DuckDB stores one fact table and three dimensions.
3. **Monitor with prior data.** Rolling Z-score uses the previous 12 weeks. Seasonal decomposition fits a robust trend and annual Fourier terms to prior observations. Isolation Forest trains on past levels and week/year changes.
4. **Catch local changes.** The combined monitor adds seasonal alerts across region, product, and channel panels. More panels improve coverage but increase false-alert risk.
5. **Explain the deviation.** The previous four weeks form a segment baseline. Signed contributions reconcile to the total gap; the revenue bridge separates units from price.
6. **Validate the business cause.** Sales identify where a movement occurred. Inventory, campaign, pricing, and operational records are needed to establish why.""")
    st.info("Synthetic sales and operational evidence illustrate the workflow. Five fresh-seed future periods test robustness. Panel thresholds increase with the number of comparisons, but approximate seasonal scores do not guarantee a formal false-discovery rate. Uploaded CSVs run the Python detector; scheduled monitoring validates and appends new complete weeks.")
    st.json(quality)
st.divider()
st.caption(f"AUTOROOT / Reproducible sales investigations / {source} / {sales.week.min():%Y}–{sales.week.max():%Y}")
