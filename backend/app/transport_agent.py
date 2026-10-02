import json
import os
from datetime import datetime, timedelta
from typing import Optional

from google import genai
from google.genai import types

from app.models.transport import (
    TransportSearchRequest, TransportSearchResponse, TransportOption,
    BudgetStatus, RankingPreference, DataSource,
)
from app.tools.geocode import geocode, estimate_distance_km
from app.tools.weather import get_weather_forecast, get_climate_normals
from app.tools.transport_search import search_all_modes

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


SYSTEM_PROMPT = """You are an autonomous transport planning agent. Your job is to find the best intercity transport options for a traveler.

You have access to these tools:
- geocode(destination): Resolve a place name to coordinates.
- get_weather_forecast(latitude, longitude, date): Get weather forecast for a date.
- get_climate_normals(latitude, longitude, month): Get historical weather for far-future dates.
- search_transport(origin, destination, date, adults, children, modes): Search for transport options across modes (flight, train, bus).

Your workflow:
1. Call geocode for both origin and destination to validate places and get coordinates.
2. Get weather for the travel date to assess weather risk.
3. Determine which transport modes are reasonable for this route (based on distance and region).
4. Call search_transport with the appropriate modes.
5. Review the results: filter by budget, rank by the traveler's preference, and label each option.
6. If no option fits the budget, suggest alternatives (shift dates, try other modes, adjust budget share).

Ranking preferences:
- "cheapest": sort by price_total ascending
- "fastest": sort by duration_total_minutes ascending
- "fewest_transfers": sort by transfers ascending, then price
- "departure_time": sort by departure time
- "arrival_time": sort by arrival time
- "comfort": prefer trains > flights > buses

For custom free-text preferences, interpret them and filter/weight accordingly. Show your interpretation.

Budget handling:
- Options within the transport Budget Share are shown first.
- If the preferred option is over budget, label it "over budget" but still show it.
- If NO option fits, explain why and suggest: (a) shift within Date Window, (b) another mode, (c) raise budget.

Return your analysis as a JSON object with this structure:
{
  "interpreted_preferences": "How you interpreted the traveler's preferences",
  "warnings": ["Any warnings or notes"],
  "recommended_ranking": ["option_id_1", "option_id_2", ...],
  "budget_analysis": {
    "within_budget_count": 0,
    "over_budget_count": 0,
    "cheapest_price": 0,
    "suggestion": "Any budget suggestion"
  }
}

Return ONLY valid JSON, no markdown fences.
"""


def _build_user_prompt(req: TransportSearchRequest) -> str:
    modes_desc = "flight, train, bus"
    pref_desc = req.ranking_preference.value
    if req.custom_preference:
        pref_desc += f" (custom: {req.custom_preference})"

    return f"""Transport search request:
- Origin: {req.origin}
- Destination: {req.destination}
- Date: {req.date}
- Date Window: ±{req.date_window_n} days
- Travelers: {req.travelers_adults} adults, {req.travelers_children} children
- Transport Budget Share: ${req.budget_share:.2f} USD
- Ranking preference: {pref_desc}
- Baggage: {req.packing_bag_count or 'unknown'} bags, {req.packing_weight_kg or 'unknown'} kg
{f'- Return date: {req.return_date}' if req.return_date else ''}

Please search for transport options and provide your analysis."""


def _apply_agent_ranking(options: list[TransportOption], agent_analysis: dict,
                          preference: RankingPreference, budget: float) -> list[TransportOption]:
    """Apply budget status, ranking, and labels to options."""
    for opt in options:
        if opt.price_total > budget:
            opt.budget_status = BudgetStatus.OVER
            opt.budget_over_by = round(opt.price_total - budget, 2)
        else:
            opt.budget_status = BudgetStatus.WITHIN
            opt.budget_over_by = 0

    # Sort based on preference
    if preference == RankingPreference.CHEAPEST:
        options.sort(key=lambda o: o.price_total)
    elif preference == RankingPreference.FASTEST:
        options.sort(key=lambda o: o.duration_total_minutes)
    elif preference == RankingPreference.FEWEST_TRANSFERS:
        options.sort(key=lambda o: (o.transfers, o.price_total))
    elif preference == RankingPreference.COMFORT:
        comfort_order = {"train": 0, "flight": 1, "bus": 2, "car": 3}
        options.sort(key=lambda o: comfort_order.get(o.mode.value, 99))
    elif preference == RankingPreference.CUSTOM:
        ranked_ids = agent_analysis.get("recommended_ranking", [])
        id_order = {oid: i for i, oid in enumerate(ranked_ids)}
        options.sort(key=lambda o: id_order.get(o.id, 999))

    # Apply labels
    if options:
        cheapest = min(options, key=lambda o: o.price_total)
        fastest = min(options, key=lambda o: o.duration_total_minutes)
        fewest = min(options, key=lambda o: o.transfers)

        cheapest.labels.append("cheapest")
        fastest.labels.append("fastest")
        fewest.labels.append("fewest transfers")

        if cheapest.id == fastest.id:
            cheapest.labels.append("best value")

    return options


