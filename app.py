from __future__ import annotations

import pandas as pd
import streamlit as st

from data.preset import (
    DEMO_BOM_S1,
    DEMO_BOM_S2,
    DEMO_DELAY_DAYS_S1,
    DEMO_DELAY_DAYS_S2,
    DEMO_PROJECT_S1,
    DEMO_PROJECT_S2,
)
from src import data_loader, engine, ui


for key, default in [
    ("simulation_run", False),
    ("demo_mode", False),
    ("demo_scenario", "NONE"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def _calculate_frozen_cash(df_inventory: pd.DataFrame) -> int:
    baseline, *_ = engine.calculate_total_risk_cost(
        selected=df_inventory,
        delay_months=0,
        plt_monthly_cost=engine.DEFAULT_PLT_MONTHLY_COST,
        holding_cost_rate=engine.DEFAULT_HOLDING_COST_RATE,
    )
    return int(baseline)


def main() -> None:
    st.set_page_config(page_title="Inventory Risk Simulator", layout="wide")
    st.title("초경량 결정론적 재고 리스크 시뮬레이터")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("⚡ [S1] LGES 오하이오 3개월 지연 데모", use_container_width=True):
            st.session_state.demo_mode = True
            st.session_state.demo_scenario = "S1"
            st.session_state.simulation_run = True
    with col_s2:
        if st.button("⚡ [S2] 전장부품 쇼티지 21일 지연 데모", use_container_width=True):
            st.session_state.demo_mode = True
            st.session_state.demo_scenario = "S2"
            st.session_state.simulation_run = True

    st.markdown("### 입력 데이터 업로드 및 스키마 검증")
    schedule_file, inventory_file = data_loader.render_upload_and_validation_interface()

    if schedule_file is not None or inventory_file is not None:
        st.session_state.demo_mode = False
        st.session_state.demo_scenario = "NONE"

    slider_value = st.slider("납기 지연 일수", min_value=0, max_value=365, value=21)
    scenario = st.session_state.demo_scenario

    if scenario == "S1":
        df_schedule = pd.DataFrame([DEMO_PROJECT_S1])
        df_inventory = pd.DataFrame([DEMO_BOM_S1])
        delay_days = DEMO_DELAY_DAYS_S1
    elif scenario == "S2":
        df_schedule = pd.DataFrame([DEMO_PROJECT_S2])
        df_inventory = pd.DataFrame([DEMO_BOM_S2])
        delay_days = DEMO_DELAY_DAYS_S2
    elif schedule_file is not None and inventory_file is not None:
        df_schedule = schedule_file
        df_inventory = inventory_file
        delay_days = slider_value
    else:
        df_schedule = None
        df_inventory = None
        delay_days = 0

    if df_schedule is not None and df_inventory is not None:
        if scenario == "NONE":
            st.markdown("### Dead Stock 시뮬레이션")
            _, _, total_risk_cost, _ = ui.render_dead_stock_simulator(df_schedule, df_inventory)
            frozen_capital = total_risk_cost
        else:
            frozen_capital = _calculate_frozen_cash(df_inventory)

        penalty_result = engine.calculate_delay_penalty(
            order_value=int(df_schedule["Order_Value"].iloc[0]),
            delay_days=delay_days,
        )

        ui.render_status_banner(st.session_state.simulation_run, scenario)
        ui.render_kpi_cards(frozen_capital, penalty_result["penalty_amount"])
        ui.render_risk_summary()
        ui.render_action_plan(frozen_capital, penalty_result["penalty_amount"], scenario)
        st.caption(f"납기지연손실 산식: {penalty_result['formula_text']}")
    else:
        st.info("📂 파일을 업로드하거나 데모 버튼을 클릭하세요.")
        ui.render_status_banner(st.session_state.simulation_run, scenario)
        ui.render_kpi_cards(0, 0)


if __name__ == "__main__":
    main()
