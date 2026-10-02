import { useState } from 'react';

const RANKING_OPTIONS = [
  { value: 'cheapest', label: 'Cheapest' },
  { value: 'fastest', label: 'Fastest' },
  { value: 'fewest_transfers', label: 'Fewest Transfers' },
  { value: 'comfort', label: 'Most Comfortable' },
  { value: 'custom', label: 'Custom Preference' },
];

export default function TransportSearch({ onSearch, loading, packingResult }) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [dateWindowN, setDateWindowN] = useState(0);
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [budgetShare, setBudgetShare] = useState(15000);
  const [rankingPreference, setRankingPreference] = useState('cheapest');
  const [customPreference, setCustomPreference] = useState('');
  const [returnDate, setReturnDate] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch({
      origin,
      destination,
      date,
      date_window_n: Number(dateWindowN),
      travelers_adults: Number(adults),
      travelers_children: Number(children),
      budget_share: Number(budgetShare),
      ranking_preference: rankingPreference,
      custom_preference: rankingPreference === 'custom' ? customPreference : null,
      return_date: returnDate || null,
      packing_bag_count: packingResult?.packing_lists?.[0]?.categories
        ?.find(c => c.name === 'Other')?.items?.length || null,
      packing_weight_kg: null,
    });
  };

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h3 className="section-title">Intercity Transport</h3>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="origin">Origin</label>
          <input
            id="origin"
            type="text"
            placeholder="e.g. New York, London"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="dest">Destination</label>
          <input
            id="dest"
            type="text"
            placeholder="e.g. Tokyo, Paris"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="travelDate">Travel Date</label>
          <input
            id="travelDate"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="returnDate">Return Date (optional)</label>
          <input
            id="returnDate"
            type="date"
            value={returnDate}
            onChange={(e) => setReturnDate(e.target.value)}
          />
        </div>
      </div>

      <div className="form-row form-row-3">
        <div className="form-group">
          <label htmlFor="dateWindow">Date Flexibility (±days)</label>
          <select
            id="dateWindow"
            value={dateWindowN}
            onChange={(e) => setDateWindowN(e.target.value)}
          >
            <option value={0}>Exact dates</option>
            <option value={1}>±1 day</option>
            <option value={2}>±2 days</option>
            <option value={3}>±3 days</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="adults">Adults</label>
          <input
            id="adults"
            type="number"
            min={1}
            max={20}
            value={adults}
            onChange={(e) => setAdults(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="children">Children</label>
          <input
            id="children"
            type="number"
            min={0}
            max={20}
            value={children}
            onChange={(e) => setChildren(e.target.value)}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="budget">Transport Budget (₹)</label>
          <input
            id="budget"
            type="number"
            min={1}
            step={10}
            value={budgetShare}
            onChange={(e) => setBudgetShare(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="ranking">Rank By</label>
          <select
            id="ranking"
            value={rankingPreference}
            onChange={(e) => setRankingPreference(e.target.value)}
          >
            {RANKING_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {rankingPreference === 'custom' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label htmlFor="customPref">Your Preference</label>
          <input
            id="customPref"
            type="text"
            placeholder="e.g. No overnight trips, avoid self-transfers, prefer morning departures"
            value={customPreference}
            onChange={(e) => setCustomPreference(e.target.value)}
          />
        </div>
      )}

      <button type="submit" className="btn-submit" disabled={loading}>
        {loading ? 'Searching...' : 'Search Transport Options'}
      </button>
    </form>
  );
}