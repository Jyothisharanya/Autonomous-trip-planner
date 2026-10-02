import os
from datetime import datetime

from app.models.accommodation import (
    AccommodationSearchRequest, AccommodationSearchResponse,
    ShortlistItem, ArrivalMismatch,
)
from app.tools.accommodation_search import search_and_rank


async def run_accommodation_agent(req: AccommodationSearchRequest) -> AccommodationSearchResponse:
    """Run accommodation search. Uses LLM if available, falls back to direct search."""
    # Calculate nights
    try:
        ci = datetime.strptime(req.check_in, "%Y-%m-%d")
        co = datetime.strptime(req.check_out, "%Y-%m-%d")
        nights = max(1, (co - ci).days)
    except Exception:
        nights = 1

    soft_margin_amount = req.budget_per_night * req.soft_margin_pct / 100

    # If Gemini API key is available, use LLM for enhanced reasoning
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return await _run_with_llm(req, nights, soft_margin_amount)
        except Exception:
            pass

    # Fallback: direct search without LLM
    ranked = await search_and_rank(req)

    shortlist = []
    for i, item in enumerate(ranked):
        stay = item["stay"]
        shortlist.append(ShortlistItem(
            stay=stay,
            rank=i + 1,
            label=item.get("label", ""),
            total_stay_cost=item["total_cost"],
            nights=nights,
            arrival_mismatch=item.get("arrival_mismatch", ArrivalMismatch()),
            score=item["score"],
        ))

    warnings = []
    if not shortlist:
        warnings.append(f"No stays found within ₹{req.budget_per_night}/night budget in {req.city}. Try increasing budget or soft margin.")
    elif all(item.stay.price_per_night_min > req.budget_per_night for item in shortlist):
        warnings.append("All shortlisted stays exceed your budget. Showing closest options within soft margin.")

    return AccommodationSearchResponse(
        city=req.city,
        check_in=req.check_in,
        check_out=req.check_out,
        nights=nights,
        budget_per_night=req.budget_per_night,
        soft_margin=soft_margin_amount,
        total_found=len(shortlist),
        shortlist=shortlist,
        warnings=warnings,
    )


async def _run_with_llm(req: AccommodationSearchRequest, nights: int, soft_margin_amount: float) -> AccommodationSearchResponse:
    """Enhanced search using Gemini LLM for reasoning."""
    from google import genai
    from google.genai import types
    import json

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # First, search and rank
    ranked = await search_and_rank(req)

    # Build stay descriptions for the LLM
    stay_descriptions = []
    for i, item in enumerate(ranked):
        s = item["stay"]
        stay_descriptions.append(
            f"{i+1}. {s.name} ({s.stay_type.value}) - ₹{item['night_price']:.0f}/night, "
            f"Rating: {s.rating}/5 ({s.review_count} reviews), "
            f"Area: {s.address}, Distance: {s.distance_from_anchor_km or 'N/A'}km, "
            f"Amenities: {', '.join(a.value for a in s.amenities)}, "
            f"Check-in: {s.check_in_time}, Check-out: {s.check_out_time}"
        )

    prompt = f"""You are an accommodation planning agent. Help rank and label these stays for a traveler.

Search parameters:
- City: {req.city}
- Check-in: {req.check_in}, Check-out: {req.check_out} ({nights} nights)
- Budget: ₹{req.budget_per_night}/night (soft margin: ₹{soft_margin_amount:.0f})
- Rooms: {req.num_rooms}, Adults: {req.adults}, Children: {req.children}
- Ranking preference: {req.ranking_preference}

Available stays:
{chr(10).join(stay_descriptions)}

For each stay, provide:
1. A short reason why it's good or bad for this traveler
2. Any warnings (e.g., early check-in issues, over budget)
3. A final ranking label (best overall, cheapest good option, closest, highest rated)

Return as JSON:
{{
  "analysis": [
    {{"rank": 1, "name": "Hotel Name", "label": "best overall", "reason": "...", "warning": null}},
    ...
  ],
  "overall_advice": "Brief advice for the traveler"
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(temperature=0.3),
        )
        text = response.candidates[0].content.parts[0].text
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        analysis = json.loads(text.strip())
    except Exception:
        analysis = {"analysis": [], "overall_advice": ""}

    # Apply LLM labels
    llm_labels = {a["name"]: a for a in analysis.get("analysis", [])}

    shortlist = []
    for i, item in enumerate(ranked):
        stay = item["stay"]
        llm_info = llm_labels.get(stay.name, {})
        label = llm_info.get("label", item.get("label", ""))

        shortlist.append(ShortlistItem(
            stay=stay,
            rank=i + 1,
            label=label,
            total_stay_cost=item["total_cost"],
            nights=nights,
            arrival_mismatch=item.get("arrival_mismatch", ArrivalMismatch()),
            score=item["score"],
        ))

    warnings = []
    if not shortlist:
        warnings.append(f"No stays found within ₹{req.budget_per_night}/night budget in {req.city}.")

    return AccommodationSearchResponse(
        city=req.city,
        check_in=req.check_in,
        check_out=req.check_out,
        nights=nights,
        budget_per_night=req.budget_per_night,
        soft_margin=soft_margin_amount,
        total_found=len(shortlist),
        shortlist=shortlist,
        warnings=warnings,
    )