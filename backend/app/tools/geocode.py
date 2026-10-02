import httpx

OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


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


async def estimate_distance_km(origin_coords: dict, dest_coords: dict) -> float:
    """Haversine distance between two coordinate pairs."""
    import math
    lat1, lon1 = math.radians(origin_coords["latitude"]), math.radians(origin_coords["longitude"])
    lat2, lon2 = math.radians(dest_coords["latitude"]), math.radians(dest_coords["longitude"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c