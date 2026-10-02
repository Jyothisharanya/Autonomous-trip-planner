from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

from app.models.transport import (
    TransportSearchRequest, TransportSearchResponse,
    SelectedOptionRequest, DateShiftProposal, DateShiftConfirm,
)
from app.transport_agent import run_transport_agent
from app.firebase_db import save_trip, get_trip

router = APIRouter(prefix="/api/transport", tags=["transport"])


@router.post("/search", response_model=TransportSearchResponse)
async def search_transport(req: TransportSearchRequest):
    """Run an intercity transport search with the agent."""
    try:
        result = await run_transport_agent(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transport agent error: {str(e)}")
    return result


@router.post("/select")
async def select_option(req: SelectedOptionRequest):
    """Mark a transport option as Selected (starts monitoring)."""
    trip = await get_trip(req.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip["selected_transport"] = {
        "option_id": req.option_id,
        "selected_at": datetime.utcnow().isoformat(),
    }
    # Update trip in DB (simplified - in production would use update, not overwrite)
    try:
        from app.firebase_db import is_firebase_available, _init_firebase
        if is_firebase_available():
            db = _init_firebase()
            db.collection("trips").document(req.trip_id).update({
                "selected_transport": trip["selected_transport"],
            })
    except Exception:
        pass

    return {"status": "selected", "option_id": req.option_id, "trip_id": req.trip_id}


@router.post("/dates/propose-shift")
async def propose_date_shift(proposal: DateShiftProposal):
    """Propose a date shift for the traveler to review."""
    return {
        "status": "pending",
        "trip_id": proposal.trip_id,
        "original_date": proposal.original_date,
        "proposed_date": proposal.proposed_date,
        "reason": proposal.reason,
        "message": f"Would you like to shift your travel date from {proposal.original_date} to {proposal.proposed_date}? Reason: {proposal.reason}",
    }


@router.post("/dates/confirm-shift")
async def confirm_date_shift(confirm: DateShiftConfirm):
    """Apply or reject a date shift."""
    if not confirm.accept:
        return {"status": "rejected", "message": "Date shift rejected. Your original dates remain."}

    trip = await get_trip(confirm.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    try:
        from app.firebase_db import is_firebase_available, _init_firebase
        if is_firebase_available():
            db = _init_firebase()
            db.collection("trips").document(confirm.trip_id).update({
                "start_date": confirm.proposed_date,
            })
    except Exception:
        pass

    return {
        "status": "accepted",
        "trip_id": confirm.trip_id,
        "new_date": confirm.proposed_date,
        "message": f"Travel date updated to {confirm.proposed_date}. You may want to re-run transport and accommodation searches.",
    }