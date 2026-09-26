import { useState } from 'react';

const PURPOSES = [
  'Leisure',
  'Business',
  'Adventure/Trekking',
  'Pilgrimage/Religious',
  'Medical',
  'Event',
  'Study/Work relocation',
];

const AGE_BRACKETS = ['infant', 'child', 'teen', 'adult', 'senior'];

export default function TripForm({ onSubmit, loading }) {
  const [destination, setDestination] = useState('');
  const [purpose, setPurpose] = useState('Leisure');
  const [startDate, setStartDate] = useState('');
  const [tripLength, setTripLength] = useState(5);
  const [travelers, setTravelers] = useState([{ age: 30, age_bracket: null }]);

  const addTraveler = () => {
    setTravelers([...travelers, { age: null, age_bracket: 'adult' }]);
  };

  const removeTraveler = (idx) => {
    if (travelers.length <= 1) return;
    setTravelers(travelers.filter((_, i) => i !== idx));
  };

  const updateTraveler = (idx, field, value) => {
    const updated = [...travelers];
    updated[idx] = { ...updated[idx], [field]: value };
    setTravelers(updated);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      destination,
      purpose,
      start_date: startDate,
      trip_length: Number(tripLength),
      travelers: travelers.map((t) => ({
        age: t.age ? Number(t.age) : null,
        age_bracket: t.age ? null : t.age_bracket,
      })),
    });
  };

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="destination">Destination</label>
          <input
            id="destination"
            type="text"
            placeholder="e.g. Tokyo, Paris, Manali"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="purpose">Trip Purpose</label>
          <select id="purpose" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
            {PURPOSES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="startDate">Start Date</label>
          <input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="tripLength">Trip Length (days)</label>
          <input
            id="tripLength"
            type="number"
            min={1}
            max={365}
            value={tripLength}
            onChange={(e) => setTripLength(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="travelers-section">
        <div className="travelers-header">
          <h3>Travelers</h3>
          <button type="button" className="btn-add" onClick={addTraveler}>+ Add Traveler</button>
        </div>

        {travelers.map((t, idx) => (
          <div key={idx} className="traveler-row">
            <span className="traveler-label">Traveler {idx + 1}</span>
            <div className="traveler-fields">
              <div className="form-group compact">
                <label>Age</label>
                <input
                  type="number"
                  min={0}
                  max={120}
                  placeholder="Age"
                  value={t.age ?? ''}
                  onChange={(e) => {
                    const val = e.target.value ? Number(e.target.value) : null;
                    updateTraveler(idx, 'age', val);
                  }}
                />
              </div>
              <span className="or-divider">or</span>
              <div className="form-group compact">
                <label>Bracket</label>
                <select
                  value={t.age_bracket || ''}
                  onChange={(e) => updateTraveler(idx, 'age_bracket', e.target.value || null)}
                >
                  <option value="">Select...</option>
                  {AGE_BRACKETS.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>
            </div>
            {travelers.length > 1 && (
              <button type="button" className="btn-remove" onClick={() => removeTraveler(idx)}>✕</button>
            )}
          </div>
        ))}
      </div>

      <button type="submit" className="btn-submit" disabled={loading}>
        {loading ? 'Generating...' : 'Generate Packing List'}
      </button>
    </form>
  );
}