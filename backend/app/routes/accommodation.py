from fastapi import APIRouter, HTTPException

from app.models.accommodation import AccommodationSearchRequest, AccommodationSearchResponse
from app.accommodation_agent import run_accommodation_agent

router = APIRouter(prefix="/api/accommodation", tags=["accommodation"])


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodation(req: AccommodationSearchRequest):
    """Search for accommodation options."""
    try:
        result = await run_accommodation_agent(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accommodation search error: {str(e)}")
    return result