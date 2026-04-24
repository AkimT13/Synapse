# Synapse

Your code and your documentation, searchable as one thing.

Highlight a function and Synapse surfaces the spec behind it. Highlight
a passage in a doc and it finds the code that implements it. Ask a
question in plain English and it answers across both, with citations.

Everything runs locally — point it at a repository and a folder of
docs and they become searchable together. Works with OpenAI or a
local [Ollama](https://ollama.com) install.

Built for the Actian VectorAI hackathon.

## What you'll need

- **Docker**, to run the Actian VectorAI database
- **Python 3.10+** and **Node 18+**
- An **OpenAI API key** *or* a local **Ollama** install
- A few minutes and something to ingest — a small repo and a handful
  of PDFs/Markdown files is plenty. The `sample/` directory has a
  starter corpus if you just want to look around.

## Running the demo

### 1. Actian VectorAI DB

```bash
cd backend
docker-compose up -d         # starts the Actian DB on localhost:50051
```

Or, once the CLI is installed:

```bash
synapse services up
```

Synapse manages its local runtime scaffold under `.synapse/runtime/`. That
directory is local workspace state, not project config.

### 2. Backend API (port 8000)

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e backend
pip install -r backend/requirements-actian.txt

cp backend/.env.example backend/.env
# Edit .env and set OPENAI_API_KEY 
# (see "Picking models and providers" below if you want to swap
# OpenAI for local Ollama, or change models).

python -m api.app         
```

`pip install -e backend` now installs the general backend and CLI dependencies.
The Actian Python client is installed separately from the bundled wheel via
`backend/requirements-actian.txt` so editable installs remain portable across
machines.

### 3. Frontend (port 3000)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # picks up NEXT_PUBLIC_API_BASE
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and click **Launch the
demo** to land on the onboarding page. Upload the sample corpora
(`sample/code` and `sample/knowledge`) or your own code & documents.

## Picking models and providers

Synapse supports two providers for both chat and embeddings: **OpenAI**
(hosted) and **Ollama** (local, `http://localhost:11434`). Chat and
embeddings are configured independently — you can mix providers, e.g.
OpenAI chat with Ollama embeddings.

Configured via environment variables in `backend/.env` (see
[`backend/.env.example`](backend/.env.example) for the full list with
comments):

| Variable              | Default                      | Options                  |
| --------------------- | ---------------------------- | ------------------------ |
| `LLM_PROVIDER`        | `openai`                     | `openai` \| `ollama`     |
| `LLM_MODEL`           | `gpt-4o-mini`                | any model the provider exposes |
| `EMBEDDING_PROVIDER`  | `openai`                     | `openai` \| `ollama`     |
| `EMBEDDING_MODEL`     | `text-embedding-3-large`     | any model the provider exposes |
| `EMBEDDING_DIMENSION` | `3072`                       | must match the embedding model's native size |
| `OPENAI_API_KEY`      | —                            | required if either provider is `openai` |
| `OLLAMA_BASE_URL`     | `http://localhost:11434`     | override if Ollama runs on a different host/port |

`EMBEDDING_DIMENSION` must match the embedding model — e.g. `3072` for
`text-embedding-3-large`, `1536` for `text-embedding-3-small`, `768`
for Ollama's `nomic-embed-text`. If you change the embedding model
after ingesting, reset the workspace (top-right of the onboarding
page) so the vector collection is recreated at the new dimension.

Ollama doesn't need an API key — just run `ollama serve` and pull the
models you want (e.g. `ollama pull llama3.1:8b`,
`ollama pull nomic-embed-text`).

## CLI

The preferred CLI entrypoint is `synapse`.

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e backend
pip install -r backend/requirements-actian.txt
```

Then use:

```bash
synapse doctor
synapse ingest
synapse query free "How is the spike detection threshold set?"
synapse drift-check --file ./sample/code/bad_spike_pipeline.py
```

## Multi-agent Development

Synapse's default parallel delivery model is a hub-and-spoke multi-agent loop.

- `MULTI_AGENT_WORKFLOW.md` defines the operating rules
- `MULTI_AGENT_STATUS.md` is the live cycle contract and status log
- `AGENT_INTEGRATION.md` covers the CLI commands agents should use

Before starting a long-running coordinated agent session, create a sentinel
commit so the loop has a clear rollback anchor.
