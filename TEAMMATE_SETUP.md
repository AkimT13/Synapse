# Synapse Teammate Setup

This is the quickest way to run Synapse in its current state.

## Current Scope

What works well right now:

- local workspace config via `.synapse/config.yaml`
- CLI commands for `init`, `status`, `ingest`, `query`, and `drift-check`
- ingestion of the sample code and sample knowledge corpora
- retrieval across code and knowledge
- first-pass drift detection against indexed domain constraints

What is still rough:

- knowledge ingestion emits a Hugging Face warning during doc chunking
- drift explanations are useful but not yet perfectly reliable on every numeric comparison
- the CLI is the main supported workflow right now

## 1. Install Backend Dependencies

From the repo root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-actian.txt
```

## 2. Start Supporting Services

From the repo root, start Actian Vector:

```bash
docker-compose up -d
```

If using local Ollama, make sure it is running and the required models exist:

```bash
ollama serve
ollama pull gemma4:e2b
ollama pull nomic-embed-text
```

## 3. Create Or Confirm The Workspace

This repo already includes a workspace config at `.synapse/config.yaml`.

If needed, create one from `backend/` (you dont need this since one exists):

```bash
python -m synapse_cli.main init \
  --repo-root .. \
  --name synapse \
  --code sample/code \
  --knowledge sample/knowledge \
  --domain domain-aware-development \
  --chat-provider ollama \
  --chat-model gemma4:e2b \
  --embedding-provider ollama \
  --embedding-model nomic-embed-text
```

Inspect status:

```bash
python -m synapse_cli.main status
```

## 4. Ingest The Sample Corpus

From `backend/`:

```bash
python -m synapse_cli.main ingest
```

If you only want code or only want knowledge:

```bash
python -m synapse_cli.main ingest code
python -m synapse_cli.main ingest knowledge
```

## 5. Run Queries

Free-text query:

```bash
python -m synapse_cli.main query free "How is the spike detection threshold set?"
```

Another useful free-text query:

```bash
python -m synapse_cli.main query free "How does the code detect muscle contamination?"
```

Code-to-knowledge query:

```bash
python -m synapse_cli.main query code "Behavior: detects spikes using a negative threshold of 4 standard deviations below baseline."
```

Knowledge-to-code query:

```bash
python -m synapse_cli.main query knowledge "Any spike detection algorithm must suppress detections within at least 1 millisecond of each other."
```

## 6. Run Drift Detection

There is an intentionally wrong sample file here:

- `sample/code/bad_spike_pipeline.py`

It violates the sample knowledge base on purpose.

Run drift detection from `backend/`:

```bash
python -m synapse_cli.main drift-check --file ../sample/code/bad_spike_pipeline.py
```

Machine-readable output:

```bash
python -m synapse_cli.main drift-check --file ../sample/code/bad_spike_pipeline.py --json
```

## 7. Useful Notes

- Current sample workspace points at `sample/code` and `sample/knowledge`, not the Synapse app source itself.
- If tests are added under a new `backend/tests/...` package directory, include an empty `__init__.py`.
- The Hugging Face warning during knowledge ingestion is currently expected and comes from docling chunking, not from Ollama embeddings.

## 8. Minimal Demo Flow

From `backend/`:

```bash
python -m synapse_cli.main status
python -m synapse_cli.main ingest
python -m synapse_cli.main query free "How is the spike detection threshold set?"
python -m synapse_cli.main drift-check --file ../sample/code/bad_spike_pipeline.py
```
