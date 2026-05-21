import pandas as pd
import streamlit as st

PROJECT_SCHEMA = {
    "Project_ID": "string",
    "Client": "string",
    "Product_Name": "string",
    "Order_Value": "float",
    "Delivery_Date": "datetime",
}

BOM_SCHEMA = {
    "Item_Code": "string",
    "Item_Name": "string",
    "Associated_Project": "string",
    "Unit_Cost": "float",
    "Required_Qty": "float",
}


def _validate_required_columns(df: pd.DataFrame, schema: dict[str, str]) -> tuple[bool, list[str]]:
    missing = [column for column in schema if column not in df.columns]
    return len(missing) == 0, missing


def _validate_dtypes(df: pd.DataFrame, schema: dict[str, str]) -> tuple[bool, list[str]]:
    invalid_columns: list[str] = []

    for column, expected in schema.items():
        if expected == "string":
            if not pd.api.types.is_string_dtype(df[column]):
                invalid_columns.append(column)
        elif expected == "float":
            if not pd.api.types.is_float_dtype(df[column]) and not pd.api.types.is_integer_dtype(df[column]):
                invalid_columns.append(column)
        elif expected == "datetime":
            if not pd.api.types.is_datetime64_any_dtype(df[column]):
                invalid_columns.append(column)

    return len(invalid_columns) == 0, invalid_columns


def load_and_validate_excel(uploaded_file, schema: dict[str, str], file_label: str) -> pd.DataFrame | None:
    try:
        parse_dates = [column for column, dtype in schema.items() if dtype == "datetime"]
        df = pd.read_excel(uploaded_file, parse_dates=parse_dates)
    except Exception:
        st.error(f"{file_label} 파일을 읽는 중 오류가 발생했습니다. 파일 형식을 확인하세요.")
        return None

    valid_columns, missing_columns = _validate_required_columns(df, schema)
    if not valid_columns:
        st.error(
            f"정규 템플릿 컬럼이 누락되었습니다. {', '.join(missing_columns)}을 확인하세요."
        )
        return None

    valid_dtypes, invalid_columns = _validate_dtypes(df, schema)
    if not valid_dtypes:
        st.error(
            f"정규 템플릿 컬럼이 누락되었습니다. {', '.join(invalid_columns)}을 확인하세요."
        )
        return None

    return df


def main() -> None:
    st.set_page_config(page_title="EPIRS - 데이터 입력/검증", layout="wide")
    st.title("제조 재고 리스크 진단기 (EPIRS)")
    st.subheader("1단계: 마스터 엑셀 업로드 및 스키마 검증")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Project_Master 업로드")
        project_file = st.file_uploader(
            "Project_Master.xlsx 파일을 업로드하세요",
            type=["xlsx"],
            key="project_master_uploader",
        )

    with col2:
        st.markdown("### Inventory_BOM 업로드")
        bom_file = st.file_uploader(
            "Inventory_BOM.xlsx 파일을 업로드하세요",
            type=["xlsx"],
            key="inventory_bom_uploader",
        )

    if project_file is not None:
        project_df = load_and_validate_excel(project_file, PROJECT_SCHEMA, "Project_Master")
        if project_df is not None:
            st.success("Project_Master.xlsx 검증 완료")
            st.dataframe(project_df.head())
        else:
            st.stop()

    if bom_file is not None:
        bom_df = load_and_validate_excel(bom_file, BOM_SCHEMA, "Inventory_BOM")
        if bom_df is not None:
            st.success("Inventory_BOM.xlsx 검증 완료")
            st.dataframe(bom_df.head())
        else:
            st.stop()


if __name__ == "__main__":
    main()
