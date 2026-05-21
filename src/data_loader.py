from __future__ import annotations

import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = {
    "project_name": "object",
    "monthly_revenue_krw": "int64",
    "expected_delay_days": "int64",
    "penalty_per_day_krw": "int64",
}

PROJECT_MASTER_SCHEMA: dict[str, str] = {
    "Project_ID": "str",
    "Client": "str",
    "Product_Name": "str",
    "Order_Value": "int",
    "Delivery_Date": "datetime",
}

INVENTORY_BOM_SCHEMA: dict[str, str] = {
    "Item_Code": "str",
    "Item_Name": "str",
    "Associated_Project": "str",
    "Unit_Cost": "int",
    "Required_Qty": "int",
}


def load_excel(uploaded_file) -> pd.DataFrame:
    """Load excel file into DataFrame."""
    return pd.read_excel(uploaded_file, engine="openpyxl")


def load_demo_data() -> pd.DataFrame:
    """Return deterministic preset data for demo."""
    return pd.DataFrame(
        {
            "project_name": ["Alpha", "Beta", "Gamma", "Delta"],
            "monthly_revenue_krw": [240000000, 180000000, 210000000, 150000000],
            "expected_delay_days": [3, 12, 7, 15],
            "penalty_per_day_krw": [2500000, 1800000, 2200000, 1200000],
        }
    )


def validate_columns(dataframe: pd.DataFrame) -> tuple[bool, list[str]]:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    return len(missing_columns) == 0, missing_columns


def sanitize_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Keep required columns and coerce numeric values deterministically."""
    sanitized = dataframe[list(REQUIRED_COLUMNS.keys())].copy()
    numeric_columns = [
        "monthly_revenue_krw",
        "expected_delay_days",
        "penalty_per_day_krw",
    ]
    sanitized[numeric_columns] = (
        sanitized[numeric_columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype("int64")
    )
    sanitized["project_name"] = sanitized["project_name"].fillna("UNKNOWN").astype(str)
    return sanitized


def _parse_numeric_column(dataframe: pd.DataFrame, column: str, label: str) -> None:
    cleaned = dataframe[column].astype("string").str.replace(",", "", regex=False).str.strip()
    parsed = pd.to_numeric(cleaned, errors="coerce")

    if parsed.isna().any():
        st.error(f"{label}의 {column} 컬럼에 숫자로 변환할 수 없는 값 또는 NaN이 있습니다.")
        st.stop()

    if (parsed < 0).any():
        st.error(f"{label}의 {column} 컬럼은 음수를 허용하지 않습니다.")
        st.stop()

    dataframe[column] = parsed.astype("int64")


def _validate_required_columns(dataframe: pd.DataFrame, required_columns: dict[str, str]) -> None:
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        st.error(
            "정규 템플릿 컬럼이 누락되었습니다. "
            f"[{', '.join(missing_columns)}]을 확인하세요."
        )
        st.stop()


def _validate_project_master(dataframe: pd.DataFrame) -> pd.DataFrame:
    validated = dataframe[list(PROJECT_MASTER_SCHEMA.keys())].copy()

    for column in ("Project_ID", "Client", "Product_Name"):
        validated[column] = validated[column].astype("string")

    _parse_numeric_column(validated, "Order_Value", "Project_Master")

    delivery_date = pd.to_datetime(validated["Delivery_Date"], errors="coerce")
    if delivery_date.isna().any():
        st.error("Project_Master의 Delivery_Date 컬럼에서 datetime 변환에 실패했습니다.")
        st.stop()
    validated["Delivery_Date"] = delivery_date

    return validated


def _validate_inventory_bom(dataframe: pd.DataFrame) -> pd.DataFrame:
    validated = dataframe[list(INVENTORY_BOM_SCHEMA.keys())].copy()

    for column in ("Item_Code", "Item_Name", "Associated_Project"):
        validated[column] = validated[column].astype("string")

    _parse_numeric_column(validated, "Unit_Cost", "Inventory_BOM")
    _parse_numeric_column(validated, "Required_Qty", "Inventory_BOM")
    return validated


def _read_excel_safely(uploaded_file, label: str) -> pd.DataFrame:
    try:
        return pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        st.error(f"{label} 파일 파싱 중 오류가 발생했습니다: {exc}")
        st.stop()


def render_upload_and_validation_interface() -> tuple[pd.DataFrame, pd.DataFrame] | tuple[None, None]:
    """Render two uploaders and return validated DataFrames when both files are uploaded."""
    project_column, bom_column = st.columns(2)

    with project_column:
        project_file = st.file_uploader("Project_Master.xlsx 업로드", type=["xlsx"], key="project_master")

    with bom_column:
        bom_file = st.file_uploader("Inventory_BOM.xlsx 업로드", type=["xlsx"], key="inventory_bom")

    if project_file is None or bom_file is None:
        st.info("Project_Master.xlsx와 Inventory_BOM.xlsx를 모두 업로드하세요.")
        return None, None

    project_raw = _read_excel_safely(project_file, "Project_Master")
    bom_raw = _read_excel_safely(bom_file, "Inventory_BOM")

    _validate_required_columns(project_raw, PROJECT_MASTER_SCHEMA)
    _validate_required_columns(bom_raw, INVENTORY_BOM_SCHEMA)

    project_validated = _validate_project_master(project_raw)
    bom_validated = _validate_inventory_bom(bom_raw)

    st.success("두 파일의 스키마 검증이 완료되었습니다.")
    st.markdown("#### Project_Master 미리보기")
    st.dataframe(project_validated.head(3))
    st.markdown("#### Inventory_BOM 미리보기")
    st.dataframe(bom_validated.head(3))

    return project_validated, bom_validated
