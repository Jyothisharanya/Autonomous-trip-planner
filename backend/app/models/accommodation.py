from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class StayType(str, Enum):
    HOTEL = "hotel"
    HOSTEL = "hostel"
    HOMESTAY = "homestay"
    RESORT = "resort"
    GUESTHOUSE = "guesthouse"
    APARTMENT = "apartment"


class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TWIN = "twin"
    TRIPLE = "triple"
    QUAD = "quad"
    DORM = "dorm"
    SUITE = "suite"
    FAMILY = "family"


class Amenity(str, Enum):
    WIFI = "wifi"
    AC = "ac"
    BREAKFAST = "breakfast"
    PARKING = "parking"
    POOL = "pool"
    GYM = "gym"
    RESTAURANT = "restaurant"
    ROOM_SERVICE = "room_service"
    LAUNDRY = "laundry"
    POWER_BACKUP = "power_backup"
    HOT_WATER = "hot_water"
    TV = "tv"
    MINIBAR = "minibar"
    KITCHEN = "kitchen"
    PET_FRIENDLY = "pet_friendly"


class ArrivalMismatch(BaseModel):
    has_mismatch: bool = False
    early_arrival: bool = False
    late_departure: bool = False
    note: Optional[str] = None


class RoomOption(BaseModel):
    id: str
    room_type: RoomType
    max_occupancy: int = 2
    price_per_night: float
    currency: str = "INR"
    amenities: list[Amenity] = Field(default_factory=list)
    available: bool = True
    cancellation_policy: Optional[str] = None


class Stay(BaseModel):
    id: str
    name: str
    stay_type: StayType
    city: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: int = 0
    price_per_night_min: float
    price_per_night_max: float
    currency: str = "INR"
    room_options: list[RoomOption] = Field(default_factory=list)
    amenities: list[Amenity] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    check_in_time: str = "14:00"
    check_out_time: str = "11:00"
    contact_phone: Optional[str] = None
    booking_link: Optional[str] = None
    source: str = "curated"
    distance_from_anchor_km: Optional[float] = None
    labels: list[str] = Field(default_factory=list, description="e.g. ['best overall', 'cheapest good', 'closest']")


class AccommodationSearchRequest(BaseModel):
    city: str = Field(..., min_length=1)
    check_in: str = Field(..., description="YYYY-MM-DD")
    check_out: str = Field(..., description="YYYY-MM-DD")
    num_rooms: int = Field(1, ge=1, le=10)
    adults: int = Field(2, ge=1, le=20)
    children: int = Field(0, ge=0, le=10)
    budget_per_night: float = Field(..., gt=0, description="Max per night in INR")
    soft_margin_pct: float = Field(10.0, ge=0, le=50, description="Soft margin % above budget")
    stay_type: Optional[StayType] = None
    required_amenities: list[Amenity] = Field(default_factory=list)
    anchor_lat: Optional[float] = Field(None, description="Anchor latitude (from itinerary)")
    anchor_lon: Optional[float] = Field(None, description="Anchor longitude (from itinerary)")
    arrival_time: Optional[str] = Field(None, description="Expected arrival time HH:MM")
    departure_time: Optional[str] = Field(None, description="Expected departure time HH:MM")
    ranking_preference: str = Field("best_overall", description="best_overall, cheapest, closest, highest_rated")


class Cluster(BaseModel):
    id: str
    name: str
    centroid_lat: float
    centroid_lon: float
    stop_names: list[str] = Field(default_factory=list)


class ShortlistItem(BaseModel):
    stay: Stay
    rank: int
    label: str = Field(..., description="e.g. 'best overall', 'cheapest good option', 'closest'")
    total_stay_cost: float
    nights: int
    arrival_mismatch: ArrivalMismatch = ArrivalMismatch()
    score: float = Field(0.0, description="Composite score 0-100")


class AccommodationSearchResponse(BaseModel):
    city: str
    check_in: str
    check_out: str
    nights: int
    budget_per_night: float
    soft_margin: float
    total_found: int
    shortlist: list[ShortlistItem]
    warnings: list[str] = Field(default_factory=list)
    clusters: list[Cluster] = Field(default_factory=list)