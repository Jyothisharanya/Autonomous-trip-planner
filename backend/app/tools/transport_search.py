import httpx
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

from app.models.transport import (
    TransportOption, TransportMode, Leg, BaggageAllowance,
    WeatherRisk, WeatherRiskLevel, DataSource, BudgetStatus,
)

# Indian airport IATA codes mapping
INDIAN_AIRPORTS = {
    "delhi": "DEL", "new delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR",
    "bengaluru": "BLR", "chennai": "MAA", "kolkata": "CCU", "hyderabad": "HYD",
    "pune": "PNQ", "ahmedabad": "AMD", "jaipur": "JAI", "lucknow": "LKO",
    "kochi": "COK", "cochin": "COK", "goa": "GOI", "guwahati": "GAU",
    "thiruvananthapuram": "TRV", "trivandrum": "TRV", "bhubaneswar": "BBI",
    "nagpur": "NAG", "indore": "IDR", "coimbatore": "CJB", "visakhapatnam": "VTZ",
    "patna": "PAT", "vadodara": "BDQ", "surat": "STV", "chandigarh": "IXC",
    "amritsar": "ATQ", "varanasi": "VNS", "srinagar": "SXR", "ranchi": "IXR",
    "raipur": "RPR", "madurai": "IXM", "jodhpur": "JDH", "udaipur": "UDR",
    "dehradun": "DED", "agra": "AGR", "mangalore": "IXE", "tiruchirappalli": "TRZ",
    "mysore": "MYQ", "hubli": "HBX", "agra": "AGR",
}

# Major Indian railway stations
INDIAN_RAILWAY_STATIONS = {
    "delhi": "NDLS", "new delhi": "NDLS", "mumbai": "CSTM", "chennai": "MAS",
    "kolkata": "HWH", "howrah": "HWH", "bangalore": "SBC", "bengaluru": "SBC",
    "hyderabad": "SC", "secunderabad": "SC", "pune": "PUNE", "ahmedabad": "ADI",
    "jaipur": "JP", "lucknow": "LKO", "kochi": "ERS", "ernakulam": "ERS",
    "goa": "MAO", "madgaon": "MAO", "guwahati": "GHY", "thiruvananthapuram": "TVC",
    "trivandrum": "TVC", "bhubaneswar": "BBS", "nagpur": "NGP", "indore": "INDB",
    "coimbatore": "CBE", "visakhapatnam": "VSKP", "patna": "PNBE",
    "vadodara": "BRC", "surat": "ST", "chandigarh": "CDG", "amritsar": "ASR",
    "varanasi": "BSB", "srinagar": "SINA", "ranchi": "RNC", "raipur": "R",
    "jodhpur": "JU", "udaipur": "UDZ", "dehradun": "DDN", "mysore": "MYS",
}

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


def _resolve_iata(city: str) -> Optional[str]:
    """Resolve city name to IATA airport code."""
    return INDIAN_AIRPORTS.get(city.lower().strip())


def _resolve_railway_station(city: str) -> Optional[str]:
    """Resolve city name to railway station code."""
    return INDIAN_RAILWAY_STATIONS.get(city.lower().strip())


async def _get_amadeus_token() -> Optional[str]:
    """Get Amadeus API access token."""
    client_id = os.environ.get("AMADEUS_CLIENT_ID", "")
    client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    base = os.environ.get("AMADEUS_BASE_URL", "https://api.amadeus.com")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{base}/v1/security/oauth2/token", data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            })
            resp.raise_for_status()
            return resp.json().get("access_token")
    except Exception:
        return None


