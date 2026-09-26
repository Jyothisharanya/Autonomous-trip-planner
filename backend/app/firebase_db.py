import os
import json
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def _init_firebase():
    global _db
    if _db is not None:
        return _db

    cred_path = os.environ.get("FIREBASE_CREDENTIALS")
    cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

    if cred_json:
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    elif cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        raise RuntimeError(
            "Firebase credentials not found. Set FIREBASE_CREDENTIALS (path to JSON file) "
            "or FIREBASE_CREDENTIALS_JSON (JSON string)."
        )

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


async def save_trip(trip_data: dict) -> str:
    db = _init_firebase()
    doc_ref = db.collection("trips").document()
    trip_data["created_at"] = datetime.now(timezone.utc).isoformat()
    doc_ref.set(trip_data)
    return doc_ref.id


async def get_trip(trip_id: str) -> Optional[dict]:
    db = _init_firebase()
    doc = db.collection("trips").document(trip_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


async def list_trips(limit: int = 20) -> list[dict]:
    db = _init_firebase()
    docs = (
        db.collection("trips")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    trips = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        trips.append(data)
    return trips