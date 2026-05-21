from __future__ import annotations

import pandas as pd


def calculate_risk_metrics(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calculate deterministic risk metrics with vectorized arithmetic operations."""
    calculated = dataframe.copy()
    calculated["risk_cost_krw"] = (
        calculated["expected_delay_days"] * calculated["penalty_per_day_krw"]
    ).astype("int64")
    calculated["risk_ratio_pct"] = (
        (calculated["risk_cost_krw"] / calculated["monthly_revenue_krw"].replace(0, 1)) * 100
    ).round(2)
    calculated["red_alert"] = calculated["risk_ratio_pct"] >= 8.0
    return calculated


def summarize_kpi(dataframe: pd.DataFrame) -> dict[str, int | float]:
    """Return aggregate KPI values for dashboard."""
    return {
        "total_revenue_krw": int(dataframe["monthly_revenue_krw"].sum()),
        "total_risk_cost_krw": int(dataframe["risk_cost_krw"].sum()),
        "red_alert_count": int(dataframe["red_alert"].sum()),
        "average_risk_ratio_pct": float(dataframe["risk_ratio_pct"].mean().round(2)),
    }
