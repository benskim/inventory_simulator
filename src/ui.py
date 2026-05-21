from __future__ import annotations

import pandas as pd
import streamlit as st


def format_krw(value: int) -> str:
    return f"₩{value:,}"


def render_kpis(kpi: dict[str, int | float]) -> None:
    column1, column2, column3, column4 = st.columns(4)
    column1.metric("총 매출", format_krw(int(kpi["total_revenue_krw"])))
    column2.metric("총 리스크 비용", format_krw(int(kpi["total_risk_cost_krw"])))
    column3.metric("Red Alert 건수", int(kpi["red_alert_count"]))
    column4.metric("평균 리스크 비율", f"{kpi['average_risk_ratio_pct']:.2f}%")


def render_table(dataframe: pd.DataFrame) -> None:
    display_df = dataframe.copy()
    display_df["monthly_revenue_krw"] = display_df["monthly_revenue_krw"].map(format_krw)
    display_df["risk_cost_krw"] = display_df["risk_cost_krw"].map(format_krw)
    display_df["penalty_per_day_krw"] = display_df["penalty_per_day_krw"].map(format_krw)
    display_df["red_alert"] = display_df["red_alert"].map(lambda is_alert: "🔴 RED" if is_alert else "🟢 NORMAL")
    st.dataframe(display_df, use_container_width=True)


def render_red_alerts(dataframe: pd.DataFrame) -> None:
    red_alerts = dataframe[dataframe["red_alert"]]
    st.markdown("### Red Alert")
    if red_alerts.empty:
        st.success("현재 Red Alert 프로젝트가 없습니다.")
        return
    for project_name in red_alerts["project_name"]:
        st.error(f"{project_name}: 리스크 비율 임계치(8%) 초과")