async def _run_without_llm(req: TransportSearchRequest) -> TransportSearchResponse:
    """Fallback: search and rank without LLM when API key is missing."""
    weather_data = None

    # Try to get weather
    try:
        geo = await geocode(req.origin)
        if "error" not in geo:
            geo_dest = await geocode(req.destination)
            if "error" not in geo_dest:
                from datetime import datetime as dt
                target = dt.strptime(req.date, "%Y-%m-%d").date()
                today = dt.utcnow().date()
                if (target - today).days <= 16:
                    weather_data = await get_weather_forecast(
                        geo_dest["latitude"], geo_dest["longitude"], req.date
                    )
                    if "error" in weather_data:
                        weather_data = None
    except Exception:
        pass

    # Search all modes
    all_options = await search_all_modes(
        req.origin, req.destination, req.date,
        req.travelers_adults, req.travelers_children,
        weather=weather_data,
    )

    analysis = {
        "interpreted_preferences": f"Ranked by {req.ranking_preference.value}" +
            (f" with custom preference: {req.custom_preference}" if req.custom_preference else ""),
        "warnings": ["Running without AI agent (GEMINI_API_KEY not set). Results are estimated."],
        "recommended_ranking": [],
    }

    ranked = _apply_agent_ranking(all_options, analysis, req.ranking_preference, req.budget_share)

    # Date window fallback
    if req.date_window_n > 0 and ranked and all(o.budget_status == BudgetStatus.OVER for o in ranked):
        window_options = []
        for delta in range(-req.date_window_n, req.date_window_n + 1):
            if delta == 0:
                continue
            alt_date = (datetime.strptime(req.date, "%Y-%m-%d") + timedelta(days=delta)).strftime("%Y-%m-%d")
            alt = await search_all_modes(
                req.origin, req.destination, alt_date,
                req.travelers_adults, req.travelers_children,
                weather=weather_data,
            )
            for o in alt:
                o.labels.append(f"date: {alt_date}")
            window_options.extend(alt)

        if window_options:
            ranked.extend(window_options)
            analysis["warnings"].append(
                f"Original date options were over budget. Showing ±{req.date_window_n} day alternatives."
            )

    return TransportSearchResponse(
        origin=req.origin,
        destination=req.destination,
        date=req.date,
        options=ranked,
        total_found=len(ranked),
        ranking_preference=req.ranking_preference.value,
        interpreted_preferences=analysis.get("interpreted_preferences"),
        budget_share=req.budget_share,
        warnings=analysis.get("warnings", []),
    )


