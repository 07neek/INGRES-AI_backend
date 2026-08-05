

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's message / question")
    session_id: Optional[str] = Field(
        None, description="Pass back the session_id you received earlier to keep conversation context; omit on first call"
    )
    language: Optional[str] = Field(
        "en", description="BCP-47-ish language hint (e.g. 'en', 'hi', 'mr'). Reserved for vernacular routing (Bhashini pillar)."
    )


class GroundwaterYearRecord(BaseModel):
    state: str
    district: str
    block: str
    latitude: float
    longitude: float
    year: int
    annual_extractable_resource_ham: float
    annual_ground_water_extraction_ham: float
    stage_of_extraction_percent: float
    category: str
    rainfall_mm: float
    pre_monsoon_level_mbgl: float
    post_monsoon_level_mbgl: float


class ChartData(BaseModel):
    type: str  # "bar"
    title: str
    labels: List[str]
    values: List[float]


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    entities: Dict[str, Optional[str]]
    records: List[GroundwaterYearRecord] = []
    chart: Optional[ChartData] = None
    crop_advisory: Optional[List[str]] = None
    data_source: str
    llm_status: str
    generated_at: str

# Groundwater data endpoints

class CategorySummary(BaseModel):
    Safe: int = 0
    Semi_Critical: int = Field(0, alias="Semi-Critical")
    Critical: int = 0
    Over_Exploited: int = Field(0, alias="Over-Exploited")
    Saline: int = 0

    model_config = {"populate_by_name": True}


class GroundwaterStatusResponse(BaseModel):
    query: Dict[str, Optional[str]]
    records: List[GroundwaterYearRecord]
    summary: Dict[str, int]
    source: str


class ForecastPoint(BaseModel):
    year: int
    stage_of_extraction_percent: float


class ForecastResponse(BaseModel):
    state: str
    district: Optional[str] = None
    block: Optional[str] = None
    historical: List[ForecastPoint]
    projected_next_year: ForecastPoint
    trend: str
    method: str
    source: str


class ErrorResponse(BaseModel):
    detail: str
