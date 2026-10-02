import httpx
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from app.models.transport import (
    TransportOption, TransportMode, Leg, BaggageAllowance,
    WeatherRisk, WeatherRiskLevel, DataSource, BudgetStatus,
)

SKYSCANNER_BASE = "https://partners.api.skyscanner.net/apiservices/v3"
AMADEUS_BASE = "https://api.amadeus.com/v2"
TRAINLINE_BASE = "https://www.trainline.eu/api/v5"
FlixBus_API = "https://api.flixbus.com/search/v1"

RISKY_WEATHER_CODES = {95, 96, 99, 71, 73, 75, 77, 85, 86}


def _make_id(origin: str, dest: str, date: str, mode: str, provider: str) -> str:
    raw = f"{origin}:{dest}:{date}:{mode}:{provider}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _weather_risk_for_departure(weather: Optional[dict], departure_dt: datetime) -> WeatherRisk:
    if not weather:
        return WeatherRisk(level=WeatherRiskLevel.NONE)

    code = weather.get("weather_code", 0)
    wind = weather.get("wind_max_kmh", 0)
    precip = weather.get("precipitation_mm", 0)

    if code in RISKY_WEATHER_CODES:
        return WeatherRisk(level=WeatherRiskLevel.HIGH, reason=f"Severe weather forecast (code {code})")
    if wind > 60:
        return WeatherRisk(level=WeatherRiskLevel.MEDIUM, reason=f"Strong winds ({wind} km/h)")
    if precip > 20:
        return WeatherRisk(level=WeatherRiskLevel.MEDIUM, reason=f"Heavy rain ({precip}mm)")
    if precip > 5:
        return WeatherRisk(level=WeatherRiskLevel.LOW, reason=f"Light rain ({precip}mm)")
    return WeatherRisk(level=WeatherRiskLevel.NONE)


def _estimate_duration(mode: TransportMode, distance_km: float) -> int:
    speeds = {
        TransportMode.FLIGHT: 800,
        TransportMode.TRAIN: 160,
        TransportMode.BUS: 80,
        TransportMode.CAR: 100,
    }
    speed = speeds.get(mode, 100)
    return max(60, int((distance_km / speed) * 60) + 90)


def _estimate_price(mode: TransportMode, distance_km: float, pax: int) -> float:
    base_rates = {
        TransportMode.FLIGHT: 0.12,
        TransportMode.TRAIN: 0.05,
        TransportMode.BUS: 0.025,
        TransportMode.CAR: 0.03,
    }
    rate = base_rates.get(mode, 0.05)
    base = distance_km * rate
    if mode == TransportMode.FLIGHT:
        base = max(80, base)
    elif mode == TransportMode.TRAIN:
        base = max(20, base)
    elif mode == TransportMode.BUS:
        base = max(10, base)
    return round(base * pax, 2)


async def search_flights(origin: str, destination: str, date: str, adults: int = 1,
                          children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    api_key = None  # Would come from env
    options = []

    if api_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{AMADEUS_BASE}/shopping/flight-offers", params={
                    "originLocationCode": origin[:3].upper(),
                    "destinationLocationCode": destination[:3].upper(),
                    "departureDate": date,
                    "adults": adults,
                    "children": children,
                    "max": 5,
                }, headers={"Authorization": f"Bearer {api_key}"})
                resp.raise_for_status()
                data = resp.json()
                for offer in data.get("data", []):
                    # Parse Amadeus response into TransportOption
                    pass
        except Exception:
            pass

    # Generate realistic estimated options
    import random
    carriers = ["SkyWings Airlines", "GlobalAir", "BudgetJet", "National Express Air", "Horizon Airlines"]
    departure_hours = [6, 8, 10, 13, 15, 18, 21]

    for i in range(min(5, len(carriers))):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:00", "%Y-%m-%d %H:%M")
        duration = random.randint(90, 300)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        price = _estimate_price(TransportMode.FLIGHT, 800, pax) * random.uniform(0.8, 1.5)

        wr = _weather_risk_for_departure(weather, dep)

        options.append(TransportOption(
            id=_make_id(origin, destination, date, "flight", carriers[i]),
            mode=TransportMode.FLIGHT,
            provider=carriers[i],
            legs=[Leg(
                **{"from": origin, "to": destination},
                departure=dep.isoformat(),
                arrival=arr.isoformat(),
                vehicle_number=f"{carriers[i][:2].upper()}{random.randint(100,999)}",
                carrier=carriers[i],
            )],
            duration_total_minutes=duration,
            transfers=0,
            price_base=round(price, 2),
            currency="USD",
            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=23, extra_bag_fee_est=50),
            baggage_fee_est=0,
            price_total=round(price, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.google.com/flights?q=flights+from+{origin}+to+{destination}+on+{date}",
            labels=[],
        ))

    return options


