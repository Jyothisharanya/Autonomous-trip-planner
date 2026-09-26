import httpx
from datetime import datetime, timedelta

OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

FORECAST_HORIZON_DAYS = 16


async def geocode(destination: str) -> dict:
    """Resolve a place name to coordinates using Open-Meteo geocoding."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPEN_METEO_GEOCODE, params={"name": destination, "count": 1})
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return {"error": f"Could not geocode '{destination}'"}

    r = results[0]
    return {
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "name": r.get("name", destination),
        "country": r.get("country", ""),
        "timezone": r.get("timezone", "UTC"),
    }


async def get_weather_forecast(latitude: float, longitude: float, date: str) -> dict:
    """Get real weather forecast for a specific date (within ~16 days)."""
    target = datetime.strptime(date, "%Y-%m-%d").date()
    today = datetime.utcnow().date()
    days_ahead = (target - today).days

    if days_ahead > FORECAST_HORIZON_DAYS:
        return {"error": f"Date {date} is {days_ahead} days out, beyond the {FORECAST_HORIZON_DAYS}-day forecast horizon."}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPEN_METEO_FORECAST, params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
            "start_date": date,
            "end_date": date,
            "timezone": "auto",
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    if not daily or not daily.get("time"):
        return {"error": "No forecast data available for this date."}

    return {
        "type": "forecast",
        "date": date,
        "temp_max_c": daily["temperature_2m_max"][0],
        "temp_min_c": daily["temperature_2m_min"][0],
        "precipitation_mm": daily["precipitation_sum"][0],
        "weather_code": daily["weathercode"][0],
        "wind_max_kmh": daily["windspeed_10m_max"][0],
    }


async def get_climate_normals(latitude: float, longitude: float, month: int) -> dict:
    """Get historical average conditions for a destination and month."""
    today = datetime.utcnow().date()

    start = datetime(today.year - 10, month, 1).date()
    end = datetime(today.year - 1, month, 28).date()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(OPEN_METEO_ARCHIVE, params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": str(start),
            "end_date": str(end),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    temps_max = [t for t in (daily.get("temperature_2m_max") or []) if t is not None]
    temps_min = [t for t in (daily.get("temperature_2m_min") or []) if t is not None]
    precip = [p for p in (daily.get("precipitation_sum") or []) if p is not None]

    if not temps_max:
        return {"error": "No historical data available for this location/month."}

    return {
        "type": "climate_normal",
        "month": month,
        "avg_temp_max_c": round(sum(temps_max) / len(temps_max), 1),
        "avg_temp_min_c": round(sum(temps_min) / len(temps_min), 1),
        "avg_daily_precip_mm": round(sum(precip) / len(precip), 1) if precip else 0,
        "years_of_data": len(set(
            datetime.strptime(d, "%Y-%m-%d").year
            for d in (daily.get("time") or [])
        )),
    }