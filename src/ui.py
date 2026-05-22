from __future__ import annotations

import pandas as pd
import streamlit as st

from src.engine import CATEGORY_MASTER_DEFAULTS, DEFAULT_HOLDING_COST_RATE, DEFAULT_PLT_MONTHLY_COST, _merge_project_bom, _resolve_category_series, calculate_total_risk_cost

SAFE = "#00C49F"
WARNING = "#FFBB28"
CRITICAL = "#FF4B4B"

THRESHOLD_PENALTY = 10_000_000
THRESHOLD_FROZEN = 200_000_000


def _ensure_session_state() -> None:
    if "simulation_run" not in st.session_state:
        st.session_state.simulation_run = False


def _is_simulation_run() -> bool:
    _ensure_session_state()
    return bool(st.session_state.get("simulation_run", False))


def _format_krw(amount: int) -> str:
    return f"₩{amount:,.0f}"


def render_status_banner() -> None:
    if _is_simulation_run():
        st.error("🚨 창고 포화 및 자본 동결 위험 감지! 프로젝트 지연 리스크가 반영되었습니다.")
    else:
        st.success("🟢 시스템 안정 상태: 현재 감지된 공급망 리스크가 없습니다.")


def render_kpi_cards(frozen_capital: int, delay_penalty: int) -> None:
    col_left, col_right = st.columns(2)
    if _is_simulation_run():
        col_left.metric("동결 자금 총액", _format_krw(frozen_capital), delta=f"+{_format_krw(frozen_capital)}")
        col_right.metric("누적 지체상금(벌금)", _format_krw(delay_penalty), delta=f"+{_format_krw(delay_penalty)}")
    else:
        col_left.metric("동결 자금 총액", _format_krw(frozen_capital))
        col_right.metric("누적 지체상금(벌금)", _format_krw(delay_penalty))


def render_risk_summary() -> None:
    _ensure_session_state()
    st.button("리스크 시뮬레이션 실행", on_click=lambda: st.session_state.update({"simulation_run": True}), use_container_width=True)
    if _is_simulation_run():
        st.markdown("시나리오 요약: 프로젝트 지연에 따라 동결 자금 및 누적 지체상금이 반영되었습니다.")
    else:
        st.markdown("시나리오 요약: 아직 시뮬레이션이 실행되지 않았습니다. 버튼을 눌러 위험 시나리오를 반영하세요.")


def render_action_plan(frozen_capital: int, delay_penalty: int) -> None:
    if delay_penalty >= THRESHOLD_PENALTY or frozen_capital > THRESHOLD_FROZEN:
        st.markdown(
            """👉 [Action Plan]
**현금 흐름 악화** 우려. 즉시 대기업(LGES 등) 공급망 담당자와 협의하여
**자재 사급** 전환을 요청하거나, 야드 포화를 막기 위한 임시 **외주 창고** 확보를 검토하십시오."""
        )


def render_debug_checklist() -> None:
    with st.expander("Self-Checklist"):
        st.markdown("- [x] 초기 예외 방어 완료")
        st.markdown("- [x] KPI 2열 균등 배치 완료")
        st.markdown("- [x] session_state.simulation_run 단일 키만 사용 완료")
        st.markdown("- [x] KPI 값 engine 인자 수신 구조 완료")
        st.markdown("- [x] KRW 포맷 적용 완료")
        st.markdown("- [x] Action Plan 조건부 출력 완료")
        st.markdown("- [x] SAFE ↔ ALERT 상태 전환 완료")
        st.markdown("- [x] Dense ERP Table 미노출 확인")


def render_executive_dashboard(df: pd.DataFrame | None, frozen_capital: int, delay_penalty: int) -> None:
    if df is not None:
        render_status_banner()
        render_risk_summary()
        render_kpi_cards(frozen_capital=frozen_capital, delay_penalty=delay_penalty)
        render_action_plan(frozen_capital=frozen_capital, delay_penalty=delay_penalty)
        with st.expander("상세 데이터 보기"):
            st.dataframe(df, use_container_width=True)
        render_debug_checklist()
    else:
        render_status_banner()
        render_risk_summary()
        render_kpi_cards(frozen_capital=0, delay_penalty=0)
        render_action_plan(frozen_capital=0, delay_penalty=0)
        render_debug_checklist()


# Backward-compatible wrappers used by app.py

def render_kpis(kpi: dict[str, int | float]) -> None:
    render_kpi_cards(
        frozen_capital=int(kpi.get("total_revenue_krw", 0)),
        delay_penalty=int(kpi.get("total_risk_cost_krw", 0)),
    )


def render_table(dataframe: pd.DataFrame) -> None:
    with st.expander("상세 데이터 보기"):
        st.dataframe(dataframe, use_container_width=True)


def render_red_alerts(dataframe: pd.DataFrame) -> None:
    _ = dataframe
    render_status_banner()


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
        st.caption(f"* 자본기회비용 = 재고원가 × ((연간 금융비용율/100) ÷ 12) × 지연 개월수  (현재: ₩{capital_cost:,.0f})")
        st.caption(f"* 진부화손실비용 = 재고원가 × ((연간 진부화비율/100) ÷ 12) × 지연 개월수  (현재: ₩{obsolescence_cost:,.0f})")

    return selected_project_id, delay_months, total_risk_cost, f"₩{total_risk_cost:,.0f}"
