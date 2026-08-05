"""
water_data_service.py
======================
Everything to do with getting groundwater data into the app — this is the
"National Water Data Portal" integration layer.

Two data sources, one interface:

"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from ..config import settings
from ..schemas import ChartData, GroundwaterYearRecord

logger = logging.getLogger("ingres_ai.water_data")

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_groundwater.json"

_CATEGORY_ORDER = ["Safe", "Semi-Critical", "Critical", "Over-Exploited", "Saline"]


class WaterDataError(Exception):
    """Raised for unrecoverable data-layer errors (bad local dataset, etc.)."""


# Local reference dataset

def _load_local_dataset() -> dict:
    if not _DATA_PATH.exists():
        raise WaterDataError(
            f"Reference dataset not found at {_DATA_PATH}. "
            f"Run `python scripts/generate_mock_data.py` once to create it."
        )
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_dataset_cache: Optional[dict] = None


def _dataset() -> dict:
    global _dataset_cache
    if _dataset_cache is None:
        _dataset_cache = _load_local_dataset()
    return _dataset_cache


def _flatten_local(state: Optional[str] = None, district: Optional[str] = None,
                    block: Optional[str] = None, latest_only: bool = False) -> List[dict]:
    """Flattens the nested {block -> yearly[]} structure into flat year-rows,
    optionally filtered by state/district/block (case-insensitive substring
    match, so "punjab" matches "Punjab")."""
    rows: List[dict] = []
    for rec in _dataset()["records"]:
        if state and state.lower() not in rec["state"].lower():
            continue
        if district and district.lower() not in rec["district"].lower():
            continue
        if block and block.lower() not in rec["block"].lower():
            continue

        yearly = rec["yearly"]
        if latest_only:
            yearly = [max(yearly, key=lambda y: y["year"])]

        for y in yearly:
            rows.append({
                "state": rec["state"],
                "district": rec["district"],
                "block": rec["block"],
                "latitude": rec["latitude"],
                "longitude": rec["longitude"],
                **y,
            })
    return rows


def get_local_history(state: Optional[str] = None, district: Optional[str] = None,
                       block: Optional[str] = None) -> List[dict]:
    """Public accessor for the full multi-year local history, filtered by
    location. Used by the forecast service, which needs every year (not just
    the latest) to fit a trend line."""
    return _flatten_local(state=state, district=district, block=block, latest_only=False)


def list_states() -> List[str]:
    return sorted({rec["state"] for rec in _dataset()["records"]})


def list_districts(state: Optional[str] = None) -> List[str]:
    return sorted({
        rec["district"] for rec in _dataset()["records"]
        if not state or state.lower() in rec["state"].lower()
    })

# Live National Water Data Portal API (data.gov.in-style)

async def _fetch_live(state: Optional[str], district: Optional[str]) -> Optional[List[dict]]:
    """Attempts the live API call. Returns None (never raises) on any failure
    so the caller can transparently fall back to the local dataset — a live
    integration should never take the whole assistant down."""
    if not settings.WATER_DATA_RESOURCE_ID or settings.WATER_DATA_RESOURCE_ID.startswith("REPLACE_WITH"):
        logger.info("Live water API skipped: WATER_DATA_RESOURCE_ID not configured.")
        return None

    params = {
        "api-key": settings.WATER_DATA_API_KEY,
        "format": "json",
        "limit": 50,
    }
    if state:
        params["filters[state]"] = state
    if district:
        params["filters[district]"] = district

    url = f"{settings.WATER_DATA_BASE_URL.rstrip('/')}/{settings.WATER_DATA_RESOURCE_ID}"

    try:
        async with httpx.AsyncClient(timeout=settings.WATER_DATA_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            records = payload.get("records")
            if not records:
                logger.warning("Live water API returned no records for state=%s district=%s", state, district)
                return None
            return records
    except Exception as exc: 
        logger.warning("Live water API call failed (%s) — falling back to local dataset.", exc)
        return None


# Public orchestrator

async def get_groundwater_data(
    state: Optional[str] = None,
    district: Optional[str] = None,
    block: Optional[str] = None,
    latest_only: bool = False,
) -> Tuple[List[dict], str]:
    """Returns (records, source_label). Tries the live portal first (if
    enabled), otherwise — or on any failure — uses the bundled reference
    dataset so the endpoint always has data to return."""
    if settings.USE_LIVE_WATER_API:
        live_records = await _fetch_live(state, district)
        if live_records:
            return live_records, "national_water_data_portal_live"

    rows = _flatten_local(state=state, district=district, block=block, latest_only=latest_only)
    return rows, "local_reference_dataset"


def local_status_summary(state: Optional[str] = None) -> Dict[str, int]:
    """Category counts (latest year per block) straight from the local
    reference dataset — used for a quick nationwide/state legend without
    needing a live API round-trip."""
    rows = _flatten_local(state=state, latest_only=True)
    return category_summary(rows)


def category_summary(records: List[dict]) -> Dict[str, int]:
    summary = {c: 0 for c in _CATEGORY_ORDER}
    for r in records:
        cat = r.get("category", "Unknown")
        summary[cat] = summary.get(cat, 0) + 1
    return summary


def build_chart(records: List[dict], intent: str) -> Optional[dict]:
    """Builds a ready-to-render chart payload for the frontend. Returns None
    when a chart wouldn't add value (e.g. no matching records)."""
    if not records:
        return None

    if intent == "forecast":
        # line chart of stage_of_extraction_percent over years for the first
        block_name = records[0]["block"]
        block_rows = sorted(
            [r for r in records if r["block"] == block_name],
            key=lambda r: r["year"],
        )
        return {
            "type": "line",
            "title": f"Stage of Ground Water Extraction (%) — {block_name}",
            "labels": [str(r["year"]) for r in block_rows],
            "values": [r["stage_of_extraction_percent"] for r in block_rows],
        }

    latest_by_block: Dict[str, dict] = {}
    for r in records:
        key = r["block"]
        if key not in latest_by_block or r["year"] > latest_by_block[key]["year"]:
            latest_by_block[key] = r

    summary = category_summary(list(latest_by_block.values()))
    non_zero = {k: v for k, v in summary.items() if v > 0}
    if not non_zero:
        return None

    return {
        "type": "pie",
        "title": "Groundwater Assessment Category Distribution",
        "labels": list(non_zero.keys()),
        "values": list(non_zero.values()),
    }


# Response-boundary conversion (raw dict validated Pydantic model)

def to_year_records(rows: List[dict]) -> List[GroundwaterYearRecord]:
    """Converts raw record dicts into validated GroundwaterYearRecord models.
    Local reference-dataset rows match the model's fields exactly. If you
    wire in a live dataset whose column names differ (data.gov.in/India-WRIS
    datasets vary), map its columns to GroundwaterYearRecord's field names
    inside `_fetch_live()` above — this function assumes that normalization
    already happened and just validates + skips (with a log) anything that
    still doesn't match, rather than failing the whole request."""
    validated: List[GroundwaterYearRecord] = []
    for row in rows:
        try:
            validated.append(GroundwaterYearRecord(**row))
        except Exception as exc:
            logger.warning("Skipping a record that doesn't match GroundwaterYearRecord: %s", exc)
    return validated


def to_chart_model(chart: Optional[dict]) -> Optional[ChartData]:
    """Same idea as to_year_records, for the single chart dict build_chart()
    returns."""
    if chart is None:
        return None
    return ChartData(**chart)