async def search_flights(origin: str, destination: str, date: str, adults: int = 1,
                          children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    """Search flights using Amadeus API (real data) with fallback to estimates."""
    origin_code = _resolve_iata(origin)
    dest_code = _resolve_iata(destination)
    options = []

    # Try Amadeus API first
    token = await _get_amadeus_token()
    if token and origin_code and dest_code:
        try:
            base = os.environ.get("AMADEUS_BASE_URL", "https://api.amadeus.com")
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{base}/v2/shopping/flight-offers", params={
                    "originLocationCode": origin_code,
                    "destinationLocationCode": dest_code,
                    "departureDate": date,
                    "adults": adults,
                    "children": children,
                    "max": 6,
                    "currencyCode": "INR",
                }, headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
                data = resp.json()

                for offer in data.get("data", []):
                    try:
                        segments = offer["itineraries"][0]["segments"]
                        legs = []
                        total_duration = 0
                        for seg in segments:
                            dep = seg["departure"]
                            arr = seg["arrival"]
                            legs.append(Leg(
                                **{"from": dep["iataCode"], "to": arr["iataCode"]},
                                departure=dep["at"],
                                arrival=arr["at"],
                                vehicle_number=seg.get("carrierCode", "") + seg.get("number", ""),
                                carrier=seg.get("carrierCode", ""),
                            ))
                            # Parse duration
                            dur_str = seg.get("duration", "PT0M")
                            mins = 0
                            if "H" in dur_str:
                                h = int(dur_str.split("H")[0].replace("PT", ""))
                                mins += h * 60
                            if "M" in dur_str:
                                m_part = dur_str.split("H")[-1] if "H" in dur_str else dur_str.replace("PT", "")
                                m = int(m_part.replace("M", ""))
                                mins += m
                            total_duration += mins

                        price_info = offer.get("price", {})
                        total_price = float(price_info.get("total", 0))
                        currency = price_info.get("currency", "INR")

                        carrier_codes = set()
                        for seg in segments:
                            carrier_codes.add(seg.get("carrierCode", ""))

                        wr = _weather_risk_for_departure(weather, datetime.fromisoformat(segments[0]["departure"]["at"]))

                        options.append(TransportOption(
                            id=_make_id(origin, destination, date, "flight", str(offer.get("id", ""))),
                            mode=TransportMode.FLIGHT,
                            provider=", ".join(carrier_codes),
                            legs=legs,
                            duration_total_minutes=total_duration or 120,
                            transfers=len(segments) - 1,
                            price_base=total_price,
                            currency=currency,
                            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=15, extra_bag_fee_est=4150),
                            baggage_fee_est=0,
                            price_total=total_price,
                            budget_status=BudgetStatus.WITHIN,
                            weather_risk=wr,
                            source=DataSource.API,
                            fetched_at=datetime.utcnow().isoformat(),
                            deep_link=f"https://www.google.com/flights?q=flights+from+{origin}+to+{destination}+on+{date}",
                            labels=[],
                        ))
                    except Exception:
                        continue

                if options:
                    return options
        except Exception:
            pass

    # Fallback: estimated options with Indian airline names
    import random
    carriers = ["IndiGo", "Air India", "SpiceJet", "Vistara", "AirAsia India", "GoFirst"]
    departure_hours = [5, 7, 9, 11, 14, 17, 20, 22]

    for i in range(min(5, len(carriers))):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:00", "%Y-%m-%d %H:%M")
        duration = random.randint(90, 180)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        price = random.randint(3500, 12000) * pax

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
            currency="INR",
            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=15, extra_bag_fee_est=4150),
            baggage_fee_est=0,
            price_total=round(price, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.makemytrip.com/flight/search?origin={origin}&destination={destination}&date={date}",
            labels=[],
        ))

    return options


