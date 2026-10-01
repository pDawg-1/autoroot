import plotly.graph_objects as go

TEAL = "#087f73"
RED = "#d45b45"

def style(fig, height=340):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10,r=10,t=25,b=15), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Arial", color="#19332f"), legend=dict(orientation="h", y=1.12), hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e5eae5", zeroline=False)
    return fig

def timeline(weekly, metric, method, selected):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly.week, y=weekly[metric], name="Actual", line=dict(color=TEAL,width=2.5)))
    fig.add_trace(go.Scatter(x=weekly.week,y=weekly.expected,name="Seasonal forecast",line=dict(color="#98a9a1",dash="dot")))
    flagged = weekly[weekly[method]]
    fig.add_trace(go.Scatter(x=flagged.week,y=flagged[metric],mode="markers",name="Alerts",marker=dict(color=RED,size=9,line=dict(color="white",width=2))))
    fig.add_vline(x=selected.timestamp()*1000, line_color="#19332f",line_dash="dash",line_width=1)
    fig.update_yaxes(title=metric.title(), tickprefix="$" if metric=="revenue" else "")
    return style(fig)

def waterfall(result):
    top = result["top"]
    values = top.delta.tolist()
    labels = [f"{r.region} · {r.sku}<br>{r.channel}" for r in top.itertuples()]
    labels += ["Other segments", "Net change"]
    values += [result["gap"]-sum(values), 0]
    fig = go.Figure(go.Waterfall(x=labels,y=values,measure=["relative"]*(len(values)-1)+["total"], increasing=dict(marker=dict(color=TEAL)),decreasing=dict(marker=dict(color=RED)),totals=dict(marker=dict(color="#19332f")),connector=dict(line=dict(color="#b8c4bb"))))
    fig.update_yaxes(tickprefix="$" if result["metric"]=="revenue" else "")
    return style(fig, 350)
