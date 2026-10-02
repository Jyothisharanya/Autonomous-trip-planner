import hashlib
import math
import os
from datetime import datetime
from typing import Optional

import httpx

from app.models.accommodation import (
    Stay, StayType, RoomOption, RoomType, Amenity,
    ArrivalMismatch, AccommodationSearchRequest,
)

# Curated Indian hotel data by city
CURATED_STAYS = {
    "delhi": [
        {"name": "Hotel Ajanta", "type": "hotel", "area": "Paharganj", "rating": 3.8, "reviews": 2450, "min": 1200, "max": 3500, "lat": 28.6448, "lon": 77.2167, "amenities": ["wifi", "ac", "room_service", "power_backup"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Zostel Delhi", "type": "hostel", "area": "Paharganj", "rating": 4.2, "reviews": 1800, "min": 500, "max": 1500, "lat": 28.6440, "lon": 77.2160, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "The Imperial", "type": "hotel", "area": "Connaught Place", "rating": 4.7, "reviews": 5600, "min": 8000, "max": 25000, "lat": 28.6315, "lon": 77.2167, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "FabHotel Prime Residency", "type": "hotel", "area": "Karol Bagh", "rating": 4.0, "reviews": 1200, "min": 1800, "max": 4000, "lat": 28.6519, "lon": 77.1898, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "HomeStay @ Defence Colony", "type": "homestay", "area": "Defence Colony", "rating": 4.5, "reviews": 320, "min": 2500, "max": 5000, "lat": 28.5733, "lon": 77.2342, "amenities": ["wifi", "ac", "breakfast", "kitchen", "parking", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
        {"name": "OYO Townhouse", "type": "hotel", "area": "Lajpat Nagar", "rating": 3.9, "reviews": 890, "min": 1400, "max": 3000, "lat": 28.5677, "lon": 77.2405, "amenities": ["wifi", "ac", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Treebo Trend", "type": "hotel", "area": "Mahipalpur", "rating": 3.7, "reviews": 1560, "min": 1100, "max": 2800, "lat": 28.5488, "lon": 77.1340, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
    ],
    "mumbai": [
        {"name": "Hotel Residency Fort", "type": "hotel", "area": "Fort", "rating": 3.9, "reviews": 1800, "min": 2500, "max": 6000, "lat": 18.9400, "lon": 72.8350, "amenities": ["wifi", "ac", "room_service", "restaurant"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Zostel Mumbai", "type": "hostel", "area": "Colaba", "rating": 4.3, "reviews": 2100, "min": 600, "max": 1800, "lat": 18.9067, "lon": 72.8147, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "The Taj Mahal Palace", "type": "hotel", "area": "Colaba", "rating": 4.8, "reviews": 12000, "min": 15000, "max": 50000, "lat": 18.9220, "lon": 72.8332, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "FabHotel Juhu", "type": "hotel", "area": "Juhu", "rating": 4.1, "reviews": 950, "min": 2000, "max": 4500, "lat": 19.0970, "lon": 72.8266, "amenities": ["wifi", "ac", "breakfast", "parking"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Guesthouse @ Bandra", "type": "guesthouse", "area": "Bandra West", "rating": 4.4, "reviews": 420, "min": 3000, "max": 7000, "lat": 19.0596, "lon": 72.8295, "amenities": ["wifi", "ac", "breakfast", "kitchen", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
        {"name": "OYO Townhouse Andheri", "type": "hotel", "area": "Andheri East", "rating": 3.8, "reviews": 1100, "min": 1500, "max": 3500, "lat": 19.1136, "lon": 72.8697, "amenities": ["wifi", "ac", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
    ],
    "bangalore": [
        {"name": "The Park Bangalore", "type": "hotel", "area": "MG Road", "rating": 4.3, "reviews": 3200, "min": 5000, "max": 12000, "lat": 12.9716, "lon": 77.5946, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Zostel Bangalore", "type": "hostel", "area": "Koramangala", "rating": 4.4, "reviews": 1600, "min": 500, "max": 1500, "lat": 12.9352, "lon": 77.6245, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Treebo Trip Indiranagar", "type": "hotel", "area": "Indiranagar", "rating": 4.0, "reviews": 1200, "min": 1800, "max": 4000, "lat": 12.9784, "lon": 77.6408, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Homestay @ Whitefield", "type": "homestay", "area": "Whitefield", "rating": 4.6, "reviews": 280, "min": 2000, "max": 5000, "lat": 12.9698, "lon": 77.7500, "amenities": ["wifi", "ac", "breakfast", "kitchen", "parking", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
        {"name": "FabHotel Electronic City", "type": "hotel", "area": "Electronic City", "rating": 3.9, "reviews": 800, "min": 1500, "max": 3500, "lat": 12.8458, "lon": 77.6553, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
    ],
    "goa": [
        {"name": "Zostel Goa", "type": "hostel", "area": "Anjuna", "rating": 4.5, "reviews": 3200, "min": 400, "max": 1200, "lat": 15.5734, "lon": 73.7408, "amenities": ["wifi", "ac", "kitchen", "pool", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Resort Rio", "type": "resort", "area": "Baga", "rating": 4.4, "reviews": 2800, "min": 4000, "max": 10000, "lat": 15.5563, "lon": 73.7513, "amenities": ["wifi", "ac", "pool", "restaurant", "room_service", "parking", "gym"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "The Leela Goa", "type": "resort", "area": "Cavelossim", "rating": 4.7, "reviews": 4500, "min": 12000, "max": 35000, "lat": 15.1730, "lon": 73.9419, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking", "hot_water"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Beach House Calangute", "type": "homestay", "area": "Calangute", "rating": 4.1, "reviews": 650, "min": 1500, "max": 4000, "lat": 15.5438, "lon": 73.7553, "amenities": ["wifi", "ac", "kitchen", "hot_water"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Treehouse Neptune", "type": "hotel", "area": "Panaji", "rating": 4.0, "reviews": 900, "min": 2500, "max": 6000, "lat": 15.4909, "lon": 73.8278, "amenities": ["wifi", "ac", "breakfast", "restaurant", "pool"], "check_in": "12:00", "check_out": "11:00"},
    ],
    "jaipur": [
        {"name": "Zostel Jaipur", "type": "hostel", "area": "Hawa Mahal Road", "rating": 4.3, "reviews": 2100, "min": 400, "max": 1200, "lat": 26.9239, "lon": 75.8267, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Hotel Pearl Palace", "type": "hotel", "area": "Hathroi Fort", "rating": 4.6, "reviews": 3800, "min": 1200, "max": 3500, "lat": 26.9117, "lon": 75.7872, "amenities": ["wifi", "ac", "breakfast", "room_service", "power_backup"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Rambagh Palace", "type": "hotel", "area": "Bhawani Singh Road", "rating": 4.8, "reviews": 6200, "min": 20000, "max": 60000, "lat": 26.8933, "lon": 75.8073, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "HomeStay Pink City", "type": "homestay", "area": "Bani Park", "rating": 4.4, "reviews": 450, "min": 1500, "max": 4000, "lat": 26.9260, "lon": 75.7877, "amenities": ["wifi", "ac", "breakfast", "kitchen", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
        {"name": "FabHotel Heritage", "type": "hotel", "area": "MI Road", "rating": 4.0, "reviews": 780, "min": 1800, "max": 4500, "lat": 26.9120, "lon": 75.7860, "amenities": ["wifi", "ac", "breakfast", "restaurant"], "check_in": "12:00", "check_out": "11:00"},
    ],
    "chennai": [
        {"name": "The Residency Towers", "type": "hotel", "area": "T Nagar", "rating": 4.2, "reviews": 2100, "min": 3000, "max": 7000, "lat": 13.0405, "lon": 80.2337, "amenities": ["wifi", "ac", "pool", "restaurant", "room_service", "gym"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Zostel Chennai", "type": "hostel", "area": "Mylapore", "rating": 4.1, "reviews": 800, "min": 500, "max": 1500, "lat": 13.0339, "lon": 80.2676, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Treebo Trip", "type": "hotel", "area": "Anna Nagar", "rating": 3.8, "reviews": 650, "min": 1500, "max": 3500, "lat": 13.0850, "lon": 80.2101, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Guesthouse Besant Nagar", "type": "guesthouse", "area": "Besant Nagar", "rating": 4.5, "reviews": 320, "min": 2500, "max": 5500, "lat": 12.9988, "lon": 80.2670, "amenities": ["wifi", "ac", "breakfast", "kitchen", "parking"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "kolkata": [
        {"name": "The Astor Hotel", "type": "hotel", "area": "Theater Road", "rating": 4.1, "reviews": 1500, "min": 3000, "max": 8000, "lat": 22.5449, "lon": 88.3512, "amenities": ["wifi", "ac", "restaurant", "room_service", "laundry"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Zostel Kolkata", "type": "hostel", "area": "Sudder Street", "rating": 4.2, "reviews": 1200, "min": 400, "max": 1200, "lat": 22.5602, "lon": 88.3518, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Treebo Park Plaza", "type": "hotel", "area": "Salt Lake", "rating": 3.9, "reviews": 700, "min": 1500, "max": 3500, "lat": 22.5804, "lon": 88.4171, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Homestay @ Ballygunge", "type": "homestay", "area": "Ballygunge", "rating": 4.5, "reviews": 280, "min": 2000, "max": 5000, "lat": 22.5293, "lon": 88.3642, "amenities": ["wifi", "ac", "breakfast", "kitchen", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "hyderabad": [
        {"name": "Hotel Minerva Grand", "type": "hotel", "area": "Secunderabad", "rating": 4.1, "reviews": 1800, "min": 2000, "max": 5000, "lat": 17.4399, "lon": 78.4983, "amenities": ["wifi", "ac", "breakfast", "restaurant", "room_service"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Zostel Hyderabad", "type": "hostel", "area": "Banjara Hills", "rating": 4.3, "reviews": 1400, "min": 500, "max": 1500, "lat": 17.4156, "lon": 78.4347, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Taj Falaknuma Palace", "type": "hotel", "area": "Falaknuma", "rating": 4.9, "reviews": 4200, "min": 25000, "max": 70000, "lat": 17.3317, "lon": 78.4585, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Treebo Comfort", "type": "hotel", "area": "Hitech City", "rating": 3.9, "reviews": 900, "min": 1500, "max": 3500, "lat": 17.4435, "lon": 78.3772, "amenities": ["wifi", "ac", "breakfast", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        {"name": "Homestay Jubilee Hills", "type": "homestay", "area": "Jubilee Hills", "rating": 4.6, "reviews": 350, "min": 3000, "max": 7000, "lat": 17.4239, "lon": 78.4091, "amenities": ["wifi", "ac", "breakfast", "kitchen", "parking", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "udaipur": [
        {"name": "Zostel Udaipur", "type": "hostel", "area": "Lal Ghat", "rating": 4.5, "reviews": 2400, "min": 400, "max": 1200, "lat": 24.5764, "lon": 73.6913, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Hotel Udai Kothi", "type": "hotel", "area": "Lal Ghat", "rating": 4.3, "reviews": 1200, "min": 2500, "max": 6000, "lat": 24.5770, "lon": 73.6920, "amenities": ["wifi", "ac", "pool", "restaurant", "room_service"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "The Oberoi Udaivilas", "type": "resort", "area": "Lake Pichola", "rating": 4.9, "reviews": 5800, "min": 30000, "max": 80000, "lat": 24.5710, "lon": 73.6810, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking", "hot_water"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Homestay Lake View", "type": "homestay", "area": "Gangaur Ghat", "rating": 4.4, "reviews": 380, "min": 1500, "max": 4000, "lat": 24.5750, "lon": 73.6880, "amenities": ["wifi", "ac", "breakfast", "kitchen", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "varanasi": [
        {"name": "Zostel Varanasi", "type": "hostel", "area": "Assi Ghat", "rating": 4.4, "reviews": 1800, "min": 400, "max": 1200, "lat": 25.2867, "lon": 83.0082, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Hotel Ganges View", "type": "hotel", "area": "Assi Ghat", "rating": 4.2, "reviews": 950, "min": 2000, "max": 5000, "lat": 25.2870, "lon": 83.0085, "amenities": ["wifi", "ac", "breakfast", "restaurant", "room_service"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "BrijRama Palace", "type": "hotel", "area": "Dashashwamedh Ghat", "rating": 4.6, "reviews": 2200, "min": 8000, "max": 20000, "lat": 25.3045, "lon": 83.0106, "amenities": ["wifi", "ac", "restaurant", "room_service", "laundry", "power_backup"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Homestay Near Ghats", "type": "homestay", "area": "Godowlia", "rating": 4.3, "reviews": 280, "min": 1200, "max": 3000, "lat": 25.3050, "lon": 83.0100, "amenities": ["wifi", "ac", "breakfast", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "kochi": [
        {"name": "Zostel Kochi", "type": "hostel", "area": "Fort Kochi", "rating": 4.4, "reviews": 1600, "min": 400, "max": 1200, "lat": 9.9638, "lon": 76.2434, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Hotel Travancore Court", "type": "hotel", "area": "MG Road", "rating": 4.1, "reviews": 1100, "min": 2500, "max": 6000, "lat": 9.9716, "lon": 76.2810, "amenities": ["wifi", "ac", "restaurant", "room_service", "gym"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "CGH Earth Brunton Boatyard", "type": "hotel", "area": "Fort Kochi", "rating": 4.7, "reviews": 2800, "min": 10000, "max": 25000, "lat": 9.9650, "lon": 76.2420, "amenities": ["wifi", "ac", "pool", "restaurant", "room_service", "laundry", "parking"], "check_in": "14:00", "check_out": "12:00"},
        {"name": "Homestay Fort Kochi", "type": "homestay", "area": "Fort Kochi", "rating": 4.5, "reviews": 420, "min": 1800, "max": 4500, "lat": 9.9630, "lon": 76.2440, "amenities": ["wifi", "ac", "breakfast", "kitchen", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
    "agra": [
        {"name": "Hotel Atulyaa Taj", "type": "hotel", "area": "Tajganj", "rating": 4.3, "reviews": 1800, "min": 2000, "max": 5000, "lat": 27.1751, "lon": 78.0421, "amenities": ["wifi", "ac", "breakfast", "restaurant", "room_service", "power_backup"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Zostel Agra", "type": "hostel", "area": "Tajganj", "rating": 4.2, "reviews": 1200, "min": 400, "max": 1200, "lat": 27.1740, "lon": 78.0430, "amenities": ["wifi", "ac", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "The Oberoi Amarvilas", "type": "resort", "area": "Tajganj", "rating": 4.9, "reviews": 5200, "min": 25000, "max": 60000, "lat": 27.1730, "lon": 78.0440, "amenities": ["wifi", "ac", "pool", "gym", "restaurant", "room_service", "laundry", "minibar", "parking"], "check_in": "14:00", "check_out": "12:00"},
    ],
    "rishikesh": [
        {"name": "Zostel Rishikesh", "type": "hostel", "area": "Laxman Jhula", "rating": 4.5, "reviews": 2800, "min": 400, "max": 1200, "lat": 30.1240, "lon": 78.3207, "amenities": ["wifi", "kitchen", "laundry"], "check_in": "13:00", "check_out": "11:00"},
        {"name": "Hotel Ganga Kinare", "type": "hotel", "area": "Haridwar Road", "rating": 4.2, "reviews": 1500, "min": 3000, "max": 7000, "lat": 30.1020, "lon": 78.2960, "amenities": ["wifi", "ac", "restaurant", "room_service", "parking"], "check_in": "12:00", "check_out": "12:00"},
        {"name": "Parmarth Niketan Ashram", "type": "guesthouse", "area": "Swarg Ashram", "rating": 4.4, "reviews": 3200, "min": 800, "max": 2500, "lat": 30.1180, "lon": 78.3180, "amenities": ["wifi", "breakfast", "hot_water"], "check_in": "10:00", "check_out": "10:00"},
        {"name": "Homestay Tapovan", "type": "homestay", "area": "Tapovan", "rating": 4.3, "reviews": 350, "min": 1500, "max": 4000, "lat": 30.1150, "lon": 78.3100, "amenities": ["wifi", "breakfast", "kitchen", "parking", "hot_water"], "check_in": "14:00", "check_out": "11:00"},
    ],
}


def _make_stay_id(city: str, name: str) -> str:
    raw = f"{city}:{name}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _parse_amenities(raw: list[str]) -> list[Amenity]:
    mapping = {
        "wifi": Amenity.WIFI, "ac": Amenity.AC, "breakfast": Amenity.BREAKFAST,
        "parking": Amenity.PARKING, "pool": Amenity.POOL, "gym": Amenity.GYM,
        "restaurant": Amenity.RESTAURANT, "room_service": Amenity.ROOM_SERVICE,
        "laundry": Amenity.LAUNDRY, "power_backup": Amenity.POWER_BACKUP,
        "hot_water": Amenity.HOT_WATER, "tv": Amenity.TV, "minibar": Amenity.MINIBAR,
        "kitchen": Amenity.KITCHEN, "pet_friendly": Amenity.PET_FRIENDLY,
    }
    return [mapping[a] for a in raw if a in mapping]


def _generate_room_options(min_price: float, max_price: float, stay_type: str) -> list[RoomOption]:
    rooms = []
    if stay_type == "hostel":
        rooms.append(RoomOption(
            id="dorm", room_type=RoomType.DORM, max_occupancy=1,
            price_per_night=min_price, amenities=[Amenity.WIFI, Amenity.AC],
            cancellation_policy="Free cancellation up to 24h before check-in",
        ))
        rooms.append(RoomOption(
            id="private", room_type=RoomType.DOUBLE, max_occupancy=2,
            price_per_night=max_price, amenities=[Amenity.WIFI, Amenity.AC],
            cancellation_policy="Free cancellation up to 24h before check-in",
        ))
    else:
        mid = (min_price + max_price) / 2
        rooms.append(RoomOption(
            id="standard", room_type=RoomType.DOUBLE, max_occupancy=2,
            price_per_night=min_price, amenities=[Amenity.WIFI, Amenity.AC],
            cancellation_policy="Free cancellation up to 48h before check-in",
        ))
        rooms.append(RoomOption(
            id="deluxe", room_type=RoomType.DOUBLE, max_occupancy=2,
            price_per_night=mid, amenities=[Amenity.WIFI, Amenity.AC, Amenity.BREAKFAST],
            cancellation_policy="Free cancellation up to 48h before check-in",
        ))
        if stay_type in ("hotel", "resort"):
            rooms.append(RoomOption(
                id="suite", room_type=RoomType.SUITE, max_occupancy=3,
                price_per_night=max_price, amenities=[Amenity.WIFI, Amenity.AC, Amenity.BREAKFAST, Amenity.MINIBAR],
                cancellation_policy="Non-refundable",
            ))
    return rooms


def _check_arrival_mismatch(check_in_time: str, arrival_time: Optional[str], departure_time: Optional[str]) -> ArrivalMismatch:
    mismatch = ArrivalMismatch(has_mismatch=False)
    if arrival_time:
        h, m = map(int, arrival_time.split(":"))
        if h < 6:
            mismatch.has_mismatch = True
            mismatch.early_arrival = True
            mismatch.note = f"Early arrival at {arrival_time}. Check-in may not be available until {check_in_time}."
    if departure_time:
        h, m = map(int, departure_time.split(":"))
        if h > 20:
            mismatch.has_mismatch = True
            mismatch.late_departure = True
            mismatch.note = (mismatch.note or "") + f" Late departure at {departure_time}. Request late check-out."
    return mismatch


def _calculate_score(stay: Stay, budget: float, soft_margin: float, anchor_lat: Optional[float], anchor_lon: Optional[float],
                     ranking: str, distance_km: Optional[float]) -> float:
    score = 50.0

    # Price score (0-40): closer to budget sweet spot = higher
    avg_price = (stay.price_per_night_min + stay.price_per_night_max) / 2
    if avg_price <= budget:
        price_score = 30 + (avg_price / budget) * 10
    elif avg_price <= budget * (1 + soft_margin / 100):
        price_score = 20
    else:
        price_score = max(0, 20 - (avg_price - budget) / budget * 20)
    score = price_score

    # Rating score (0-25)
    if stay.rating:
        score += stay.rating * 5

    # Distance score (0-20)
    if distance_km is not None:
        if distance_km <= 2:
            score += 20
        elif distance_km <= 5:
            score += 15
        elif distance_km <= 10:
            score += 10
        elif distance_km <= 20:
            score += 5

    # Review count bonus (0-10)
    if stay.review_count > 1000:
        score += 10
    elif stay.review_count > 500:
        score += 7
    elif stay.review_count > 100:
        score += 5

    # Amenity bonus (0-5)
    if len(stay.amenities) > 6:
        score += 5
    elif len(stay.amenities) > 3:
        score += 3

    # Ranking preference adjustments
    if ranking == "cheapest":
        score = price_score * 2 + (stay.rating or 0) * 3
    elif ranking == "closest" and distance_km is not None:
        score = max(0, 50 - distance_km * 5) + (stay.rating or 0) * 5
    elif ranking == "highest_rated":
        score = (stay.rating or 0) * 20 + price_score

    return min(100, max(0, round(score, 1)))


async def search_stays(req: AccommodationSearchRequest) -> list[Stay]:
    """Search for stays using curated data. Returns list of Stay objects."""
    city_key = req.city.lower().strip()
    stays_data = CURATED_STAYS.get(city_key, [])

    # If city not in curated data, generate some generic options
    if not stays_data:
        stays_data = [
            {"name": f"Hotel {req.city} Central", "type": "hotel", "area": "City Center", "rating": 3.8, "reviews": 500, "min": 1500, "max": 4000, "lat": 20.0, "lon": 77.0, "amenities": ["wifi", "ac", "breakfast"], "check_in": "12:00", "check_out": "11:00"},
            {"name": f"Zostel {req.city}", "type": "hostel", "area": "Main Area", "rating": 4.2, "reviews": 300, "min": 400, "max": 1200, "lat": 20.0, "lon": 77.0, "amenities": ["wifi", "kitchen"], "check_in": "13:00", "check_out": "11:00"},
            {"name": f"Homestay {req.city}", "type": "homestay", "area": "Residential", "rating": 4.4, "reviews": 150, "min": 1200, "max": 3000, "lat": 20.0, "lon": 77.0, "amenities": ["wifi", "breakfast", "kitchen"], "check_in": "14:00", "check_out": "11:00"},
            {"name": f"Treebo {req.city}", "type": "hotel", "area": "Market Area", "rating": 3.9, "reviews": 400, "min": 1000, "max": 2500, "lat": 20.0, "lon": 77.0, "amenities": ["wifi", "ac", "power_backup"], "check_in": "12:00", "check_out": "11:00"},
        ]

    stays = []
    for data in stays_data:
        # Filter by stay type
        if req.stay_type and data["type"] != req.stay_type.value:
            continue

        # Filter by budget (with soft margin)
        max_allowed = req.budget_per_night * (1 + req.soft_margin_pct / 100)
        if data["min"] > max_allowed:
            continue

        amenities = _parse_amenities(data["amenities"])

        # Filter by required amenities
        if req.required_amenities:
            if not all(a in amenities for a in req.required_amenities):
                continue

        # Calculate distance from anchor
        dist_km = None
        if req.anchor_lat and req.anchor_lon and data.get("lat") and data.get("lon"):
            dist_km = _haversine_km(req.anchor_lat, req.anchor_lon, data["lat"], data["lon"])

        room_options = _generate_room_options(data["min"], data["max"], data["type"])

        stay = Stay(
            id=_make_stay_id(city_key, data["name"]),
            name=data["name"],
            stay_type=StayType(data["type"]),
            city=req.city,
            address=data.get("area", ""),
            latitude=data.get("lat"),
            longitude=data.get("lon"),
            rating=data.get("rating"),
            review_count=data.get("reviews", 0),
            price_per_night_min=data["min"],
            price_per_night_max=data["max"],
            currency="INR",
            room_options=room_options,
            amenities=amenities,
            check_in_time=data.get("check_in", "14:00"),
            check_out_time=data.get("check_out", "11:00"),
            booking_link=f"https://www.makemytrip.com/hotels/{data['name'].lower().replace(' ', '-')}",
            source="curated",
            distance_from_anchor_km=round(dist_km, 2) if dist_km else None,
        )
        stays.append(stay)

    return stays


def rank_stays(stays: list[Stay], req: AccommodationSearchRequest) -> list[dict]:
    """Rank stays and produce shortlist items."""
    soft_margin_amount = req.budget_per_night * req.soft_margin_pct / 100
    max_allowed = req.budget_per_night + soft_margin_amount

    scored = []
    for stay in stays:
        dist = stay.distance_from_anchor_km
        score = _calculate_score(stay, req.budget_per_night, req.soft_margin_pct,
                                 req.anchor_lat, req.anchor_lon, req.ranking_preference, dist)

        avg_price = (stay.price_per_night_min + stay.price_per_night_max) / 2
        # Choose best room option within budget
        best_room = None
        for room in stay.room_options:
            if room.price_per_night <= req.budget_per_night:
                if best_room is None or room.price_per_night > best_room.price_per_night:
                    best_room = room
        if best_room is None and stay.room_options:
            best_room = min(stay.room_options, key=lambda r: r.price_per_night)

        night_price = best_room.price_per_night if best_room else avg_price
        # Calculate nights
        try:
            ci = datetime.strptime(req.check_in, "%Y-%m-%d")
            co = datetime.strptime(req.check_out, "%Y-%m-%d")
            nights = max(1, (co - ci).days)
        except Exception:
            nights = 1

        total_cost = night_price * req.num_rooms * nights

        arrival_mismatch = _check_arrival_mismatch(stay.check_in_time, req.arrival_time, req.departure_time)

        scored.append({
            "stay": stay,
            "score": score,
            "total_cost": total_cost,
            "nights": nights,
            "night_price": night_price,
            "room": best_room,
            "arrival_mismatch": arrival_mismatch,
            "over_budget": night_price > req.budget_per_night,
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Assign labels
    if scored:
        scored[0]["label"] = "best overall"

        cheapest = min(scored, key=lambda x: x["night_price"])
        if cheapest != scored[0]:
            cheapest["label"] = cheapest.get("label", "cheapest good option")

        if req.anchor_lat and req.anchor_lon:
            closest = min(scored, key=lambda x: x["stay"].distance_from_anchor_km or 999)
            if closest != scored[0] and closest != cheapest:
                closest["label"] = closest.get("label", "closest")

        highest_rated = max(scored, key=lambda x: x["stay"].rating or 0)
        if highest_rated not in (scored[0], cheapest):
            highest_rated["label"] = highest_rated.get("label", "highest rated")

    return scored[:5]


async def search_and_rank(req: AccommodationSearchRequest) -> list[dict]:
    """Full accommodation search: search then rank."""
    stays = await search_stays(req)
    return rank_stays(stays, req)