async def search_trains(origin: str, destination: str, date: str, adults: int = 1,
                         children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    """Search trains using erail.in API (free, no key required) with real Indian Railway data."""
    origin_code = _resolve_railway_station(origin)
    dest_code = _resolve_railway_station(destination)
    options = []

    # Try erail.in API (free, no authentication required)
    if origin_code and dest_code:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://erail.in/rail/getTrains.aspx",
                    params={
                        "Station_From": origin_code,
                        "Station_To": dest_code,
                        "DataSource": "0",
                        "Language": "0",
                    }
                )
                resp.raise_for_status()
                raw = resp.text
                
                # Parse erail.in response format
                # Each train is separated by ^, fields separated by ~
                records = raw.split("^")
                
                for record in records[1:]:  # Skip first empty record
                    try:
                        fields = record.split("~")
                        if len(fields) < 40:
                            continue
                        
                        train_number = fields[0].strip()
                        train_name = fields[1].strip()
                        source_station = fields[2].strip()
                        source_code = fields[3].strip()
                        dest_station = fields[4].strip()
                        dest_code_field = fields[5].strip()
                        
                        # Boarding and alighting points
                        board_station = fields[6].strip()
                        board_code = fields[7].strip()
                        alight_station = fields[8].strip()
                        alight_code = fields[9].strip()
                        
                        # Departure and arrival times
                        dep_time_str = fields[10].strip()
                        arr_time_str = fields[11].strip()
                        duration_str = fields[12].strip()
                        
                        if not dep_time_str or not arr_time_str:
                            continue
                        
                        # Parse departure time (format: HH.MM)
                        dep_parts = dep_time_str.replace(".", ":").split(":")
                        dep_hour = int(dep_parts[0])
                        dep_min = int(dep_parts[1]) if len(dep_parts) > 1 else 0
                        
                        # Parse arrival time
                        arr_parts = arr_time_str.replace(".", ":").split(":")
                        arr_hour = int(arr_parts[0])
                        arr_min = int(arr_parts[1]) if len(arr_parts) > 1 else 0
                        
                        dep = datetime.strptime(f"{date} {dep_hour:02d}:{dep_min:02d}", "%Y-%m-%d %H:%M")
                        arr = datetime.strptime(f"{date} {arr_hour:02d}:{arr_min:02d}", "%Y-%m-%d %H:%M")
                        if arr < dep:
                            arr += timedelta(days=1)
                        
                        duration_mins = int((arr - dep).total_seconds() / 60)
                        if duration_mins <= 0:
                            # Parse duration from HH.MM format
                            dur_parts = duration_str.split(".")
                            if len(dur_parts) == 2:
                                duration_mins = int(dur_parts[0]) * 60 + int(dur_parts[1])
                            else:
                                duration_mins = 600
                        
                        # Parse train type
                        train_type = fields[32].strip() if len(fields) > 32 else ""
                        days_of_run = fields[13].strip() if len(fields) > 13 else ""
                        
                        # Parse fares from field41
                        # Format: TRAIN_TYPE:BASE_FARE:CLASS1_FARES:CLASS2_FARES:...
                        pax = adults + children
                        fare_data = fields[41].strip() if len(fields) > 41 else ""
                        
                        # Extract fare based on train type and class
                        fare = 0
                        if fare_data:
                            parts = fare_data.split(":")
                            if len(parts) > 2:
                                # First part is train type, second is base fare
                                try:
                                    base_fare = float(parts[1])
                                    # Use 3AC fare (index 2) if available, else SL (index 4)
                                    for i, class_fares in enumerate(parts[2:], 2):
                                        if class_fares.strip():
                                            fares = class_fares.split(",")
                                            # Try to get 3AC fare (usually 3rd non-empty class)
                                            if len(fares) >= 3 and fares[2].strip():
                                                fare = float(fares[2]) * pax
                                                break
                                            elif len(fares) >= 1 and fares[0].strip():
                                                fare = float(fares[0]) * pax
                                                break
                                except:
                                    pass
                        
                        if fare <= 0:
                            # Estimate based on train type
                            if "RAJDHANI" in train_type.upper():
                                fare = random.randint(2000, 4000) * pax
                            elif "SHATABDI" in train_type.upper():
                                fare = random.randint(1500, 3000) * pax
                            elif "DURONTO" in train_type.upper():
                                fare = random.randint(1800, 3500) * pax
                            elif "SUPERFAST" in train_type.upper():
                                fare = random.randint(800, 2000) * pax
                            else:
                                fare = random.randint(500, 1500) * pax
                        
                        wr = _weather_risk_for_departure(weather, dep)
                        
                        # Build vehicle number (train number)
                        vehicle = train_number
                        
                        options.append(TransportOption(
                            id=_make_id(origin, destination, date, "train", train_number),
                            mode=TransportMode.TRAIN,
                            provider=train_name,
                            legs=[Leg(
                                **{"from": origin, "to": destination},
                                departure=dep.isoformat(),
                                arrival=arr.isoformat(),
                                vehicle_number=vehicle,
                                carrier=train_name,
                            )],
                            duration_total_minutes=duration_mins,
                            transfers=0,
                            price_base=fare,
                            currency="INR",
                            baggage_allowance=None,
                            baggage_fee_est=0,
                            price_total=fare,
                            budget_status=BudgetStatus.WITHIN,
                            weather_risk=wr,
                            source=DataSource.API,
                            fetched_at=datetime.utcnow().isoformat(),
                            deep_link=f"https://www.irctc.co.in/nget/train-search?from={origin_code}&to={dest_code}&date={date}",
                            labels=[],
                        ))
                    except Exception:
                        continue

                if options:
                    return options
        except Exception:
            pass

    # Fallback: curated Indian trains with realistic fares
    import random
    trains = [
        {"name": "Rajdhani Express", "number": "12951", "type": "premium"},
        {"name": "Shatabdi Express", "number": "12002", "type": "premium"},
        {"name": "Duronto Express", "number": "12213", "type": "express"},
        {"name": "Garib Rath", "number": "12215", "type": "budget"},
        {"name": "Superfast Express", "number": "12625", "type": "express"},
        {"name": "Jan Shatabdi", "number": "12058", "type": "budget"},
    ]
    departure_hours = [5, 6, 8, 10, 14, 16, 18, 21, 23]

    fare_ranges = {"premium": (1500, 5000), "express": (800, 2500), "budget": (400, 1200)}

    for i, train in enumerate(trains[:5]):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:{random.randint(0,59):02d}", "%Y-%m-%d %H:%M")
        duration = random.randint(180, 900)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        low, high = fare_ranges.get(train["type"], (500, 2000))
        fare = random.randint(low, high) * pax

        wr = _weather_risk_for_departure(weather, dep)

        options.append(TransportOption(
            id=_make_id(origin, destination, date, "train", train["number"]),
            mode=TransportMode.TRAIN,
            provider=train["name"],
            legs=[Leg(
                **{"from": origin, "to": destination},
                departure=dep.isoformat(),
                arrival=arr.isoformat(),
                vehicle_number=train["number"],
                carrier=train["name"],
            )],
            duration_total_minutes=duration,
            transfers=0,
            price_base=round(fare, 2),
            currency="INR",
            baggage_allowance=None,
            baggage_fee_est=0,
            price_total=round(fare, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.irctc.co.in/nget/train-search",
            labels=[],
        ))

    return options


async def search_buses(origin: str, destination: str, date: str, adults: int = 1,
                        children: int = 0, weather: Optional[dict] = None) -> list[TransportOption]:
    """Search buses using RedBus/AbhiBus API with fallback to curated data."""
    options = []

    # Try RedBus API if available
    redbus_key = os.environ.get("REDBUS_API_KEY", "")
    if redbus_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.redbus.in/v2/search",
                    params={"src": origin, "dest": destination, "doj": date},
                    headers={"Authorization": f"Bearer {redbus_key}"}
                )
                resp.raise_for_status()
                data = resp.json()
                for bus in data.get("buses", [])[:5]:
                    try:
                        fare = float(bus.get("fare", 0)) * adults
                        dep = datetime.strptime(f"{date} {bus.get('departure', '20:00')}", "%Y-%m-%d %H:%M")
                        arr = datetime.strptime(f"{date} {bus.get('arrival', '06:00')}", "%Y-%m-%d %H:%M")
                        if arr < dep:
                            arr += timedelta(days=1)
                        dur = int((arr - dep).total_seconds() / 60)

                        options.append(TransportOption(
                            id=_make_id(origin, destination, date, "bus", bus.get("operator", "")),
                            mode=TransportMode.BUS,
                            provider=bus.get("operator", "Bus Operator"),
                            legs=[Leg(
                                **{"from": origin, "to": destination},
                                departure=dep.isoformat(),
                                arrival=arr.isoformat(),
                                vehicle_number=bus.get("bus_number", ""),
                                carrier=bus.get("operator", ""),
                            )],
                            duration_total_minutes=dur,
                            transfers=0,
                            price_base=fare,
                            currency="INR",
                            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=15),
                            baggage_fee_est=0,
                            price_total=fare,
                            budget_status=BudgetStatus.WITHIN,
                            weather_risk=_weather_risk_for_departure(weather, dep),
                            source=DataSource.API,
                            fetched_at=datetime.utcnow().isoformat(),
                            deep_link=f"https://www.redbus.in/bus-tickets/{origin.lower()}-to-{destination.lower()}",
                            labels=[],
                        ))
                    except Exception:
                        continue

                if options:
                    return options
        except Exception:
            pass

    # Fallback: curated Indian bus operators
    import random
    operators = [
        {"name": "KSRTC", "type": "govt"},
        {"name": "APSRTC", "type": "govt"},
        {"name": "TSRTC", "type": "govt"},
        {"name": "SRS Travels", "type": "private"},
        {"name": "VRL Travels", "type": "private"},
        {"name": "Orange Travels", "type": "private"},
        {"name": "KPN Travels", "type": "private"},
        {"name": "Neeta Travels", "type": "private"},
    ]
    departure_hours = [5, 7, 9, 11, 14, 17, 19, 21, 23]

    fare_ranges = {"govt": (300, 1200), "private": (500, 2500)}

    for i, op in enumerate(operators[:5]):
        dep_hour = departure_hours[i % len(departure_hours)]
        dep = datetime.strptime(f"{date} {dep_hour:02d}:{random.randint(0,59):02d}", "%Y-%m-%d %H:%M")
        duration = random.randint(180, 720)
        arr = dep + timedelta(minutes=duration)
        pax = adults + children
        low, high = fare_ranges.get(op["type"], (400, 1500))
        fare = random.randint(low, high) * pax

        wr = _weather_risk_for_departure(weather, dep)

        options.append(TransportOption(
            id=_make_id(origin, destination, date, "bus", op["name"]),
            mode=TransportMode.BUS,
            provider=op["name"],
            legs=[Leg(
                **{"from": origin, "to": destination},
                departure=dep.isoformat(),
                arrival=arr.isoformat(),
                vehicle_number=f"{''.join(w[0] for w in op['name'].split())}{random.randint(100,999)}",
                carrier=op["name"],
            )],
            duration_total_minutes=duration,
            transfers=0,
            price_base=round(fare, 2),
            currency="INR",
            baggage_allowance=BaggageAllowance(included_bags=1, included_weight_kg=15),
            baggage_fee_est=0,
            price_total=round(fare, 2),
            budget_status=BudgetStatus.WITHIN,
            weather_risk=wr,
            source=DataSource.ESTIMATE,
            fetched_at=datetime.utcnow().isoformat(),
            deep_link=f"https://www.redbus.in/bus-tickets/{origin.lower()}-to-{destination.lower()}",
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