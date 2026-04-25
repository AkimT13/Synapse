# Synapse

Developers don't always know the spec. Researchers don't always read the code. Synapse bridges both sides.

Synapse ingests your domain knowledge — research papers, protocol documents, safety specifications — alongside your source code, and continuously checks whether the two are aligned. When a developer writes a threshold that violates a constraint buried on page 47 of a spec, Synapse catches it. When a researcher updates a protocol, Synapse flags every function that may now be out of compliance.

Point it at a repository and a folder of docs and they become searchable together. Highlight a function and Synapse surfaces the spec behind it. Highlight a passage in a doc and it finds the code that implements it. Ask a question in plain English and it answers across both, with citations.

Works with OpenAI or a local [Ollama](https://ollama.com) install. Built for the Actian VectorAI hackathon.

## Quick install

```bash
git clone https://github.com/AkimT13/Synapse.git && cd Synapse && bash install.sh
```

This sets up the Python venv, installs the backend + CLI, and installs
frontend dependencies.

## Prerequisites

- **Python 3.10+** and **Node 18+**
- **Docker**, to run the Actian VectorAI database
- **Actian VectorAI Python client** (`.whl` file — see below)
- An **OpenAI API key** *or* a local **Ollama** install

## Setup

### 1. Actian VectorAI client

The Actian Python client is distributed as a `.whl` file and is not on
PyPI. Place the wheel in the `backend/` directory, then install it:

```bash
cp /path/to/actian_vectorai-0.1.0b2-py3-none-any.whl backend/
source backend/.venv/bin/activate
pip install backend/actian_vectorai-0.1.0b2-py3-none-any.whl
```

> The `.whl` is gitignored. Each developer needs to obtain and install
> it locally.

### 2. Start the vector database

```bash
synapse services up
```

This starts the Actian VectorAI DB on `localhost:50051` via Docker.

### 3. Initialize a workspace

```bash
synapse init
```

Follow the prompts to set your workspace name, code paths, knowledge
paths, and model provider. This creates `.synapse/config.yaml`.

### 4. Configure your models

Set your API key in `.synapse/.env`:

```bash
echo "OPENAI_API_KEY=sk-..." > .synapse/.env
```

Or use Ollama (no API key needed):

```bash
ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

When running `synapse init`, select Ollama as your provider.

### 5. Ingest your data

```bash
synapse ingest
```

This parses your code and knowledge, normalizes, embeds, and stores
everything in the vector database. Each workspace gets its own
isolated collection.

### 6. Verify

```bash
synapse doctor
```

All checks should pass. You're ready to go.

## Usage

### CLI

```bash
synapse status                # workspace overview
synapse query free "How does the threshold work?"
synapse drift-check --file ./code/my_module.py
synapse review --file ./code/my_module.py
synapse reset                 # wipe this workspace's vectors
synapse reindex               # reset + re-ingest
```

### GUI (port 3000 + 8000)

Start the backend API and frontend dev server:

```bash
# Terminal 1 — API
source backend/.venv/bin/activate
python -m api.app

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### VS Code extension

```bash
synapse vscode
```

Builds the extension and opens VS Code with it loaded. The extension
provides drift checks, review, and query directly in the editor.
Requires the venv to be active so `synapse` is on PATH.

### Agent skills (Claude Code / Codex)

```bash
synapse install-skill
```

Installs a `synapse-review` skill that AI coding agents use
automatically when editing domain-relevant code. The agent runs
`synapse review` before and after edits to check for drift.

## Picking models and providers

Synapse supports **OpenAI** (hosted) and **Ollama** (local) for both
chat and embeddings. They're configured independently — you can mix
providers.

Configured via `.synapse/config.yaml` (created by `synapse init`) or
environment variables in `.synapse/.env`:

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
after ingesting, run `synapse reindex` so the collection is recreated
at the new dimension.

## Workspace isolation

Each workspace gets its own vector DB collection derived from its name.
A project named `"eeg-analysis"` stores vectors in `eeg_analysis_chunks`,
while `"my-project"` uses `my_project_chunks`. Running `synapse reset`
in one project does not affect another.

## Sample data

The `sample/` directory contains a starter corpus (EEG neuroscience)
with code and knowledge files you can use to try things out. There's
also an `aerospace-sample/` with flight dynamics and GNC content.

## Architecture

Five-stage pipeline with full provenance tracking:

1. **Ingestion** — Parse raw documents (PDF, DOCX, MD) and code (Python via tree-sitter)
2. **Normalization** — Extract semantic structure (constraints, behaviors, procedures) with optional LLM rewrite
3. **Embedding** — Vectorize normalized text (L2-normalized)
4. **Storage** — Persist to Actian VectorAI DB with metadata for filtered retrieval
5. **Retrieval** — Direction-aware KNN search + LLM explanation

See `pipeline.mermaid` for a detailed sequence diagram.
