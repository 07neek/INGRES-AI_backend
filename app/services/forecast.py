from typing import List, Optional

from .water_data_service import get_local_history


class ForecastError(Exception):
    pass


def _linear_fit(xs: List[float], ys: List[float]):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def forecast_stage_of_extraction(state: str, district: Optional[str] = None, block: Optional[str] = None) -> dict:
    rows = get_local_history(state=state, district=district, block=block)
    if not rows:
        raise ForecastError(f"No historical data found for state='{state}' district='{district}' block='{block}'")

    # If multiple blocks matched (e.g. only state given), use the first block
    chosen_block = rows[0]["block"]
    block_rows = sorted([r for r in rows if r["block"] == chosen_block], key=lambda r: r["year"])

    years = [r["year"] for r in block_rows]
    values = [r["stage_of_extraction_percent"] for r in block_rows]

    slope, intercept = _linear_fit(years, values)
    next_year = max(years) + 1
    projected = round(slope * next_year + intercept, 1)

    if slope > 0.5:
        trend = "declining"  # extraction stage rising = groundwater situation worsening
    elif slope < -0.5:
        trend = "improving"
    else:
        trend = "stable"

    return {
        "state": block_rows[0]["state"],
        "district": block_rows[0]["district"],
        "block": chosen_block,
        "historical": [{"year": r["year"], "stage_of_extraction_percent": r["stage_of_extraction_percent"]} for r in block_rows],
        "projected_next_year": {"year": next_year, "stage_of_extraction_percent": max(0.0, projected)},
        "trend": trend,
        "method": "linear_trend_projection (illustrative — swap in LSTM/Prophet for production-grade forecasting)",
        "source": "local_reference_dataset",
    }
