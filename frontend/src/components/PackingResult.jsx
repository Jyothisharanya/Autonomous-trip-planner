const CATEGORY_ICONS = {
  'Clothing': '👕',
  'Toiletries': '🧴',
  'Documents': '📄',
  'Electronics': '🔌',
  'Health & Medical': '💊',
  'Other': '📦',
};

const WEATHER_BADGE = {
  forecast: { label: 'Live Forecast', className: 'badge-forecast' },
  climate_normal: { label: 'Historical Average', className: 'badge-climate' },
  unavailable: { label: 'Weather Unavailable', className: 'badge-unavailable' },
};

export default function PackingResult({ result }) {
  if (!result) return null;

  return (
    <div className="packing-result">
      <div className="result-header">
        <h2>Packing List for {result.destination}</h2>
        <span className="purpose-tag">{result.purpose}</span>
      </div>

      {result.weather_summary && (
        <div className="weather-summary">
          <strong>Weather:</strong> {result.weather_summary}
        </div>
      )}

      {result.packing_lists?.length === 0 && (
        <div className="no-results">No packing lists were generated. Please try again.</div>
      )}

      {result.packing_lists?.map((pl, idx) => (
        <div key={idx} className="traveler-card">
          <div className="traveler-card-header">
            <h3>Traveler {pl.traveler_index + 1} — {pl.age_label}</h3>
            {(() => {
              const badge = WEATHER_BADGE[pl.weather_basis] || WEATHER_BADGE.unavailable;
              return <span className={`badge ${badge.className}`}>{badge.label}</span>;
            })()}
          </div>

          <div className="categories-grid">
            {pl.categories?.map((cat, ci) => (
              <div key={ci} className="category-card">
                <h4>{CATEGORY_ICONS[cat.name] || '📋'} {cat.name}</h4>
                <ul>
                  {cat.items?.map((item, ii) => (
                    <li key={ii}>
                      <label>
                        <input type="checkbox" />
                        <span>{item}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}