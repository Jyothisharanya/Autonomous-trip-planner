import { useState } from 'react';
import TripForm from './components/TripForm';
import PackingResult from './components/PackingResult';
import TransportSearch from './components/TransportSearch';
import TransportResults from './components/TransportResults';
import AccommodationSearch from './components/AccommodationSearch';
import AccommodationResults from './components/AccommodationResults';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function App() {
  const [tab, setTab] = useState('packing');
  const [packingResult, setPackingResult] = useState(null);
  const [transportResult, setTransportResult] = useState(null);
  const [selectedTransportId, setSelectedTransportId] = useState(null);
  const [accommodationResult, setAccommodationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePackSubmit = async (tripData) => {
    setLoading(true);
    setError(null);
    setPackingResult(null);

    try {
      const resp = await fetch(`${API_BASE}/api/pack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tripData),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'Request failed');
      }

      const data = await resp.json();
      setPackingResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTransportSearch = async (searchData) => {
    setLoading(true);
    setError(null);
    setTransportResult(null);
    setSelectedTransportId(null);

    try {
      const resp = await fetch(`${API_BASE}/api/transport/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchData),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'Request failed');
      }

      const data = await resp.json();
      setTransportResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTransport = async (optionId) => {
    setSelectedTransportId(optionId);
  };

  const handleAccommodationSearch = async (searchData) => {
    setLoading(true);
    setError(null);
    setAccommodationResult(null);

    try {
      const resp = await fetch(`${API_BASE}/api/accommodation/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchData),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'Request failed');
      }

      const data = await resp.json();
      setAccommodationResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Autonomous Trip Planner</h1>
        <p>AI-powered travel planning — packing, transport, and stays</p>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${tab === 'packing' ? 'tab-active' : ''}`}
          onClick={() => setTab('packing')}
        >
          🧳 Packing
        </button>
        <button
          className={`tab-btn ${tab === 'transport' ? 'tab-active' : ''}`}
          onClick={() => setTab('transport')}
        >
          ✈️ Transport
        </button>
        <button
          className={`tab-btn ${tab === 'accommodation' ? 'tab-active' : ''}`}
          onClick={() => setTab('accommodation')}
        >
          🏨 Stay
        </button>
      </nav>

      <main>
        {tab === 'packing' && (
          <>
            <TripForm onSubmit={handlePackSubmit} loading={loading} />

            {loading && (
              <div className="loading">
                <div className="spinner" />
                <p>Generating your personalized packing list...</p>
                <p className="loading-sub">Looking up weather & reasoning through your trip details</p>
              </div>
            )}

            {error && (
              <div className="error-box">
                <strong>Error:</strong> {error}
              </div>
            )}

            {packingResult && <PackingResult result={packingResult} />}
          </>
        )}

        {tab === 'transport' && (
          <>
            <TransportSearch
              onSearch={handleTransportSearch}
              loading={loading}
              packingResult={packingResult}
            />

            {loading && (
              <div className="loading">
                <div className="spinner" />
                <p>Searching transport options...</p>
                <p className="loading-sub">Checking flights, trains, and buses across providers</p>
              </div>
            )}

            {error && (
              <div className="error-box">
                <strong>Error:</strong> {error}
              </div>
            )}

            {transportResult && (
              <TransportResults
                result={transportResult}
                onSelect={handleSelectTransport}
                selectedId={selectedTransportId}
              />
            )}
          </>
        )}

        {tab === 'accommodation' && (
          <>
            <AccommodationSearch
              onSearch={handleAccommodationSearch}
              loading={loading}
            />

            {loading && (
              <div className="loading">
                <div className="spinner" />
                <p>Searching accommodation...</p>
                <p className="loading-sub">Finding the best stays within your budget</p>
              </div>
            )}

            {error && (
              <div className="error-box">
                <strong>Error:</strong> {error}
              </div>
            )}

            {accommodationResult && (
              <AccommodationResults result={accommodationResult} />
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;