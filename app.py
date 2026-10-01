"""AutoRoot: weekly sales monitoring and investigation workspace."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st
from charts import timeline, waterfall
from detector import detect, METHODS
from evaluate import evaluate
from generate_data import generate
from root_cause import investigate
from warehouse import build_warehouse, validate

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

@st.cache_data
def load_data():
    if not (ROOT/"data"/"sales.csv").exists():
        generate(output=ROOT/"data")
    sales = pd.read_csv(ROOT/"data"/"sales.csv",parse_dates=["week"])
    labels = pd.read_csv(ROOT/"data"/"ground_truth.csv",parse_dates=["week"])
    with build_warehouse() as conn:
        kpis = conn.sql("SELECT * FROM kpi_weekly ORDER BY week").df()
    return sales,labels,kpis,validate(sales)

@st.cache_data
def analysis(metric):
    sales,_,_,_ = load_data()
    report = ROOT/"reports"/f"detections_{metric}.csv"
    evidence = ROOT/"reports"/f"evidence_{metric}.csv"
    # Precomputed files are produced by the same versioned Python pipeline.
    if report.exists() and evidence.exists():
        return pd.read_csv(report,parse_dates=["week"]),pd.read_csv(evidence,parse_dates=["week"])
    return detect(sales,metric)

sales,labels,kpis,quality = load_data()
with st.sidebar:
    st.markdown("## ◉ AutoRoot")
    st.caption("SALES INTELLIGENCE WORKSPACE")
    st.divider()
    metric = st.selectbox("Performance metric",["revenue","units"],format_func=str.title)
    method = st.selectbox("Detection method",METHODS,index=3,format_func=lambda x:{"rolling_z":"Rolling Z-score","seasonal":"Seasonal decomposition","isolation_forest":"Isolation Forest","ensemble":"Combined + segment monitoring"}[x])
    weekly,evidence = analysis(metric)
    alerts_only = st.toggle("Show alert weeks only",value=True)
    options = weekly.loc[weekly[method] if alerts_only else weekly.eligible,"week"].tolist()
    if not options:
        st.info("No alerts for this method. Showing monitored weeks.")
        options = weekly.loc[weekly.eligible,"week"].tolist()
    default_week = pd.Timestamp("2024-03-18")
    default_index = options.index(default_week) if default_week in options else len(options)-1
    week = st.selectbox("Investigation week",options,index=default_index,format_func=lambda w:w.strftime("%d %b %Y"))
    st.divider()
    st.caption("DATA COVERAGE")
    st.markdown("**104 weeks** · 2023–2024\n\n8 regions · 15 products · 3 channels")
    st.caption("Reproducible synthetic retail dataset · USD")

selected = weekly.loc[weekly.week.eq(week)].iloc[0]
result = investigate(sales,week,metric)
is_alert = bool(selected[method])
st.markdown('<p class="eyebrow">MONITOR → INVESTIGATE → EXPLAIN</p>',unsafe_allow_html=True)
left,right = st.columns([4,1])
with left:
    st.title("Every movement has a story.")
    st.caption("Weekly sales monitoring with a clear trail from the signal to the segments behind it.")
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
    st.markdown(f'<div class="brief">{result["narrative"]}</div>',unsafe_allow_html=True)
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
    with st.expander("Segment evidence and investigation export"):
        st.dataframe(evidence[evidence.week.eq(week)],hide_index=True,use_container_width=True)
        st.download_button("Download driver detail",result["cells"].drop(columns="aligned_delta").to_csv(index=False),file_name=f"autoroot-drivers-{week:%Y-%m-%d}.csv",mime="text/csv")
        st.download_button("Download investigation brief",result["narrative"],file_name=f"autoroot-brief-{week:%Y-%m-%d}.txt")
with validation:
    st.subheader("Measured against known events")
    st.caption("Exact week-level scoring after 26 clean calibration weeks. Labels are used only here, never by the detector. Units evaluation excludes the price-only event.")
    scores = evaluate(weekly,labels,metric)
    st.dataframe(scores,hide_index=True,use_container_width=True,column_config={name:st.column_config.NumberColumn(format="%.3f") for name in ["precision","recall","f1"]})
    st.subheader("Scenario ledger")
    ledger = labels[["id","week","name","region","sku","channel",f"injected_{metric}_delta"]].copy()
    ledger["Detected"] = ledger.week.isin(weekly.loc[weekly[method],"week"])
    st.dataframe(ledger,hide_index=True,use_container_width=True)
    st.caption("Known simulation scenarios demonstrate detection behavior; these scores are not a guarantee on operational data.")
with methodology:
    st.subheader("A reproducible analyst workflow")
    st.markdown("""1. **Model the sales panel.** Seeded demand, annual seasonality, trend, regional factors, channel mix, and independent noise produce 37,440 segment-week records.
2. **Check the data.** Nulls, duplicates, negative values, missing weeks, and incomplete histories stop the warehouse load. DuckDB stores one fact table and three dimensions.
3. **Monitor with prior data.** Rolling Z-score uses the previous 12 weeks. Seasonal decomposition fits a robust trend and annual Fourier terms to prior observations. Isolation Forest trains on past levels and week/year changes.
4. **Catch local changes.** The combined monitor adds seasonal alerts across region, product, and channel panels. More panels improve coverage but increase false-alert risk.
5. **Explain the deviation.** The previous four weeks form a segment baseline. Signed contributions reconcile to the total gap; the revenue bridge separates units from price.
6. **Validate the business cause.** Sales identify where a movement occurred. Inventory, campaign, pricing, and operational records are needed to establish why.""")
    st.info("Limitations: 104 weeks give only two annual cycles. Year-over-year features are unavailable for the first year. Fixed thresholds and the clean calibration period suit this demonstration; production monitoring needs longer history, multiplicity controls, and alert review.")
    st.json(quality)
st.divider()
st.caption("AUTOROOT  /  Reproducible sales investigations  /  Synthetic data · 2023–2024")
