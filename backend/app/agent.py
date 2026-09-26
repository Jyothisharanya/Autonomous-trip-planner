import json
import os
from datetime import datetime
from google import genai
from google.genai import types

from app.tools.weather import geocode, get_weather_forecast, get_climate_normals
from app.models.schemas import (
    TripInput, PackingResponse, TravelerPackingList,
    PackingCategory, TravelerInput,
)

MODEL = "gemini-3.5-flash-lite"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client

SYSTEM_PROMPT = """You are a travel packing assistant. Your job is to generate a personalized packing list for each traveler on a trip.

You have access to these tools:
- geocode(destination): Resolve a place name to coordinates. Call this first.
- get_weather_forecast(latitude, longitude, date): Get real forecast for near-term trips (within 16 days).
- get_climate_normals(latitude, longitude, month): Get historical averages for trips beyond the forecast horizon.

Workflow:
1. Call geocode to get coordinates for the destination.
2. Determine if the trip start date is within 16 days. If yes, call get_weather_forecast. If no, call get_climate_normals with the start month.
3. If weather tools fail, proceed anyway and note weather was unavailable.
4. Generate a packing list PER TRAVELER, grouped into these categories: Clothing, Toiletries, Documents, Electronics, Health & Medical, Other.
5. Consider: destination climate, trip purpose, trip length, traveler age.
6. Always indicate whether the weather data came from a real forecast or historical averages.

Return your response as a JSON object with this exact structure:
{
  "weather_summary": "Brief description of expected weather and data source",
  "packing_lists": [
    {
      "traveler_index": 0,
      "age_label": "adult (age 30)",
      "weather_basis": "forecast",
      "categories": [
        {"name": "Clothing", "items": ["item1", "item2"]},
        {"name": "Toiletries", "items": ["item1"]},
        {"name": "Documents", "items": ["item1"]},
        {"name": "Electronics", "items": ["item1"]},
        {"name": "Health & Medical", "items": ["item1"]},
        {"name": "Other", "items": ["item1"]}
      ]
    }
  ]
}

Important:
- weather_basis must be one of: "forecast", "climate_normal", "unavailable"
- Items should be specific and practical
- Adjust quantities based on trip length
- Age-appropriate items (e.g., diapers for infants, medications for seniors)
- Purpose-appropriate items (e.g., formal wear for business, hiking boots for adventure)
- Return ONLY valid JSON, no markdown fences or extra text
"""


def _traveler_age_label(t: TravelerInput) -> str:
    if t.age is not None:
        return f"age {t.age}"
    return t.age_bracket or "adult"


def _build_user_prompt(trip: TripInput) -> str:
    travelers_desc = []
    for i, t in enumerate(trip.travelers):
        label = _traveler_age_label(t)
        travelers_desc.append(f"Traveler {i}: {label}")

    return f"""Trip details:
- Destination: {trip.destination}
- Purpose: {trip.purpose.value}
- Start date: {trip.start_date}
- Trip length: {trip.trip_length} days
- Travelers:
{chr(10).join(travelers_desc)}

Please generate a packing list for each traveler."""


async def run_agent(trip: TripInput) -> PackingResponse:
    """Run the Gemini agent loop with tool calling to generate packing lists."""
    user_prompt = _build_user_prompt(trip)

    tools = types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="geocode",
            description="Resolve a place name to latitude/longitude coordinates.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "destination": types.Schema(type=types.Type.STRING, description="City or region name"),
                },
                required=["destination"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_weather_forecast",
            description="Get real weather forecast for a specific date. Only valid within 16 days from today.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "latitude": types.Schema(type=types.Type.NUMBER),
                    "longitude": types.Schema(type=types.Type.NUMBER),
                    "date": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
                },
                required=["latitude", "longitude", "date"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_climate_normals",
            description="Get historical average weather conditions for a location and month. Use for trips beyond the forecast horizon.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "latitude": types.Schema(type=types.Type.NUMBER),
                    "longitude": types.Schema(type=types.Type.NUMBER),
                    "month": types.Schema(type=types.Type.INTEGER, description="Month number 1-12"),
                },
                required=["latitude", "longitude", "month"],
            ),
        ),
    ])

    config = types.GenerateContentConfig(
        tools=[tools],
        system_instruction=SYSTEM_PROMPT,
        temperature=0.4,
    )

    contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]
    client = _get_client()

    MAX_TURNS = 10
    for _ in range(MAX_TURNS):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts

        has_function_call = any(p.function_call for p in parts)
        if not has_function_call:
            text_parts = [p.text for p in parts if p.text]
            raw = "".join(text_parts).strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"weather_summary": "Could not parse agent response.", "packing_lists": []}

            packing_lists = []
            for i, pl in enumerate(data.get("packing_lists", [])):
                categories = [
                    PackingCategory(name=c["name"], items=c["items"])
                    for c in pl.get("categories", [])
                ]
                packing_lists.append(TravelerPackingList(
                    traveler_index=pl.get("traveler_index", i),
                    age_label=pl.get("age_label", _traveler_age_label(trip.travelers[i])),
                    weather_basis=pl.get("weather_basis", "unavailable"),
                    categories=categories,
                ))

            return PackingResponse(
                destination=trip.destination,
                purpose=trip.purpose.value,
                weather_summary=data.get("weather_summary"),
                packing_lists=packing_lists,
            )

        contents.append(candidate.content)

        function_responses = []
        for part in parts:
            fc = part.function_call
            if not fc:
                continue

            args = dict(fc.args) if fc.args else {}
            result = None

            if fc.name == "geocode":
                result = await geocode(args["destination"])
            elif fc.name == "get_weather_forecast":
                result = await get_weather_forecast(
                    args["latitude"], args["longitude"], args["date"]
                )
            elif fc.name == "get_climate_normals":
                result = await get_climate_normals(
                    args["latitude"], args["longitude"], args["month"]
                )
            else:
                result = {"error": f"Unknown tool: {fc.name}"}

            function_responses.append(types.Part(
                function_response=types.FunctionResponse(
                    name=fc.name,
                    response=result,
                )
            ))

        contents.append(types.Content(role="user", parts=function_responses))

    return PackingResponse(
        destination=trip.destination,
        purpose=trip.purpose.value,
        weather_summary="Agent exceeded maximum turns.",
        packing_lists=[],
    )