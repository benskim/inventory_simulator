"""
초경량 결정론적 리스크 시뮬레이터

제품 목표:
- CEO 대상 기술영업 데모를 위한 단일 실행형 앱
- streamlit run app.py 한 줄로 즉시 구동

Scope 경계:
✅ IN-SCOPE
- Excel 업로드
- Pandas 파싱
- 리스크 사칙연산
- KPI 대시보드
- Red Alert UI
- 프리셋 데모 데이터

❌ OUT-OF-SCOPE
- ERP/MES 연동
- 로그인/인증
- OCR
- ML 학습
- RDB
- 멀티유저 동기화
"""

from __future__ import annotations

import streamlit as st

from src.data_loader import load_demo_data, load_excel, sanitize_dataframe, validate_columns
from src.engine import calculate_risk_metrics, summarize_kpi
from src.ui import render_kpis, render_red_alerts, render_table


def main() -> None:
    st.set_page_config(page_title="Inventory Risk Simulator", layout="wide")
    st.title("초경량 결정론적 재고 리스크 시뮬레이터")

    use_demo_data = st.toggle("프리셋 데모 데이터 사용", value=True)
    uploaded_file = st.file_uploader("Excel 파일 업로드 (.xlsx)", type=["xlsx"])

    if use_demo_data:
        source_df = load_demo_data()
    elif uploaded_file is not None:
        source_df = load_excel(uploaded_file)
    else:
        st.info("데모 데이터를 사용하거나 Excel 파일을 업로드하세요.")
        st.stop()

    is_valid, missing_columns = validate_columns(source_df)
    if not is_valid:
        st.error(f"필수 컬럼 누락: {', '.join(missing_columns)}")
        st.stop()

    sanitized_df = sanitize_dataframe(source_df)
    result_df = calculate_risk_metrics(sanitized_df)
    kpi = summarize_kpi(result_df)

    render_kpis(kpi)
    render_red_alerts(result_df)
    st.markdown("### 프로젝트 리스크 상세")
    render_table(result_df)


if __name__ == "__main__":
    main()
