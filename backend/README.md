# Synapse Backend

FastAPI service on top of the ingestion, normalization, retrieval, and chat
layers. Persists vectors to Actian VectorAI DB, chat history to SQLite, and
uploaded source/knowledge files to a local `uploads/` directory.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e backend
pip install -r backend/requirements-actian.txt

cp backend/.env.example backend/.env
# Edit .env: set OPENAI_API_KEY, or switch providers to local Ollama.
# See the root README for the full provider / model table.

cd backend
docker-compose up -d       # Actian VectorAI DB on localhost:50051
python -m app.main         # API on localhost:8000
```

`pip install -e backend` installs the backend, tests, and CLI without the
bundled Actian wheel so editable installs work reliably on new machines.
To run the API or anything that touches the VectorAI client, install the
bundled wheel separately with `pip install -r backend/requirements-actian.txt`.

For the CLI, prefer the installed console entrypoint from the repo root:

```bash
synapse services up
synapse doctor
synapse ingest
synapse query free "How is the spike threshold set?"
```

`synapse services up` now manages a workspace-local compose file under
`.synapse/runtime/` rather than relying on the backend source tree as the
runtime entrypoint.

## Smoke test (no UI)

Exercises the full pipeline against `sample/code` and `sample/knowledge`,
running each retrieval direction and printing the output:

```bash
python -m app.smoke.smoke_test
```

The individual stages are also runnable — useful when debugging one layer:

```bash
python -m app.smoke.code_ingestion ../sample/code
python -m app.smoke.knowledge_ingestion ../sample/knowledge
python -m app.smoke.retrieval free "how is the spike threshold set?"
```

## Directory Map

```
backend/
  api/                  # FastAPI routers (workspace, corpora, ingest, retrieval, chat)
  app/
    main.py             # uvicorn entry point
    smoke/              # CLI smoke tests for each stage + end-to-end
  ingestion/            # source file → RawChunk (parse + chunk)
    walker.py           # shared filesystem discovery
    code/               # tree-sitter-based Python parser
    knowledge/          # docling-based document parser
  normalization/        # RawChunk → NormalizedChunk (LLM-assisted)
    code/
    knowledge/
  embeddings/           # NormalizedChunk → EmbeddedChunk
  storage/              # Actian VectorAI persistence + KNN search
  retrieval/            # search pipelines (free, code↔knowledge)
  jobs/                 # end-to-end orchestration (ingest_code, ingest_knowledge)
  models/               # provider-agnostic LLM + embedding client (openai, ollama)
  config/               # runtime settings
  tests/
```

## Pipeline

Each stage produces a schema that nests its source, forming a provenance chain:

```
RawChunk → NormalizedChunk → EmbeddedChunk → VectorStore
```

- **RawChunk** — first structured representation of a source file. Base class with shared fields (`raw_text`, `source_file`, `chunk_type`). Subclassed by `RawKnowledgeChunk` and `RawCodeChunk`, which carry resource-specific fields.
- **NormalizedChunk** — extracts intent (constraints, behaviors, procedures) and produces `embed_text`. Carries its source `RawChunk` inline. Uses a Pydantic discriminated union for deserialization; use `isinstance(chunk.source_chunk, RawCodeChunk)` to branch on the source type and access subclass-specific fields.
- **EmbeddedChunk** — the vector and its metadata. Carries its source `NormalizedChunk` inline. `embed_text` and `chunk_type` are derived via properties — no data duplication.

A single vector DB search returns a full `EmbeddedChunk` with the complete chain, all the way back to the original source text.

## Extending

**Adding a model provider.** Drop a module into `models/providers/` that
exposes `complete(model, system_prompt, user_prompt)` and
`embed(model, texts, dimension)`. Wire it into the `match` arms in
`models/__init__.py` under the chat and embedding routers. Chat and
embedding providers are independent, so a new one can back either or
both. Nothing else in the codebase imports providers directly — call
sites only see `models.complete()` / `models.embed()`.

**Adding a new resource type.** Code and knowledge are both instances
of the same shape: *parse → normalize → embed → store*. To plug in a
third type (tickets, transcripts, schema docs, anything):

1. Subclass `RawChunk` in `ingestion/schemas.py` with your
   resource-specific fields and a unique `chunk_type` literal.
2. Add `ingestion/<type>/` that parses source files into your new
   `RawChunk` subclass. Reuse `ingestion.walker.iter_files` for
   directory discovery.
3. Add `normalization/<type>/` that produces each chunk's
   `embed_text` — the natural-language description that lands in the
   shared vector space.
4. Add `jobs/ingest_<type>.py` mirroring `ingest_code.py`: walker →
   normalizer → `EmbeddingService` → `VectorStore`.
5. (Optional) Expose it via `api/ingestion.py` for HTTP upload, and
   add filter paths in `api/retrieval.py` / `api/chat.py` if the
   frontend needs to scope searches.

The `EmbeddedChunk` schema doesn't need to change — every resource
type lands in the same collection and participates in cross-modal
search, with `chunk_type` as the discriminating filter.
