import { useState } from 'react';

const STAY_TYPES = [
  { value: '', label: 'Any' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'hostel', label: 'Hostel' },
  { value: 'homestay', label: 'Homestay' },
  { value: 'resort', label: 'Resort' },
  { value: 'guesthouse', label: 'Guesthouse' },
  { value: 'apartment', label: 'Apartment' },
];

const RANKING_OPTIONS = [
  { value: 'best_overall', label: 'Best Overall' },
  { value: 'cheapest', label: 'Cheapest' },
  { value: 'closest', label: 'Closest' },
  { value: 'highest_rated', label: 'Highest Rated' },
];

const AMENITY_OPTIONS = [
  'wifi', 'ac', 'breakfast', 'parking', 'pool', 'gym',
  'restaurant', 'room_service', 'laundry', 'hot_water', 'kitchen',
];

export default function AccommodationSearch({ onSearch, loading }) {
  const [city, setCity] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [numRooms, setNumRooms] = useState(1);
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [budgetPerNight, setBudgetPerNight] = useState(3000);
  const [softMargin, setSoftMargin] = useState(10);
  const [stayType, setStayType] = useState('');
  const [requiredAmenities, setRequiredAmenities] = useState([]);
  const [rankingPreference, setRankingPreference] = useState('best_overall');

  const toggleAmenity = (amenity) => {
    setRequiredAmenities(prev =>
      prev.includes(amenity) ? prev.filter(a => a !== amenity) : [...prev, amenity]
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch({
      city,
      check_in: checkIn,
      check_out: checkOut,
      num_rooms: Number(numRooms),
      adults: Number(adults),
      children: Number(children),
      budget_per_night: Number(budgetPerNight),
      soft_margin_pct: Number(softMargin),
      stay_type: stayType || null,
      required_amenities: requiredAmenities,
      ranking_preference: rankingPreference,
    });
  };

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h3 className="section-title">Find Accommodation</h3>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="accCity">City</label>
          <input
            id="accCity"
            type="text"
            placeholder="e.g. Delhi, Mumbai, Goa"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="stayType">Stay Type</label>
          <select id="stayType" value={stayType} onChange={(e) => setStayType(e.target.value)}>
            {STAY_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="accCheckIn">Check-in</label>
          <input
            id="accCheckIn"
            type="date"
            value={checkIn}
            onChange={(e) => setCheckIn(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="accCheckOut">Check-out</label>
          <input
            id="accCheckOut"
            type="date"
            value={checkOut}
            onChange={(e) => setCheckOut(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="form-row form-row-3">
        <div className="form-group">
          <label htmlFor="accRooms">Rooms</label>
          <input
            id="accRooms"
            type="number"
            min={1}
            max={10}
            value={numRooms}
            onChange={(e) => setNumRooms(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="accAdults">Adults</label>
          <input
            id="accAdults"
            type="number"
            min={1}
            max={20}
            value={adults}
            onChange={(e) => setAdults(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="accChildren">Children</label>
          <input
            id="accChildren"
            type="number"
            min={0}
            max={10}
            value={children}
            onChange={(e) => setChildren(e.target.value)}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="accBudget">Budget per night (₹)</label>
          <input
            id="accBudget"
            type="number"
            min={100}
            step={100}
            value={budgetPerNight}
            onChange={(e) => setBudgetPerNight(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="accSoftMargin">Soft margin (%)</label>
          <input
            id="accSoftMargin"
            type="number"
            min={0}
            max={50}
            value={softMargin}
            onChange={(e) => setSoftMargin(e.target.value)}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="accRanking">Rank By</label>
          <select id="accRanking" value={rankingPreference} onChange={(e) => setRankingPreference(e.target.value)}>
            {RANKING_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-group" style={{ marginBottom: 16 }}>
        <label>Required Amenities</label>
        <div className="amenity-chips">
          {AMENITY_OPTIONS.map(a => (
            <button
              key={a}
              type="button"
              className={`amenity-chip ${requiredAmenities.includes(a) ? 'amenity-selected' : ''}`}
              onClick={() => toggleAmenity(a)}
            >
              {a.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <button type="submit" className="btn-submit" disabled={loading}>
        {loading ? 'Searching...' : 'Search Accommodation'}
      </button>
    </form>
  );
}