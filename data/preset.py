# ── 시나리오 1: Demand-Side (LGES 오하이오 지연) ──────────────────────
DEMO_DELAY_DAYS_S1 = 0

DEMO_PROJECT_S1 = {
    "Project_ID": "PRJ-2026-LGES-01",
    "Client": "LG에너지솔루션",
    "Product_Name": "B-LINK ESS 인클로저 외함 100세트",
    "Order_Value": 700_000_000,
    "Delivery_Date": "2026-07-31",
}
DEMO_BOM_S1 = {
    "Item_Code": "COMP-ACB-4000A",
    "Item_Name": "LS일렉트릭 기중차단기 4000A",
    "Associated_Project": "PRJ-2026-LGES-01",
    "Unit_Cost": 3_500_000,
    "Required_Qty": 100,
}

# ── 시나리오 2: Supply-Side (전장부품 쇼티지) ─────────────────────────
DEMO_DELAY_DAYS_S2 = 21

DEMO_PROJECT_S2 = {
    "Project_ID": "PRJ-2026-SKTM-02",
    "Client": "SK텔레시스",
    "Product_Name": "배터리 랙 어셈블리 50세트",
    "Order_Value": 700_000_000,
    "Delivery_Date": "2026-08-15",
}
DEMO_BOM_S2 = {
    "Item_Code": "COMP-BMS-500V",
    "Item_Name": "BMS 제어보드 500V급",
    "Associated_Project": "PRJ-2026-SKTM-02",
    "Unit_Cost": 2_000_000,
    "Required_Qty": 0,
}
