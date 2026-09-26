# Autonomous Trip Planner — Packing Module

AI-powered packing list generator that uses real weather data and LLM tool-calling to create personalized, per-traveler packing lists.

## Tech Stack

- **Backend**: Python (FastAPI) + Google Gemini AI (tool calling) + Open-Meteo (weather/geocoding) + Firebase (persistence)
- **Frontend**: React + Vite

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))
- A Firebase project with Firestore enabled ([setup guide](https://firebase.google.com/docs/firestore/quickstart))

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and FIREBASE_CREDENTIALS path
```

### Frontend

```bash
cd frontend
npm install
```

## Running

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to the backend.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/pack` | Generate packing lists for a trip |
| `GET` | `/api/trips` | List saved trips |
| `GET` | `/api/trips/{id}` | Get a specific trip |
| `GET` | `/api/health` | Health check |

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `FIREBASE_CREDENTIALS` | Yes | Path to Firebase service account JSON |
| `FIREBASE_CREDENTIALS_JSON` | Alt | Firebase credentials as JSON string (for cloud deploys) |