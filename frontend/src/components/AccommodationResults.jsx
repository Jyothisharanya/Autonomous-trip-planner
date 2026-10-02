import { useState } from 'react';

const STAY_TYPE_ICONS = {
  hotel: '🏨',
  hostel: '🛏️',
  homestay: '🏠',
  resort: '🏖️',
  guesthouse: '🏡',
  apartment: '🏢',
};

const AMENITY_LABELS = {
  wifi: 'WiFi',
  ac: 'AC',
  breakfast: 'Breakfast',
  parking: 'Parking',
  pool: 'Pool',
  gym: 'Gym',
  restaurant: 'Restaurant',
  room_service: 'Room Service',
  laundry: 'Laundry',
  power_backup: 'Power Backup',
  hot_water: 'Hot Water',
  tv: 'TV',
  minibar: 'Minibar',
  kitchen: 'Kitchen',
  pet_friendly: 'Pet Friendly',
};

function StarRating({ rating, count }) {
  if (!rating) return null;
  const stars = Math.round(rating);
  return (
    <span className="star-rating">
      {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
      <span className="rating-num">{rating}</span>
      {count > 0 && <span className="review-count">({count.toLocaleString()} reviews)</span>}
    </span>
  );
}

function StayCard({ item, isExpanded, onToggle }) {
  const stay = item.stay;
  const icon = STAY_TYPE_ICONS[stay.stay_type] || '🏨';

  return (
    <div className={`stay-card ${item.label === 'best overall' ? 'stay-best' : ''}`}>
      <div className="stay-card-main" onClick={onToggle}>
        <div className="stay-card-left">
          <span className="stay-icon">{icon}</span>
          <div className="stay-type-badge">{stay.stay_type}</div>
        </div>

        <div className="stay-card-center">
          <h3 className="stay-name">{stay.name}</h3>
          <div className="stay-location">{stay.address}, {stay.city}</div>
          <StarRating rating={stay.rating} count={stay.review_count} />
          <div className="stay-amenities-preview">
            {stay.amenities.slice(0, 4).map(a => (
              <span key={a} className="amenity-tag">{AMENITY_LABELS[a] || a}</span>
            ))}
            {stay.amenities.length > 4 && <span className="amenity-more">+{stay.amenities.length - 4}</span>}
          </div>
        </div>

        <div className="stay-card-right">
          <div className="stay-price">
            <span className="price-amount">₹{item.stay.price_per_night_min.toLocaleString()}</span>
            <span className="price-unit">/night</span>
          </div>
          <div className="stay-total">Total: ₹{item.total_stay_cost.toLocaleString()}</div>
          {item.label && <span className="stay-label">{item.label}</span>}
          {item.stay.distance_from_anchor_km != null && (
            <span className="stay-distance">{item.stay.distance_from_anchor_km} km away</span>
          )}
          <span className="expand-toggle">{isExpanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {isExpanded && (
        <div className="stay-detail">
          <div className="stay-detail-grid">
            <div className="detail-section">
              <h4>Room Options</h4>
              {stay.room_options?.map((room, i) => (
                <div key={i} className="room-option-row">
                  <span className="room-type">{room.room_type}</span>
                  <span className="room-occupancy">Up to {room.max_occupancy} guests</span>
                  <span className="room-price">₹{room.price_per_night.toLocaleString()}/night</span>
                  <span className="room-cancel">{room.cancellation_policy}</span>
                </div>
              ))}
            </div>

            <div className="detail-section">
              <h4>Details</h4>
              <div className="detail-row">
                <span>Check-in:</span><span>{stay.check_in_time}</span>
              </div>
              <div className="detail-row">
                <span>Check-out:</span><span>{stay.check_out_time}</span>
              </div>
              <div className="detail-row">
                <span>Nights:</span><span>{item.nights}</span>
              </div>
              <div className="detail-row">
                <span>Rooms:</span><span>{item.stay.room_options?.length || 0} types available</span>
              </div>
              {item.arrival_mismatch?.has_mismatch && (
                <div className="arrival-mismatch">
                  ⚠ {item.arrival_mismatch.note}
                </div>
              )}
            </div>

            <div className="detail-section">
              <h4>All Amenities</h4>
              <div className="amenity-full-list">
                {stay.amenities.map(a => (
                  <span key={a} className="amenity-tag">{AMENITY_LABELS[a] || a}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="stay-actions">
            {stay.booking_link && (
              <a href={stay.booking_link} target="_blank" rel="noopener noreferrer" className="btn-book">
                Book on provider's site ↗
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


export default function AccommodationResults({ result }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!result) return null;

  return (
    <div className="accommodation-results">
      <div className="result-header">
        <h2>Stays in {result.city}</h2>
        <span className="purpose-tag">{result.check_in} → {result.check_out}</span>
      </div>

      <div className="acc-summary">
        <span>{result.nights} night{result.nights > 1 ? 's' : ''}</span>
        <span>Budget: ₹{result.budget_per_night.toLocaleString()}/night</span>
        <span>Soft margin: ₹{result.soft_margin.toLocaleString()}</span>
        <span>{result.total_found} stays found</span>
      </div>

      {result.warnings?.length > 0 && (
        <div className="warnings-box">
          {result.warnings.map((w, i) => (
            <div key={i} className="warning-item">⚠ {w}</div>
          ))}
        </div>
      )}

      {result.shortlist?.length === 0 && (
        <div className="no-results">No stays found. Try adjusting your budget or filters.</div>
      )}

      {result.shortlist?.map((item, idx) => (
        <StayCard
          key={item.stay.id}
          item={item}
          isExpanded={expandedId === item.stay.id}
          onToggle={() => setExpandedId(expandedId === item.stay.id ? null : item.stay.id)}
        />
      ))}
    </div>
  );
}