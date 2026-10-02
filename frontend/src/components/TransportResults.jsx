import { useState } from 'react';

const MODE_ICONS = {
  flight: '✈️',
  train: '🚂',
  bus: '🚌',
  car: '🚗',
};

const WEATHER_RISK_COLORS = {
  none: { bg: '#dcfce7', color: '#166534', label: 'No Risk' },
  low: { bg: '#fef9c3', color: '#854d0e', label: 'Low Risk' },
  medium: { bg: '#fed7aa', color: '#9a3412', label: 'Medium Risk' },
  high: { bg: '#fecaca', color: '#991b1b', label: 'High Risk' },
};

const SOURCE_LABELS = {
  api: { label: 'Live API', className: 'badge-forecast' },
  web: { label: 'Web Search', className: 'badge-climate' },
  estimate: { label: 'Estimated — verify before booking', className: 'badge-unavailable' },
};

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

function OptionCard({ option, onSelect, isSelected }) {
  const [expanded, setExpanded] = useState(false);
  const wr = WEATHER_RISK_COLORS[option.weather_risk?.level || 'none'];
  const src = SOURCE_LABELS[option.source] || SOURCE_LABELS.estimate;

  return (
    <div className={`transport-card ${isSelected ? 'transport-card-selected' : ''} ${option.budget_status === 'over' ? 'transport-card-over' : ''}`}>
      <div className="transport-card-main" onClick={() => setExpanded(!expanded)}>
        <div className="transport-card-left">
          <span className="transport-mode">{MODE_ICONS[option.mode] || '🚆'} {option.mode}</span>
          <span className="transport-provider">{option.provider}</span>
        </div>

        <div className="transport-card-center">
          <div className="transport-time">
            {option.legs?.[0] && (
              <>
                <strong>{formatTime(option.legs[0].departure)}</strong>
                <span className="transport-arrow">→</span>
                <strong>{formatTime(option.legs[option.legs.length - 1]?.arrival)}</strong>
              </>
            )}
          </div>
          {option.legs?.[0]?.vehicle_number && (
            <div className="transport-vehicle-number">
              {option.mode === 'flight' ? '✈️' : option.mode === 'train' ? '🚂' : '🚌'} {option.legs[0].vehicle_number}
            </div>
          )}
          <div className="transport-meta">
            <span>{formatDuration(option.duration_total_minutes)}</span>
            {option.transfers > 0 && <span>· {option.transfers} transfer{option.transfers > 1 ? 's' : ''}</span>}
            {option.transfers === 0 && <span>· direct</span>}
          </div>
        </div>

        <div className="transport-card-right">
          <div className="transport-price">
            ₹{option.price_total.toFixed(2)}
            {option.baggage_fee_est > 0 && (
              <span className="baggage-fee">+₹{option.baggage_fee_est.toFixed(2)} bag</span>
            )}
          </div>

          {option.labels?.length > 0 && (
            <div className="transport-labels">
              {option.labels.map((l, i) => (
                <span key={i} className="transport-label">{l}</span>
              ))}
            </div>
          )}

          {option.budget_status === 'over' && (
            <span className="over-budget-badge">
              over budget by ₹{option.budget_over_by.toFixed(2)}
            </span>
          )}
        </div>

        <span className="expand-toggle">{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div className="transport-card-detail">
          <div className="detail-grid">
            <div className="detail-section">
              <h4>Route</h4>
              {option.legs?.map((leg, i) => (
                <div key={i} className="leg-item">
                  <span className="leg-route">{leg.from} → {leg.to}</span>
                  <span className="leg-times">{formatTime(leg.departure)} – {formatTime(leg.arrival)}</span>
                  {leg.vehicle_number && <span className="leg-vehicle">{leg.vehicle_number}</span>}
                </div>
              ))}
            </div>

            <div className="detail-section">
              <h4>Details</h4>
              <div className="detail-row">
                <span>Weather Risk:</span>
                <span className="risk-badge" style={{ background: wr.bg, color: wr.color }}>{wr.label}</span>
              </div>
              {option.weather_risk?.reason && (
                <div className="detail-row"><span>Reason:</span><span>{option.weather_risk.reason}</span></div>
              )}
              <div className="detail-row">
                <span>Data Source:</span>
                <span className={`badge ${src.className}`}>{src.label}</span>
              </div>
              <div className="detail-row">
                <span>Fetched:</span>
                <span>{option.fetched_at ? new Date(option.fetched_at).toLocaleString() : 'N/A'}</span>
              </div>
              {option.baggage_allowance && (
                <div className="detail-row">
                  <span>Baggage:</span>
                  <span>{option.baggage_allowance.included_bags} bag, {option.baggage_allowance.included_weight_kg}kg included</span>
                </div>
              )}
            </div>
          </div>

          <div className="detail-actions">
            <button className="btn-select" onClick={() => onSelect(option.id)}>
              {isSelected ? '✓ Selected' : 'Select This Option'}
            </button>
            {option.deep_link && (
              <a href={option.deep_link} target="_blank" rel="noopener noreferrer" className="btn-book">
                Book on provider's site ↗
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


export default function TransportResults({ result, onSelect, selectedId }) {
  if (!result) return null;

  const withinBudget = result.options.filter(o => o.budget_status === 'within');
  const overBudget = result.options.filter(o => o.budget_status === 'over');

  return (
    <div className="transport-results">
      <div className="result-header">
        <h2>Transport: {result.origin} → {result.destination}</h2>
        <span className="purpose-tag">{result.date}</span>
      </div>

      {result.interpreted_preferences && (
        <div className="interpreted-prefs">
          <strong>Understanding your preferences:</strong> {result.interpreted_preferences}
        </div>
      )}

      {result.warnings?.length > 0 && (
        <div className="warnings-box">
          {result.warnings.map((w, i) => (
            <div key={i} className="warning-item">⚠ {w}</div>
          ))}
        </div>
      )}

      <div className="budget-summary">
        <span>Budget: ₹{result.budget_share.toFixed(2)}</span>
        <span>{withinBudget.length} within budget</span>
        {overBudget.length > 0 && <span className="over-count">{overBudget.length} over budget</span>}
      </div>

      {result.options.length === 0 && (
        <div className="no-results">No transport options found. Try adjusting your search.</div>
      )}

      {withinBudget.length > 0 && (
        <div className="options-section">
          <h3 className="section-label">Within Budget</h3>
          {withinBudget.map((opt) => (
            <OptionCard
              key={opt.id}
              option={opt}
              onSelect={onSelect}
              isSelected={selectedId === opt.id}
            />
          ))}
        </div>
      )}

      {overBudget.length > 0 && (
        <div className="options-section">
          <h3 className="section-label over-section-label">Over Budget</h3>
          {overBudget.map((opt) => (
            <OptionCard
              key={opt.id}
              option={opt}
              onSelect={onSelect}
              isSelected={selectedId === opt.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}