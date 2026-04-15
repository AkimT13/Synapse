# Synapse Backend

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python app/main.py
```

Requires Docker for the vector DB:
```bash
docker-compose up -d  # starts Actian VectorAI DB on localhost:50051
```

## Directory Map

```
backend/
  app/                  # entrypoint
  ingestion/            # initial ingestion & parsing
    code/
    knowledge/
  normalization/        # normalizing resources into a unified schema
    code/
    knowledge/
  embeddings/           # vectorize unified schema into EmbeddedChunks
  storage/              # persist and search via Actian VectorAI DB
  tests/
```

## Pipeline Abstractions

Each stage produces a schema that nests its source, forming a provenance chain:

```
RawChunk → NormalizedChunk → EmbeddedChunk → VectorStore
```

- **RawChunk** — first structured representation of a source file. Base class with shared fields (`raw_text`, `source_file`, `chunk_type`). Subclassed by `RawKnowledgeChunk` and `RawCodeChunk`, which will carry resource-specific fields as the ingestion pipeline develops.
- **NormalizedChunk** — extracts intent (constraints, behaviors, procedures) and produces `embed_text`. Carries its source `RawChunk` inline. Uses a Pydantic discriminated union for deserialization; use `isinstance(chunk.source_chunk, RawCodeChunk)` to branch on the source type and access subclass-specific fields.
- **EmbeddedChunk** — the vector and its metadata. Carries its source `NormalizedChunk` inline. `embed_text` and `chunk_type` are derived via properties — no data duplication.

A single vector DB search returns a full `EmbeddedChunk` with the complete chain, all the way back to the original source text.
