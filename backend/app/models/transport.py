from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TransportMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"


class BudgetStatus(str, Enum):
    WITHIN = "within"
    OVER = "over"


class WeatherRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataSource(str, Enum):
    API = "api"
    WEB = "web"
    ESTIMATE = "estimate"


class RankingPreference(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    FEWEST_TRANSFERS = "fewest_transfers"
    DEPARTURE_TIME = "departure_time"
    ARRIVAL_TIME = "arrival_time"
    COMFORT = "comfort"
    CUSTOM = "custom"


class Leg(BaseModel):
    from_place: str = Field(..., alias="from")
    to_place: str = Field(..., alias="to")
    departure: str = Field(..., description="ISO datetime")
    arrival: str = Field(..., description="ISO datetime")
    vehicle_number: Optional[str] = None
    carrier: Optional[str] = None

    model_config = {"populate_by_name": True}


class BaggageAllowance(BaseModel):
    included_bags: int = 0
    included_weight_kg: Optional[float] = None
    extra_bag_fee_est: float = 0.0


class WeatherRisk(BaseModel):
    level: WeatherRiskLevel = WeatherRiskLevel.NONE
    reason: Optional[str] = None


class TransportOption(BaseModel):
    id: str
    mode: TransportMode
    provider: str
    legs: list[Leg]
    duration_total_minutes: int
    transfers: int = 0
    price_base: float
    currency: str = "INR"
    baggage_allowance: Optional[BaggageAllowance] = None
    baggage_fee_est: float = 0.0
    price_total: float
    budget_status: BudgetStatus = BudgetStatus.WITHIN
    budget_over_by: float = 0.0
    weather_risk: WeatherRisk = WeatherRisk()
    source: DataSource = DataSource.ESTIMATE
    fetched_at: str = ""
    deep_link: Optional[str] = None
    labels: list[str] = Field(default_factory=list, description="e.g. ['cheapest', 'fastest']")


class TransportSearchRequest(BaseModel):
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    date: str = Field(..., description="YYYY-MM-DD")
    date_window_n: int = Field(0, ge=0, le=3, description="±N days flexibility")
    travelers_adults: int = Field(1, ge=1)
    travelers_children: int = Field(0, ge=0)
    budget_share: float = Field(..., gt=0, description="Transport budget in INR")
    ranking_preference: RankingPreference = RankingPreference.CHEAPEST
    custom_preference: Optional[str] = Field(None, description="Free-text preference")
    return_date: Optional[str] = Field(None, description="YYYY-MM-DD for return trip")
    packing_bag_count: Optional[int] = None
    packing_weight_kg: Optional[float] = None


class TransportSearchResponse(BaseModel):
    trip_id: Optional[str] = None
    origin: str
    destination: str
    date: str
    options: list[TransportOption]
    total_found: int
    ranking_preference: str
    interpreted_preferences: Optional[str] = None
    budget_share: float
    warnings: list[str] = Field(default_factory=list)


class SelectedOptionRequest(BaseModel):
    option_id: str
    trip_id: str


class DateShiftProposal(BaseModel):
    trip_id: str
    original_date: str
    proposed_date: str
    reason: str
    affected_option_id: str


class DateShiftConfirm(BaseModel):
    trip_id: str
    proposed_date: str
    accept: bool