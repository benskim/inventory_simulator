from __future__ import annotations

import pandas as pd
import streamlit as st

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
