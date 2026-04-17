# Synapse

A shared vector space for your code and your domain knowledge. Built for the
Actian VectorAI hackathon.

- `backend/` — FastAPI service on top of the ingestion, normalization,
  retrieval, and chat layers. Persists vectors to Actian VectorAI DB, chat
  history to SQLite, and uploaded source/knowledge files to a local
  `uploads/` directory so the UI can render them without round-tripping
  through the vector DB.
- `frontend/` — Next.js 14 app that wraps the backend API. Pixel-ports the
  mockups in `mockups/` into React + Tailwind with a typed API client and
  Server-Sent Events for live ingestion progress.
- `sample/` — small neuroscience corpora for smoke-testing the pipeline.

## Running the demo

### 1. Actian VectorAI DB

```bash
cd backend
docker-compose up -d         # starts the Actian DB on localhost:50051
```

### 2. Backend API (port 8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .

cp .env.example .env
# Edit .env and set OPENAI_API_KEY

python -m api.app            # or: uvicorn api.app:app --reload
```

### 3. Frontend (port 3000)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # picks up NEXT_PUBLIC_API_BASE
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and click **Launch the
demo** to land on the onboarding page. Upload the sample corpora
(`sample/code` and `sample/knowledge`), then jump into the three workspaces.

## Smoke test (no UI)

To exercise the whole pipeline from the command line:

```bash
cd backend
python -m app.smoke_test
```

This ingests the sample corpora, runs each retrieval direction, and prints
results. Useful for confirming the backend is healthy before wiring up the UI.
