from __future__ import annotations

import pandas as pd
import streamlit as st

from data.preset import DEMO_BOM, DEMO_DELAY_DAYS, DEMO_PROJECT
from src import ui
from src import data_loader
from src import engine


for key, default in [
    ("simulation_run", False),
    ("demo_mode", False),
    ("demo_data", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def main() -> None:
    st.set_page_config(page_title="Inventory Risk Simulator", layout="wide")
    st.title("초경량 결정론적 재고 리스크 시뮬레이터")

    if st.button("⚡ LGES 오하이오향 3개월 지연 데모 실행", use_container_width=True):
        try:
            df_schedule = pd.DataFrame([DEMO_PROJECT])
            df_schedule["Delivery_Date"] = pd.to_datetime(df_schedule["Delivery_Date"])
            df_inventory = pd.DataFrame([DEMO_BOM])

            st.session_state.demo_data = {
                "schedule": df_schedule,
                "inventory": df_inventory,
            }
            st.session_state.demo_mode = True
            st.session_state.simulation_run = True
        except Exception as e:  # noqa: BLE001
            st.error(f"데모 데이터 생성 실패: {e}")
            st.stop()

    st.markdown("### 입력 데이터 업로드 및 스키마 검증")
    schedule_file, inventory_file = data_loader.render_upload_and_validation_interface()

    if schedule_file is not None or inventory_file is not None:
        st.session_state.demo_mode = False
        st.session_state.demo_data = None

    slider_value = st.slider("납기 지연 일수", min_value=0, max_value=365, value=DEMO_DELAY_DAYS)

    if st.session_state.demo_mode and st.session_state.demo_data:
        df_schedule = st.session_state.demo_data["schedule"]
        df_inventory = st.session_state.demo_data["inventory"]
        delay_days = DEMO_DELAY_DAYS
    elif schedule_file is not None and inventory_file is not None:
        df_schedule = schedule_file
        df_inventory = inventory_file
        delay_days = slider_value
    else:
        df_schedule = None
        df_inventory = None

    if df_schedule is not None and df_inventory is not None:
        frozen_capital, *_ = engine.calculate_total_risk_cost(
            selected=df_inventory,
            delay_months=0,
            plt_monthly_cost=engine.DEFAULT_PLT_MONTHLY_COST,
            holding_cost_rate=engine.DEFAULT_HOLDING_COST_RATE,
        )
        penalty_result = engine.calculate_delay_penalty(
            order_value=int(df_schedule["Order_Value"].iloc[0]),
            delay_days=delay_days,
        )

        ui.render_status_banner()
        ui.render_kpi_cards(frozen_capital, penalty_result["penalty_amount"])
        ui.render_risk_summary()
        ui.render_action_plan(frozen_capital, penalty_result["penalty_amount"])
    else:
        st.info("📂 엑셀 파일을 업로드하거나 데모 버튼을 클릭하세요.")
        ui.render_kpi_cards(0, 0)


if __name__ == "__main__":
    main()
