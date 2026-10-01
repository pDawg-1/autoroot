"""Past-only statistical monitoring at total and segment level."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

METHODS = ["rolling_z", "seasonal", "isolation_forest", "ensemble"]
WARMUP = 26

def design(t):
    t = np.asarray(t)
    return np.column_stack([np.ones(len(t)), t / 52, np.sin(2*np.pi*t/52), np.cos(2*np.pi*t/52), np.sin(4*np.pi*t/52), np.cos(4*np.pi*t/52)])

def seasonal_residual(values):
    """Forecast with trend + annual Fourier seasonality, fitted on prior rows only.

    This is a causal regression decomposition, avoiding centered full-series filters.
    """
    values = np.asarray(values, dtype=float)
    expected = np.full(len(values), np.nan)
    score = np.full(len(values), np.nan)
    for i in range(WARMUP, len(values)):
        x = design(np.arange(i))
        y = np.log(np.maximum(values[:i], 1))
        # Iteratively reweighted fit reduces contamination from earlier spikes.
        weights = np.ones(i)
        beta = np.zeros(x.shape[1])
        for _ in range(5):
            beta = np.linalg.solve(x.T @ (weights[:, None]*x) + np.diag([1e-8, .01, .02, .02, .02, .02]), x.T @ (weights*y))
            residual = y - x @ beta
            scale = max(1.4826*np.median(np.abs(residual-np.median(residual))), .015)
            weights = np.minimum(1., 1.5*scale / np.maximum(np.abs(residual), 1e-9))
        pred = (design([i]) @ beta).item()
        expected[i] = np.exp(pred)
        # Operational noise floor prevents trivial deviations becoming alerts.
        scale = max(1.4826*np.median(np.abs(residual-np.median(residual))), .025)
        score[i] = (np.log(max(values[i], 1))-pred) / scale
    return expected, score

def monitor_series(frame, metric="revenue"):
    frame = frame.sort_values("week").reset_index(drop=True).copy()
    value = frame[metric].astype(float)
    previous = value.shift(1)
    mean = previous.rolling(12, min_periods=12).mean()
    std = previous.rolling(12, min_periods=12).std()
    frame["rolling_score"] = (value-mean) / std.clip(lower=mean.abs()*.01)
    frame["expected"], frame["seasonal_score"] = seasonal_residual(value)
    features = pd.DataFrame({"level": np.log(value.clip(lower=1)), "wow": value.pct_change(), "yoy": value.pct_change(52).fillna(0)})
    scores = np.full(len(frame), np.nan)
    flags = np.zeros(len(frame), dtype=bool)
    for i in range(WARMUP, len(frame)):
        history = features.iloc[1:i]
        model = IsolationForest(n_estimators=80, contamination=.04, random_state=42, n_jobs=1)
        model.fit(history)
        scores[i] = -model.decision_function(features.iloc[[i]])[0]
        flags[i] = model.predict(features.iloc[[i]])[0] == -1
    eligible = np.arange(len(frame)) >= WARMUP
    frame["eligible"] = eligible
    frame["rolling_z"] = eligible & frame.rolling_score.abs().gt(3)
    frame["seasonal"] = eligible & frame.seasonal_score.abs().gt(3)
    frame["isolation_score"] = scores
    frame["isolation_forest"] = eligible & flags
    # Seasonal evidence or agreement between independent raw-signal methods.
    frame["ensemble"] = frame.seasonal | (frame.rolling_z & frame.isolation_forest)
    return frame

def detect(sales, metric="revenue", segments=True):
    weekly = sales.groupby("week", as_index=False)[metric].sum()
    total = monitor_series(weekly, metric)
    evidence = []
    if segments:
        # Seasonal scores on marginal dimensions catch localized events diluted in totals.
        for dimension in ["region", "sku", "channel"]:
            grouped = sales.groupby(["week", dimension], as_index=False)[metric].sum()
            for segment, panel in grouped.groupby(dimension):
                panel = panel.sort_values("week").reset_index(drop=True)
                expected, score = seasonal_residual(panel[metric])
                for i in np.flatnonzero(np.abs(score) > 3):
                    evidence.append({"week": panel.week.iloc[i], "dimension": dimension, "segment": segment, "actual": float(panel[metric].iloc[i]), "expected": expected[i], "score": score[i]})
        events = pd.DataFrame(evidence, columns=["week", "dimension", "segment", "actual", "expected", "score"])
        segment_weeks = set(events.week)
        total["segment_alert"] = total.week.isin(segment_weeks)
        total["ensemble"] |= total.segment_alert
    else:
        events = pd.DataFrame(columns=["week", "dimension", "segment", "actual", "expected", "score"])
        total["segment_alert"] = False
    return total, events
