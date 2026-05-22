from __future__ import annotations

import math
import re

import pandas as pd
import streamlit as st


DEFAULT_PLT_MONTHLY_COST = 30000
DEFAULT_HOLDING_COST_RATE = 6.5

CATEGORY_MASTER_DEFAULTS: dict[str, dict[str, float | int]] = {
    "원자재": {"annual_obs_rate": 8.0, "qty_per_pallet": 200},
    "전장부품": {"annual_obs_rate": 15.0, "qty_per_pallet": 500},
    "기능성모듈": {"annual_obs_rate": 12.0, "qty_per_pallet": 2},
    "기타": {"annual_obs_rate": 5.0, "qty_per_pallet": 100},
}

INTOAL_KEYWORD_MAPPING: dict[str, list[str]] = {
    "원자재": ["철판", "AL", "알루미늄", "프로파일", "SUS", "스텐", "강판", "EGI", "PIPE", "파이프", "앵글", "브라켓", "PLATE", "플레이트", "BASE", "베이스", "볼트", "너트", "와셔", "스크류", "리벳", "힌지", "경첩", "도어락"],
    "전장부품": ["AD보드", "PCB", "컨트롤러", "인버터", "SMPS", "파워", "POWER", "어댑터", "케이블", "CABLE", "하네스", "HARNESS", "커넥터", "CONNECTOR", "젠더", "터치패널", "터치스크린", "스위치", "SWITCH", "차단기", "릴레이"],
    "기능성모듈": ["LCD", "OLED", "패널", "PANEL", "모니터", "MONITOR", "디스플레이", "PC", "컴퓨터", "메인보드", "CPU", "SSD", "RAM", "FAN", "팬", "쿨러", "COOLER", "환풍기", "영수증프린터", "지문인식기"],
}


def calculate_risk_metrics(dataframe: pd.DataFrame) -> pd.DataFrame:
    calculated = dataframe.copy()
    calculated["risk_cost_krw"] = (calculated["expected_delay_days"] * calculated["penalty_per_day_krw"]).astype("int64")
    calculated["risk_ratio_pct"] = ((calculated["risk_cost_krw"] / calculated["monthly_revenue_krw"].replace(0, 1)) * 100).round(2)
    calculated["red_alert"] = calculated["risk_ratio_pct"] >= 8.0
    return calculated


def summarize_kpi(dataframe: pd.DataFrame) -> dict[str, int | float]:
    return {
        "total_revenue_krw": int(dataframe["monthly_revenue_krw"].sum()),
        "total_risk_cost_krw": int(dataframe["risk_cost_krw"].sum()),
        "red_alert_count": int(dataframe["red_alert"].sum()),
        "average_risk_ratio_pct": float(dataframe["risk_ratio_pct"].mean().round(2)),
    }


def _predict_category_from_item_name(item_names: pd.Series) -> pd.Series:
    normalized = item_names.astype("string").fillna("").str.upper()
    predicted = pd.Series(["기타"] * len(normalized), index=normalized.index, dtype="string")
    for category, keywords in INTOAL_KEYWORD_MAPPING.items():
        pattern = "|".join(re.escape(keyword.upper()) for keyword in keywords)
        matched = normalized.str.contains(pattern, regex=True, na=False)
        predicted = predicted.where(~matched, category)
    return predicted


def _resolve_category_series(dataframe: pd.DataFrame) -> pd.Series:
    if "Category" in dataframe.columns:
        category = dataframe["Category"].astype("string").str.strip()
        predicted = _predict_category_from_item_name(dataframe["Item_Name"])
        return category.where(category.notna() & (category != ""), predicted).fillna("기타")
    return _predict_category_from_item_name(dataframe["Item_Name"]).fillna("기타")


def _merge_project_bom(project_master_df: pd.DataFrame, inventory_bom_df: pd.DataFrame, project_id: str) -> pd.DataFrame:
    project_keys = project_master_df[["Project_ID"]].copy()
    project_keys["Project_ID"] = project_keys["Project_ID"].astype("string").str.strip()
    bom = inventory_bom_df.copy()
    bom["Associated_Project"] = bom["Associated_Project"].astype("string").str.strip()
    merged = bom.merge(project_keys, left_on="Associated_Project", right_on="Project_ID", how="inner")
    return merged[merged["Project_ID"] == project_id].copy()


def calculate_total_risk_cost(selected: pd.DataFrame, delay_months: int, plt_monthly_cost: int, holding_cost_rate: float) -> tuple[int, int, int, int, int]:
    if selected.empty:
        return 0, 0, 0, 0, 0
    selected = selected.copy()
    selected["재고원가"] = selected["Unit_Cost"] * selected["Required_Qty"]
    selected["카테고리"] = _resolve_category_series(selected)

    annual_obs_map = {k: float(v["annual_obs_rate"]) for k, v in CATEGORY_MASTER_DEFAULTS.items()}
    qty_per_pallet_map = {k: int(v["qty_per_pallet"]) for k, v in CATEGORY_MASTER_DEFAULTS.items()}
    selected["연간진부화비율"] = selected["카테고리"].map(annual_obs_map).fillna(annual_obs_map["기타"])
    selected["PLT환산계수"] = selected["카테고리"].map(qty_per_pallet_map).fillna(qty_per_pallet_map["기타"])
    selected["차지하는_PLT수"] = (selected["Required_Qty"] / selected["PLT환산계수"]).apply(math.ceil).astype("int64")

    yard_cost = (selected["차지하는_PLT수"] * plt_monthly_cost * delay_months).sum()
    capital_cost = (selected["재고원가"] * ((holding_cost_rate / 100) / 12) * delay_months).sum()
    obsolescence_cost = (selected["재고원가"] * ((selected["연간진부화비율"] / 100) / 12) * delay_months).sum()
    baseline = round(selected["재고원가"].sum(), 0)
    total = round(yard_cost + capital_cost + obsolescence_cost, 0)
    return int(baseline), int(round(yard_cost, 0)), int(round(capital_cost, 0)), int(round(obsolescence_cost, 0)), int(total)


