import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.models.schemas import TripInput, PackingResponse, TripRecord
from app.agent import run_agent
from app.firebase_db import save_trip, get_trip, list_trips, is_firebase_available
from app.routes.transport import router as transport_router
from app.routes.accommodation import router as accommodation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY is not set. The agent will fail on requests.")
    if not is_firebase_available():
        print("WARNING: Firebase is not configured. Trips will not be persisted.")
    yield


app = FastAPI(title="Autonomous Trip Planner", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transport_router)
app.include_router(accommodation_router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "firebase_configured": is_firebase_available(),
    }


@app.post("/api/pack", response_model=PackingResponse)
async def pack(trip: TripInput):
    """Run the packing agent for a trip and optionally save the result."""
    try:
        result = await run_agent(trip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    try:
        trip_doc = {
            "destination": trip.destination,
            "purpose": trip.purpose.value,
            "start_date": trip.start_date,
            "trip_length": trip.trip_length,
            "travelers": [t.model_dump() for t in trip.travelers],
            "weather_summary": result.weather_summary,
            "packing_lists": [pl.model_dump() for pl in result.packing_lists],
        }
        trip_id = await save_trip(trip_doc)
        result.trip_id = trip_id
    except Exception:
        pass

    return result


@app.get("/api/trips/{trip_id}")
async def api_get_trip(trip_id: str):
    trip = await get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.get("/api/trips")
async def api_list_trips(limit: int = 20):
    try:
        trips = await list_trips(limit)
        return {"trips": trips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")