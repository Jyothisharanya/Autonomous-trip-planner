import { useState } from 'react';
import TripForm from './components/TripForm';
import PackingResult from './components/PackingResult';
import TransportSearch from './components/TransportSearch';
import TransportResults from './components/TransportResults';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function App() {
  const [tab, setTab] = useState('packing');
  const [packingResult, setPackingResult] = useState(null);
  const [transportResult, setTransportResult] = useState(null);
  const [selectedTransportId, setSelectedTransportId] = useState(null);
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
    // In a full implementation, this would call POST /api/transport/select
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Autonomous Trip Planner</h1>
        <p>AI-powered travel planning — packing, transport, and more</p>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${tab === 'packing' ? 'tab-active' : ''}`}
          onClick={() => setTab('packing')}
        >
          🧳 Packing List
        </button>
        <button
          className={`tab-btn ${tab === 'transport' ? 'tab-active' : ''}`}
          onClick={() => setTab('transport')}
        >
          ✈️ Transport
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
      </main>
    </div>
  );
}

export default App;