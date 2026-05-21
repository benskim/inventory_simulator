from __future__ import annotations

import math

import pandas as pd
import streamlit as st


DEFAULT_PLT_MONTHLY_COST = 30000
DEFAULT_HOLDING_COST_RATE = 6.5

CATEGORY_MASTER_DEFAULTS: dict[str, dict[str, float | int]] = {
    "원자재": {"annual_obs_rate": 0.08, "qty_per_pallet": 200},
    "전장부품": {"annual_obs_rate": 0.15, "qty_per_pallet": 500},
    "기능성모듈": {"annual_obs_rate": 0.12, "qty_per_pallet": 2},
    "기타": {"annual_obs_rate": 0.05, "qty_per_pallet": 100},
}


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


def _resolve_category_series(dataframe: pd.DataFrame) -> pd.Series:
    if "Category" in dataframe.columns:
        return dataframe["Category"].astype("string").fillna("기타").str.strip()
    return pd.Series(["기타"] * len(dataframe), index=dataframe.index, dtype="string")


def calculate_dead_stock_amount(project_master_df: pd.DataFrame, inventory_bom_df: pd.DataFrame, project_id: str) -> int:
    """Baseline dead-stock amount for selected project: Σ(Unit_Cost × Required_Qty)."""
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


def calculate_total_risk_cost(
    project_master_df: pd.DataFrame,
    inventory_bom_df: pd.DataFrame,
    project_id: str,
    delay_months: int,
    plt_monthly_cost: int,
    holding_cost_rate: float,
) -> tuple[int, int, int, int]:
    """Calculate total risk cost with category-aware factors and monthly prorating."""
    project_keys = project_master_df[["Project_ID"]].copy()
    project_keys["Project_ID"] = project_keys["Project_ID"].astype("string").str.strip()

    bom = inventory_bom_df.copy()
    bom["Associated_Project"] = bom["Associated_Project"].astype("string").str.strip()
    bom = bom.merge(project_keys, left_on="Associated_Project", right_on="Project_ID", how="inner")
    selected = bom[bom["Project_ID"] == project_id].copy()

    if selected.empty:
        return 0, 0, 0, 0

    selected["재고원가"] = selected["Unit_Cost"] * selected["Required_Qty"]
    selected["카테고리"] = _resolve_category_series(selected)

    annual_obs_map = {
        category: float(config["annual_obs_rate"]) for category, config in CATEGORY_MASTER_DEFAULTS.items()
    }
    qty_per_pallet_map = {
        category: int(config["qty_per_pallet"]) for category, config in CATEGORY_MASTER_DEFAULTS.items()
    }

    selected["연간진부화비율"] = selected["카테고리"].map(annual_obs_map).fillna(annual_obs_map["기타"])
    selected["PLT환산계수"] = selected["카테고리"].map(qty_per_pallet_map).fillna(qty_per_pallet_map["기타"])
    selected["차지하는_PLT수"] = (
        (selected["Required_Qty"] / selected["PLT환산계수"]).apply(math.ceil).astype("int64")
    )

    yard_cost = (selected["차지하는_PLT수"] * plt_monthly_cost * delay_months).sum()
    capital_cost = (
        selected["재고원가"] * ((holding_cost_rate / 100) / 12) * delay_months
    ).sum()
    obsolescence_cost = (selected["재고원가"] * (selected["연간진부화비율"] / 12) * delay_months).sum()

    total_risk_cost = round(yard_cost + capital_cost + obsolescence_cost, 0)
    baseline_dead_stock = round(selected["재고원가"].sum(), 0)
    return int(baseline_dead_stock), int(round(yard_cost, 0)), int(round(capital_cost, 0)), int(total_risk_cost)


def render_dead_stock_simulator(
    project_master_df: pd.DataFrame,
    inventory_bom_df: pd.DataFrame,
) -> tuple[str, int, int, str]:
    """Render project selector/slider and category-linked cost simulation."""
    st.markdown("#### 연산 로직: 총리스크비용 = 야드보관비용 + 자본기회비용(연이율/12×지연개월) + 진부화손실(연간진부화율/12×지연개월)")

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

    control_col1, control_col2, control_col3 = st.columns(3)
    selected_project_id = control_col1.selectbox("Project 선택", project_ids)
    delay_months = control_col2.slider("지연 기간(개월)", min_value=0, max_value=12, value=0)
    holding_cost_rate = control_col3.number_input("연간 금융비용율(%)", min_value=0.0, max_value=100.0, value=DEFAULT_HOLDING_COST_RATE, step=0.1)
    plt_monthly_cost = st.number_input("PLT당 월 보관료(원)", min_value=0, value=DEFAULT_PLT_MONTHLY_COST, step=1000)

    base_dead_stock, yard_cost, capital_cost, total_risk_cost = calculate_total_risk_cost(
        project_master_df,
        inventory_bom_df,
        selected_project_id,
        delay_months,
        int(plt_monthly_cost),
        float(holding_cost_rate),
    )

    st.metric("총 리스크 비용 (자본 동결 + 보관 + 진부화)", f"₩{total_risk_cost:,.0f}")
    st.caption(
        f"기준 재고원가(Σ단가×수량): ₩{base_dead_stock:,.0f} | "
        f"야드보관비용: ₩{yard_cost:,.0f} | 자본기회비용: ₩{capital_cost:,.0f}"
    )
    return selected_project_id, delay_months, total_risk_cost, f"₩{total_risk_cost:,.0f}"