async def run_transport_agent(req: TransportSearchRequest) -> TransportSearchResponse:
    """Run the transport agent loop with tool calling."""
    # If no Gemini API key, use direct search fallback
    if not os.environ.get("GEMINI_API_KEY"):
        return await _run_without_llm(req)

    user_prompt = _build_user_prompt(req)

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
            description="Get real weather forecast for a specific date.",
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
            name="search_transport",
            description="Search for intercity transport options between two cities.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "origin": types.Schema(type=types.Type.STRING),
                    "destination": types.Schema(type=types.Type.STRING),
                    "date": types.Schema(type=types.Type.STRING, description="YYYY-MM-DD"),
                    "adults": types.Schema(type=types.Type.INTEGER),
                    "children": types.Schema(type=types.Type.INTEGER),
                    "modes": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Modes to search: flight, train, bus",
                    ),
                },
                required=["origin", "destination", "date", "adults", "children", "modes"],
            ),
        ),
    ])

    config = types.GenerateContentConfig(
        tools=[tools],
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
    )

    contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]
    client = _get_client()

    # Pre-fetch weather for the agent
    weather_data = None
    origin_coords = None
    dest_coords = None
    all_options = []

    MAX_TURNS = 8
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
                analysis = json.loads(raw)
            except json.JSONDecodeError:
                analysis = {"interpreted_preferences": "", "warnings": [], "recommended_ranking": []}

            # If we haven't searched yet, do it now
            if not all_options:
                all_options = await search_all_modes(
                    req.origin, req.destination, req.date,
                    req.travelers_adults, req.travelers_children,
                    weather=weather_data,
                )

            # If still no options (shouldn't happen), generate estimates
            if not all_options:
                analysis.setdefault("warnings", []).append("No transport options found. APIs may be unavailable.")

            # Apply agent's ranking and budget analysis
            ranked = _apply_agent_ranking(
                all_options, analysis,
                req.ranking_preference, req.budget_share
            )

            # Search date window if requested
            if req.date_window_n > 0 and ranked and all(o.budget_status == BudgetStatus.OVER for o in ranked):
                window_options = []
                for delta in range(-req.date_window_n, req.date_window_n + 1):
                    if delta == 0:
                        continue
                    alt_date = (datetime.strptime(req.date, "%Y-%m-%d") + timedelta(days=delta)).strftime("%Y-%m-%d")
                    alt = await search_all_modes(
                        req.origin, req.destination, alt_date,
                        req.travelers_adults, req.travelers_children,
                        weather=weather_data,
                    )
                    for o in alt:
                        o.labels.append(f"date: {alt_date}")
                    window_options.extend(alt)

                if window_options:
                    ranked.extend(window_options)
                    analysis.setdefault("warnings", []).append(
                        f"Original date options were over budget. Showing ±{req.date_window_n} day alternatives."
                    )

            return TransportSearchResponse(
                origin=req.origin,
                destination=req.destination,
                date=req.date,
                options=ranked,
                total_found=len(ranked),
                ranking_preference=req.ranking_preference.value,
                interpreted_preferences=analysis.get("interpreted_preferences"),
                budget_share=req.budget_share,
                warnings=analysis.get("warnings", []),
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
                # Track coordinates
                if "error" not in result:
                    if origin_coords is None:
                        origin_coords = result
                    else:
                        dest_coords = result
            elif fc.name == "get_weather_forecast":
                result = await get_weather_forecast(
                    args["latitude"], args["longitude"], args["date"]
                )
                if result and "error" not in result:
                    weather_data = result
            elif fc.name == "search_transport":
                modes = args.get("modes", ["flight", "train", "bus"])
                all_options = await search_all_modes(
                    args["origin"], args["destination"], args["date"],
                    args.get("adults", 1), args.get("children", 0),
                    modes=modes, weather=weather_data,
                )
                result = {
                    "options_found": len(all_options),
                    "options": [
                        {
                            "id": o.id, "mode": o.mode.value, "provider": o.provider,
                            "price_total": o.price_total, "duration_minutes": o.duration_total_minutes,
                            "transfers": o.transfers, "source": o.source.value,
                        }
                        for o in all_options[:10]
                    ],
                }
            else:
                result = {"error": f"Unknown tool: {fc.name}"}

            function_responses.append(types.Part(
                function_response=types.FunctionResponse(
                    name=fc.name,
                    response=result,
                )
            ))

        contents.append(types.Content(role="user", parts=function_responses))

    # Fallback if we exit the loop without a text response
    if not all_options:
        all_options = await search_all_modes(
            req.origin, req.destination, req.date,
            req.travelers_adults, req.travelers_children,
            weather=weather_data,
        )

    ranked = _apply_agent_ranking(
        all_options, {},
        req.ranking_preference, req.budget_share
    )

    return TransportSearchResponse(
        origin=req.origin,
        destination=req.destination,
        date=req.date,
        options=ranked,
        total_found=len(ranked),
        ranking_preference=req.ranking_preference.value,
        budget_share=req.budget_share,
        warnings=["Agent exceeded maximum turns. Showing unranked results."],
    )