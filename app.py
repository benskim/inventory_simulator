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


def _build_template_bytes() -> bytes:
    project_template = pd.DataFrame(columns=PROJECT_SCHEMA.keys())
    bom_template = pd.DataFrame(columns=BOM_SCHEMA.keys())

    with pd.ExcelWriter("sample_template.xlsx", engine="openpyxl") as writer:
        project_template.to_excel(writer, sheet_name="Project_Master", index=False)
        bom_template.to_excel(writer, sheet_name="Inventory_BOM", index=False)

    with open("sample_template.xlsx", "rb") as template_file:
        return template_file.read()


def _validate_required_columns(df: pd.DataFrame, schema: dict[str, str]) -> tuple[list[str], list[str]]:
    missing = [column for column in schema if column not in df.columns]
    extra = [column for column in df.columns if column not in schema]
    return missing, extra


def _normalize_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def _normalize_and_validate(df: pd.DataFrame, schema: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    normalized = df.copy()
    errors: list[dict[str, object]] = []

    for column, expected in schema.items():
        if expected == "string":
            normalized[column] = normalized[column].astype("string").str.strip()
            missing_mask = normalized[column].isna() | (normalized[column] == "")
            for index in normalized[missing_mask].index:
                errors.append(
                    {"row": int(index) + 2, "column": column, "value": df.at[index, column], "reason": "empty string"}
                )
        elif expected == "float":
            converted = _normalize_numeric(normalized[column])
            invalid_mask = converted.isna()
            negative_mask = converted < 0
            normalized[column] = converted

            for index in normalized[invalid_mask].index:
                errors.append(
                    {"row": int(index) + 2, "column": column, "value": df.at[index, column], "reason": "invalid numeric"}
                )
            for index in normalized[negative_mask].index:
                errors.append(
                    {"row": int(index) + 2, "column": column, "value": df.at[index, column], "reason": "negative not allowed"}
                )
        elif expected == "datetime":
            converted = pd.to_datetime(normalized[column], errors="coerce")
            invalid_mask = converted.isna()
            normalized[column] = converted

            for index in normalized[invalid_mask].index:
                errors.append(
                    {"row": int(index) + 2, "column": column, "value": df.at[index, column], "reason": "invalid datetime"}
                )

    return normalized, pd.DataFrame(errors)


def load_and_validate_excel(uploaded_file, schema: dict[str, str], file_label: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception:
        st.error(f"{file_label} 파일을 읽는 중 오류가 발생했습니다. 파일 형식을 확인하세요.")
        return None, None

    missing_columns, extra_columns = _validate_required_columns(df, schema)
    if missing_columns:
        st.error(f"[{file_label}] 필수 컬럼 누락: {', '.join(missing_columns)}")
        return None, None

    if extra_columns:
        st.warning(f"[{file_label}] 템플릿 외 컬럼 감지: {', '.join(extra_columns)}")

    normalized_df, error_df = _normalize_and_validate(df[list(schema.keys())], schema)
    if not error_df.empty:
        st.error(f"[{file_label}] 데이터 타입/값 오류 {len(error_df)}건이 발견되었습니다.")
        st.dataframe(error_df, use_container_width=True)
        return None, error_df

    return normalized_df, None


def main() -> None:
    st.set_page_config(page_title="EPIRS - 데이터 입력/검증", layout="wide")
    st.title("제조 재고 리스크 진단기 (EPIRS)")
    st.subheader("1단계: 마스터 엑셀 업로드 및 스키마 검증")
    st.caption("핵심: 업로드 시 스키마/타입/키 검증을 수행하고 오류 row를 표시합니다.")

    st.download_button(
        "샘플 템플릿 다운로드 (.xlsx)",
        data=_build_template_bytes(),
        file_name="inventory_simulator_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

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
        project_df, _ = load_and_validate_excel(project_file, PROJECT_SCHEMA, "Project_Master")
        if project_df is not None:
            duplicate_project = project_df["Project_ID"].duplicated(keep=False)
            if duplicate_project.any():
                duplicate_rows = [index + 2 for index in project_df[duplicate_project].index]
                st.error(f"[Project_Master] Project_ID 중복 row: {duplicate_rows}")
                st.stop()
            st.success("Project_Master.xlsx 검증 완료")
            st.dataframe(project_df.head())
        else:
            st.stop()

    if bom_file is not None:
        bom_df, _ = load_and_validate_excel(bom_file, BOM_SCHEMA, "Inventory_BOM")
        if bom_df is not None:
            if project_file is not None and project_df is not None:
                missing_project_mask = ~bom_df["Associated_Project"].isin(project_df["Project_ID"])
                if missing_project_mask.any():
                    rows = [index + 2 for index in bom_df[missing_project_mask].index]
                    st.error(f"[Inventory_BOM] Associated_Project 미존재 row: {rows}")
                    st.dataframe(
                        bom_df.loc[missing_project_mask, ["Associated_Project"]].reset_index(names="row_number"),
                        use_container_width=True,
                    )
                    st.stop()
            st.success("Inventory_BOM.xlsx 검증 완료")
            st.dataframe(bom_df.head())
        else:
            st.stop()


if __name__ == "__main__":
    main()
