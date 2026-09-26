from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Purpose(str, Enum):
    LEISURE = "Leisure"
    BUSINESS = "Business"
    ADVENTURE = "Adventure/Trekking"
    PILGRIMAGE = "Pilgrimage/Religious"
    MEDICAL = "Medical"
    EVENT = "Event"
    STUDY = "Study/Work relocation"


class TravelerInput(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120, description="Exact age in years")
    age_bracket: Optional[str] = Field(None, description="One of: infant, child, teen, adult, senior")


class TripInput(BaseModel):
    destination: str = Field(..., min_length=1, description="City or region name")
    purpose: Purpose
    start_date: str = Field(..., description="YYYY-MM-DD")
    trip_length: int = Field(..., ge=1, le=365, description="Trip length in days")
    travelers: list[TravelerInput] = Field(..., min_length=1)


class PackingCategory(BaseModel):
    name: str
    items: list[str]


class TravelerPackingList(BaseModel):
    traveler_index: int
    age_label: str
    weather_basis: str  # "forecast" | "climate_normal" | "unavailable"
    categories: list[PackingCategory]


class PackingResponse(BaseModel):
    trip_id: Optional[str] = None
    destination: str
    purpose: str
    weather_summary: Optional[str] = None
    packing_lists: list[TravelerPackingList]


class TripRecord(BaseModel):
    id: str
    destination: str
    purpose: str
    start_date: str
    trip_length: int
    travelers: list[TravelerInput]
    created_at: str
    packing_lists: Optional[list[TravelerPackingList]] = None
    weather_summary: Optional[str] = None