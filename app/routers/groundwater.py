"""
routers/groundwater.py
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .. import schemas
from ..services import water_data_service as wds
from ..services.forecast import ForecastError, forecast_stage_of_extraction

router = APIRouter(prefix="/api/v1/groundwater", tags=["groundwater"])


@router.get("/states")
def get_states():
    return {"states": wds.list_states()}


@router.get("/districts")
def get_districts(state: Optional[str] = Query(None)):
    return {"state": state, "districts": wds.list_districts(state=state)}


@router.get("/status/{state}", response_model=schemas.GroundwaterStatusResponse)
async def get_status(state: str, district: Optional[str] = Query(None), block: Optional[str] = Query(None)):
    records, source = await wds.get_groundwater_data(state=state, district=district, block=block, latest_only=True)
    if not records:
        raise HTTPException(status_code=404, detail=f"No groundwater data found for state='{state}'.")
    return schemas.GroundwaterStatusResponse(
        query={"state": state, "district": district, "block": block},
        records=wds.to_year_records(records),
        summary=wds.category_summary(records),
        source=source,
    )


@router.get("/categories")
def get_categories(state: Optional[str] = Query(None)):
    # Local dataset only, by design: a nationwide/state category legend is a
    # cheap summary and doesn't need a live API round-trip.
    summary = wds.local_status_summary(state=state)
    return {"state": state, "summary": summary, "source": "local_reference_dataset"}


@router.get("/forecast/{state}", response_model=schemas.ForecastResponse)
def get_forecast(state: str, district: Optional[str] = Query(None), block: Optional[str] = Query(None)):
    try:
        result = forecast_stage_of_extraction(state=state, district=district, block=block)
    except ForecastError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return schemas.ForecastResponse(
        state=result["state"],
        district=result["district"],
        block=result["block"],
        historical=[schemas.ForecastPoint(**point) for point in result["historical"]],
        projected_next_year=schemas.ForecastPoint(**result["projected_next_year"]),
        trend=result["trend"],
        method=result["method"],
        source=result["source"],
    )
