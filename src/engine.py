from __future__ import annotations

import pandas as pd
import streamlit as st


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


def calculate_dead_stock_amount(project_master_df: pd.DataFrame, inventory_bom_df: pd.DataFrame, project_id: str) -> int:
    """Calculate dead-stock amount for one project with vectorized arithmetic.

    Formula: Dead_Stock = Σ(Unit_Cost × Required_Qty)
    """
    project_keys = project_master_df[["Project_ID"]].copy()
    project_keys["Project_ID"] = project_keys["Project_ID"].astype("string").str.strip()

    bom = inventory_bom_df.copy()
    bom["Associated_Project"] = bom["Associated_Project"].astype("string").str.strip()

    merged = bom.merge(
        project_keys,
        left_on="Associated_Project",
        right_on="Project_ID",
        how="inner",
    )

    selected_rows = merged[merged["Project_ID"] == project_id]
    dead_stock_amount = round((selected_rows["Unit_Cost"] * selected_rows["Required_Qty"]).sum(), 0)
    return int(dead_stock_amount)


def render_dead_stock_simulator(
    project_master_df: pd.DataFrame,
    inventory_bom_df: pd.DataFrame,
) -> tuple[str, int, int, str]:
    """Render project selector/slider and return calculated dead-stock amount."""
    project_ids = (
        project_master_df["Project_ID"]
        .astype("string")
        .str.strip()
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if len(project_ids) == 0:
        st.error("Project_Master에 유효한 Project_ID가 없습니다.")
        st.stop()

    selected_project_id = st.selectbox("Project 선택", project_ids)
    delay_months = st.slider("지연 기간(개월)", min_value=1, max_value=12, value=1)

    dead_stock_amount = calculate_dead_stock_amount(project_master_df, inventory_bom_df, selected_project_id)
    dead_stock_display = f"₩{dead_stock_amount:,.0f}"

    st.metric("Dead Stock (자본 동결 금액)", dead_stock_display)
    st.caption(f"선택 프로젝트: {selected_project_id} / 지연 기간: {delay_months}개월")
    return selected_project_id, delay_months, dead_stock_amount, dead_stock_display