async def search_trains(origin: str, destination: str, date: str, adults: int = 1,
                         children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    import random
    options = []
    operators = ["National Rail", "Express Rail", "Regional Connect", "Intercity", "HighSpeed Rail"]
    departure_hours = [5, 7, 9, 12, 14, 17, 20]

    for i in range(min(4, len(operators))):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:30", "%Y-%m-%d %H:%M")
        duration = random.randint(120, 480)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        price = _estimate_price(TransportMode.TRAIN, 500, pax) * random.uniform(0.7, 1.3)

        wr = _weather_risk_for_departure(weather, dep)

        options.append(TransportOption(
            id=_make_id(origin, destination, date, "train", operators[i]),
            mode=TransportMode.TRAIN,
            provider=operators[i],
            legs=[Leg(
                **{"from": origin, "to": destination},
                departure=dep.isoformat(),
                arrival=arr.isoformat(),
                vehicle_number=f"TR{random.randint(1000,9999)}",
                carrier=operators[i],
            )],
            duration_total_minutes=duration,
            transfers=0,
            price_base=round(price, 2),
            currency="USD",
            baggage_allowance=None,
            baggage_fee_est=0,
            price_total=round(price, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.google.com/travel/trains?q={origin}+to+{destination}",
            labels=[],
        ))

    return options


async def search_buses(origin: str, destination: str, date: str, adults: int = 1,
                        children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    import random
    options = []
    operators = ["FlixBus", "Greyhound", "Megabus", "National Express", "RedBus"]
    departure_hours = [5, 8, 11, 14, 18, 22]

    for i in range(min(4, len(operators))):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:00", "%Y-%m-%d %H:%M")
        duration = random.randint(180, 720)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        price = _estimate_price(TransportMode.BUS, 400, pax) * random.uniform(0.6, 1.2)

        wr = _weather_risk_for_departure(weather, dep)

        options.append(TransportOption(
            id=_make_id(origin, destination, date, "bus", operators[i]),
            mode=TransportMode.BUS,
            provider=operators[i],
            legs=[Leg(
                **{"from": origin, "to": destination},
                departure=dep.isoformat(),
                arrival=arr.isoformat(),
                vehicle_number=f"B{random.randint(100,999)}",
                carrier=operators[i],
            )],
            duration_total_minutes=duration,
            transfers=0,
            price_base=round(price, 2),
            currency="USD",
            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=15),
            baggage_fee_est=0,
            price_total=round(price, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.google.com/travel/buses?q={origin}+to+{destination}",
            labels=[],
        ))

    return options


async def search_all_modes(origin: str, destination: str, date: str, adults: int = 1,
                            children: int = 0, modes: Optional[list[str]] = None,
                            weather: Optional[dict] = None) -> list[TransportOption]:
    """Search all transport modes and combine results."""
    if modes is None:
        modes = ["flight", "train", "bus"]

    all_options = []
    searchers = {
        "flight": search_flights,
        "train": search_trains,
        "bus": search_buses,
    }

    for mode in modes:
        if mode in searchers:
            try:
                opts = await searchers[mode](origin, destination, date, adults, children, weather)
                all_options.extend(opts)
            except Exception:
                pass

    return all_options