def render_dead_stock_simulator(project_master_df: pd.DataFrame, inventory_bom_df: pd.DataFrame) -> tuple[str, int, int, str]:
    project_ids = project_master_df["Project_ID"].astype("string").str.strip().dropna().drop_duplicates().sort_values().tolist()
    if len(project_ids) == 0:
        st.error("Project_Master에 유효한 Project_ID가 없습니다.")
        st.stop()

    selected_project_id = st.selectbox("Project 선택", project_ids)

    c1, c2, c3 = st.columns(3)
    delay_months = c1.slider("지연 기간(개월)", min_value=0, max_value=12, value=0)
    holding_cost_rate = c2.number_input("연간 금융비용율(%)", min_value=0.0, max_value=100.0, value=DEFAULT_HOLDING_COST_RATE, step=0.1)
    plt_monthly_cost = c3.number_input("PLT당 월 보관료(원)", min_value=0, value=DEFAULT_PLT_MONTHLY_COST, step=1000)

    selected_bom = _merge_project_bom(project_master_df, inventory_bom_df, selected_project_id)
    selected_bom["Category"] = _resolve_category_series(selected_bom)

    editable = st.data_editor(
        selected_bom[["Item_Code", "Item_Name", "Unit_Cost", "Required_Qty", "Category"]],
        hide_index=True,
        use_container_width=True,
        column_config={"Category": st.column_config.SelectboxColumn("Category", options=list(CATEGORY_MASTER_DEFAULTS.keys()))},
        key=f"category_editor_{selected_project_id}",
    )

    selected_bom.loc[editable.index, "Category"] = editable["Category"].astype("string")
    base_dead_stock, yard_cost, capital_cost, obsolescence_cost, total_risk_cost = calculate_total_risk_cost(
        selected_bom,
        delay_months,
        int(plt_monthly_cost),
        float(holding_cost_rate),
    )

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Dead Stock (재고 원가)", f"₩{base_dead_stock:,.0f}")
        st.caption("Dead Stock = Σ(Unit_Cost × Required_Qty) (지연 개월수와 무관)")
        st.caption("**카테고리별 [연간 진부화비율/qty to plt] 안내 :**")
        st.caption("원자재(연8%/200), 전장부품(연15%/500), 기능성모듈(연12%/2), 기타(연5%/100).")
        st.caption("Category는 Item_Name 기반 자동 예측되며, 아래 드롭다운에서 사용자가 수정할 수 있습니다. 빈 값은 기타 처리됩니다.")

    with m2:
        st.metric("총 리스크 비용", f"₩{total_risk_cost:,.0f}")
        st.caption("**총 손실 = 보관비용 + 자본기회비용 + 진부화손실비용**")
        st.caption(f"* 보관비용 = PLT당 월 보관료 × Q(PLT환산) × 지연 개월수  (현재: ₩{yard_cost:,.0f})")
        st.caption(f"* 자본기회비용 = 재고원가 × ((연간 금융비용율/100) ÷ 12) × 지연 개월수  (현재: ₩{capital_cost:,.0f})") #월별 가중평균자본비용
        st.caption(f"* 진부화손실비용 = 재고원가 × ((연간 진부화비율/100) ÷ 12) × 지연 개월수  (현재: ₩{obsolescence_cost:,.0f})")
        
    return selected_project_id, delay_months, total_risk_cost, f"₩{total_risk_cost:,.0f}"

DAILY_PENALTY_RATE: float = 0.001  # 일일 지체상금 요율 0.1%


def _sanitize_to_non_negative_int(value: object) -> int:
    if value is None:
        value = 0
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            value = 0
        else:
            try:
                numeric = float(stripped.replace(",", ""))
                if math.isnan(numeric):
                    value = 0
                else:
                    value = numeric
            except (TypeError, ValueError):
                value = 0
    else:
        try:
            if math.isnan(value):
                value = 0
        except (TypeError, ValueError):
            pass

    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0

    return max(0, value)


def calculate_delay_penalty(order_value: int, delay_days: int) -> dict:
    safe_order_value = _sanitize_to_non_negative_int(order_value)
    safe_delay_days = _sanitize_to_non_negative_int(delay_days)

    penalty_amount = int(safe_order_value * safe_delay_days * DAILY_PENALTY_RATE)
    formula_text = f"₩{safe_order_value:,.0f} × {safe_delay_days}일 × {DAILY_PENALTY_RATE * 100:.1f}% = ₩{penalty_amount:,.0f}"

    return {
        "penalty_amount": penalty_amount,
        "formula_breakdown": {
            "order_value": safe_order_value,
            "delay_days": safe_delay_days,
            "daily_rate": DAILY_PENALTY_RATE,
        },
        "formula_text": formula_text,
    }

