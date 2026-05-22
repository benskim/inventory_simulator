import math

DAILY_PENALTY_RATE: float = 0.001  # 일일 지체상금 요율 0.1%


def calculate_delay_penalty(order_value: int, delay_days: int) -> dict:
    def _sanitize_to_non_negative_int(value: object) -> int:
        if value is None:
            value = 0
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                value = 0
            else:
                try:
                    numeric = float(stripped.replace(",", ""))
                    if math.isnan(numeric):
                        value = 0
                    else:
                        value = numeric
                except (TypeError, ValueError):
                    value = 0
        else:
            try:
                if math.isnan(value):
                    value = 0
            except (TypeError, ValueError):
                pass

        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0

        return max(0, value)

    safe_order_value = _sanitize_to_non_negative_int(order_value)
    safe_delay_days = _sanitize_to_non_negative_int(delay_days)

    penalty_amount = int(safe_order_value * safe_delay_days * DAILY_PENALTY_RATE)
    rate_percent_text = f"{DAILY_PENALTY_RATE * 100:.1f}%"
    formula_text = (
        f"₩{safe_order_value:,.0f} × {safe_delay_days}일 × {rate_percent_text} = "
        f"₩{penalty_amount:,.0f}"
    )

    return {
        "penalty_amount": penalty_amount,
        "formula_breakdown": {
            "order_value": safe_order_value,
            "delay_days": safe_delay_days,
            "daily_rate": DAILY_PENALTY_RATE,
        },
        "formula_text": formula_text,
    }
