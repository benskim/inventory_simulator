from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {
    "project_name": "object",
    "monthly_revenue_krw": "int64",
    "expected_delay_days": "int64",
    "penalty_per_day_krw": "int64",
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
