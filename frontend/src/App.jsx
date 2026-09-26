import { useState } from 'react';
import TripForm from './components/TripForm';
import PackingResult from './components/PackingResult';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (tripData) => {
    setLoading(true);
    setError(null);
    setResult(null);

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
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🧳 Packing Planner</h1>
        <p>AI-powered packing lists based on your destination, weather, and trip purpose</p>
      </header>

      <main>
        <TripForm onSubmit={handleSubmit} loading={loading} />

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

        {result && <PackingResult result={result} />}
      </main>
    </div>
  );
}

export default App;