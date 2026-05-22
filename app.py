from __future__ import annotations

import pandas as pd
import streamlit as st

from data.preset import DEMO_BOM, DEMO_DELAY_DAYS, DEMO_PROJECT
from src import data_loader
from src import engine
from src import ui


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
    project_df, bom_df = data_loader.render_upload_and_validation_interface()

    if project_df is not None or bom_df is not None:
        st.session_state.demo_mode = False
        st.session_state.demo_data = None

    slider_days = st.slider("납기 지연 일수", min_value=0, max_value=365, value=DEMO_DELAY_DAYS)

    frozen_capital = 0
    penalty_amount = 0

    if st.session_state.demo_mode and st.session_state.demo_data:
        df_schedule = st.session_state.demo_data["schedule"]
        _ = st.session_state.demo_data["inventory"]
        penalty_result = engine.calculate_delay_penalty(
            order_value=int(df_schedule["Order_Value"].iloc[0]),
            delay_days=DEMO_DELAY_DAYS,
        )
        penalty_amount = penalty_result["penalty_amount"]
        st.session_state.simulation_run = True

        ui.render_status_banner()
        ui.render_kpi_cards(frozen_capital, penalty_amount)
        ui.render_action_plan(frozen_capital, penalty_amount)
        st.caption(f"납기지연손실금액 산식: {penalty_result['formula_text']}")

    elif project_df is not None and bom_df is not None:
        st.markdown("### Dead Stock 시뮬레이션")
        _, delay_months, total_risk_cost, _ = ui.render_dead_stock_simulator(project_df, bom_df)

        # 총 손실 공식은 기존 월 단위를 그대로 유지 (일 슬라이더와 분리)
        _ = delay_months
        frozen_capital = total_risk_cost

        df_schedule = project_df
        first_order_value = int(df_schedule["Order_Value"].iloc[0]) if len(df_schedule) > 0 else 0
        penalty_result = engine.calculate_delay_penalty(
            order_value=first_order_value,
            delay_days=slider_days,
        )

        penalty_amount = 0
        st.session_state.simulation_run = True

        ui.render_status_banner()
        ui.render_kpi_cards(frozen_capital, penalty_amount)
        ui.render_action_plan(frozen_capital, penalty_amount)
        st.caption("동결자금 산식(월기준): 보관비용 + 자본기회비용 + 진부화손실비용")
        st.caption(f"(참고) 납기지연손실금액 일단위 산식: {penalty_result['formula_text']}")

    else:
        st.info("📂 엑셀 파일을 업로드하거나 데모 버튼을 클릭하세요.")
        ui.render_kpi_cards(0, 0)


if __name__ == "__main__":
    main()
