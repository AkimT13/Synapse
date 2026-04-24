# Synapse Handoff Document

## Project Overview

**Synapse** is a domain-aware code review and drift detection system. It processes documents (code + knowledge bases) through a five-stage pipeline to detect when code implementation drifts from domain specifications.

### Core Problem
- Code can drift from domain specifications over time
- Developers need semantic understanding of "constraints" (domain rules) vs "implementations" (code)
- Manual review is time-consuming; automated drift detection is needed

### Key Insight
The system combines:
1. **Code parsing** (Python AST + tree-sitter)
2. **LLM normalization** (constraint extraction, behavior understanding)
3. **Vector embeddings** (semantic similarity search)
4. **Structured retrieval** (code-to-knowledge matching)

Example: If domain spec says "threshold must be 3-5 sigma", but code has `THRESHOLD_SIGMA = 2.0`, the system flags this as a conflict.

---

## Current Architecture

### Pipeline Stages
```
RawChunk → NormalizedChunk → EmbeddedChunk → VectorStore → CLI Output
```

1. **ingestion/** — Parse PDFs, Python files, Markdown, CSV into `RawChunk` objects
2. **normalization/** — Extract constraints/behaviors into `NormalizedChunk`
3. **embeddings/** — Vectorize normalized text
4. **storage/** — Persist to Actian VectorAI DB (localhost:50051)
5. **app/** — FastAPI server + CLI entrypoint

### Key Files
- `backend/synapse_cli/main.py` — CLI entry point (build_parser, handlers for each command)
- `backend/synapse_cli/*_command.py` — Individual command implementations (drift-check, ingest, review, doctor, query, etc.)
- `backend/synapse_cli/ui.py` — **NEW** Rich-based CLI UI (colorful output, spinners, tables, interactive menu)
- `backend/storage/vector_store.py` — VectorStore context manager (Actian client)
- `backend/config/` — Workspace config (YAML-based)
- `.synapse/config.yaml` — Per-repo workspace definition (code roots, knowledge roots, LLM model names)

---

## Latest Changes (This Session)

### What Was Done: "Sexy CLI UX with Rich"

#### Added Rich Library Integration
- **Dependency**: `"rich>=13.0"` in `pyproject.toml`
- **New Module**: `backend/synapse_cli/ui.py` (600+ lines)

#### UI Enhancements
1. **ASCII Banner** — Synapse logo in cyan on startup
2. **Colored Output** — Status icons (✓ aligned, ⚠ warning, ✖ conflict) with color codes
3. **Animated Spinners** — "Analyzing…", "Running checks…" during long ops (→ stderr)
4. **Rich Tables** — Formatted results for ingest, doctor, query
5. **Colored Panels** — Answer/Explanation boxes with border styles
6. **Interactive Menu** — No-args `synapse` shows numbered choices [1-5]

#### Handler Updates (main.py)
- All handlers now split: if `--json`, use old plain JSON; else wrap with Rich spinner + render function
- `_handle_ingest` / `_handle_reindex` — Progress messages formatted with `[dim][/dim]`
- `_handle_drift_check` / `_handle_review` — Spinner + Rich panels for checks
- `_handle_doctor` — Table with ✔/✖ icons, "Overall: ok/fail"
- `_handle_query` — Answer/Explanation panels + results table

#### Test Compatibility
- All 47 CLI tests pass
- Tests check for structural output (e.g., "Workspace:", "Status: aligned", "workspace_config")
- `--json` path unchanged (VS Code extension uses this)

---

## Project Structure

```
backend/
├── app/                    # FastAPI server
├── agents/                 # Agent-based pipelines
├── config/                 # Workspace config loading
├── embeddings/            # Vector generation
├── ingestion/             # Document parsing
├── jobs/                  # Ingest jobs (code, knowledge)
├── models/                # LLM providers (OpenAI, Ollama)
├── normalization/         # Constraint/behavior extraction
├── retrieval/             # Code-to-knowledge matching
├── storage/               # VectorStore (Actian)
├── synapse_cli/           # CLI commands + UI
│   ├── main.py           # CLI parser & handlers
│   ├── ui.py            # Rich UI components ✨ NEW
│   ├── *_command.py     # Command implementations
│   └── ...
├── tests/                 # Full test suite (47 tests passing)
├── workspace/            # Workspace config/initialization
├── pyproject.toml        # Dependencies + pytest config
└── .venv/                # Virtual environment

sample/                    # Demo workspace
├── code/                  # Python code examples
└── knowledge/            # Domain specs (constraints)
```

---

## How to Use (CLI)

### Commands

```bash
# Initialize workspace
synapse init --repo-root /path --name my-project --code backend --knowledge docs

# Ingest code/knowledge into vector DB
synapse ingest [all|code|knowledge] --repo-root /path

# Check code against domain specs
synapse drift-check --file backend/logic.py --repo-root /path
synapse drift-check "Behavior: threshold enforces 3-5 sigma" --repo-root /path

# Review file with drift + context
synapse review --file backend/logic.py --repo-root /path

# Query the knowledge base
synapse query free "where is the threshold enforced?" --repo-root /path
synapse query code "Behavior: threshold is enforced" --repo-root /path
synapse query knowledge "Constraint: threshold must be 3-5 sigma" --repo-root /path

# Diagnostics
synapse doctor  # Preflight checks (config, models, DB connectivity)
synapse status  # Workspace info

# Database ops
synapse reset         # Delete vector collection
synapse reindex       # Reset + re-ingest
synapse services up   # Start Actian VectorAI (docker-compose)

# Agent tools
synapse install-skill --agent claude  # Install review skill
synapse watch --repo-root /path       # Auto-ingest on file changes
```

### Interactive Menu
```bash
synapse
# → Banner
# → [1] Review a file
# → [2] Drift check a file
# → [3] Ingest workspace
# → [4] Run doctor
# → [5] Query free text
```

### JSON Mode (VS Code Extension)
```bash
synapse drift-check --file backend/logic.py --json | python3 -m json.tool
# Outputs pure JSON (unchanged by Rich UI)
```

---

## Development Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate

pip install -e .  # Install package + dependencies (includes rich>=13.0)
docker-compose up -d  # Start Actian VectorAI on localhost:50051

pytest                              # Run all tests
pytest tests/cli/ -q                # Run CLI tests only
pytest tests/cli/test_doctor.py -v  # Specific test file
```

---

## Known Limitations & Future Opportunities

### Current Limitations
1. **Single Model Provider** — OpenAI by default; Ollama support exists but not fully tested
2. **Actian DB Only** — Vector store hardcoded to Actian; could abstract to other providers (Pinecone, Weaviate, pgvector)
3. **Python Code Only** — Parser only handles Python; could add JavaScript, Go, Rust, etc.
4. **No Auth** — Workspace access not gated; multi-tenant support missing
5. **No Drift History** — Doesn't track drift over time; no trend analysis
6. **Limited UI Polish** — Rich tables are nice, but no:
   - Progress bars for large ingestions
   - Real-time streaming output
   - Export to HTML/PDF reports

### Potential Features

#### 1. **Enhanced UI/UX**
- [ ] Progress bars during ingest (show "156/500 files processed")
- [ ] Diff viewer for expected vs observed constraints
- [ ] Web dashboard (FastAPI + React) for drift visualization
- [ ] Export reports (HTML, PDF, JSON)
- [ ] Real-time log streaming (SSE) during long operations

#### 2. **Drift Analytics**
- [ ] Drift history tracking (timestamp, status, summary)
- [ ] Trend analysis ("drift increased 3x in last week")
- [ ] Severity scoring (critical vs warning)
- [ ] Drift remediation suggestions ("Update THRESHOLD_SIGMA to 4.0")

#### 3. **Code Support**
- [ ] JavaScript/TypeScript support (via @babel/parser)
- [ ] Go, Rust, Java language support
- [ ] Generic AST-based parsing framework

#### 4. **Multi-Tenancy**
- [ ] Per-tenant vector namespaces in Actian
- [ ] API authentication (JWT, API keys)
- [ ] RBAC (role-based access control)

#### 5. **Integration Points**
- [ ] GitHub Actions workflow (drift-check on PRs)
- [ ] Slack notifications ("Drift detected in signal_processing.py")
- [ ] VS Code extension enhancement (currently just using --json, could show inline annotations)
- [ ] IDE plugins (IntelliJ, Vim)

#### 6. **Advanced Retrieval**
- [ ] Hybrid search (BM25 + semantic)
- [ ] Multi-hop reasoning ("constraint A → constraint B → code C")
- [ ] Explanation confidence scoring
- [ ] Constraint versioning (different constraint sets per code version)

#### 7. **Quality & Testing**
- [ ] Structured test generation (pytest from constraints)
- [ ] Mutation testing (verify constraints catch drift)
- [ ] Benchmark suite (drift detection accuracy vs ground truth)

#### 8. **Operations**
- [ ] Helm chart / Kubernetes deployment
- [ ] Vector DB migration tools (Actian → other providers)
- [ ] Bulk data import from external sources
- [ ] Scheduled drift reports (daily/weekly email)

---

## Testing Strategy

### Current Test Coverage (47 tests)
- `tests/cli/` — CLI command tests (doctor, ingest, drift-check, query, review, reindex)
- `tests/embeddings/` — Vector store tests (requires Actian DB)
- `tests/agents/` — Agent pipeline tests (requires LLM)
- Tests use monkeypatching to mock expensive operations (VectorStore, LLM calls)

### To Add Tests For New Features
1. **Drift history** — Mock timestamp, verify sorting
2. **Web dashboard** — FastAPI TestClient for routes
3. **Export reports** — Mock file I/O, verify format
4. **Multi-tenancy** — Parameterize tests with tenant IDs
5. **GitHub Actions** — Integration test with real workflow

---

## Performance Notes

### Bottlenecks
1. **LLM calls** — Normalization uses GPT-4o-mini (~200ms/chunk). Parallel batching could help.
2. **Vector DB latency** — Actian queries ~100ms. Caching frequently-used constraints could help.
3. **Parser time** — tree-sitter parsing ~10ms/file. Large codebases (1000+ files) take minutes.

### Optimization Opportunities
1. Cache LLM normalization results (avoid re-normalizing unchanged files)
2. Batch vector inserts (currently one at a time)
3. Lazy-load code roots (don't parse everything on `ingest all`)
4. Incremental updates (ingest only changed files via git diff)

---

## Tips for Next Session

1. **Always activate venv first**: `source .venv/bin/activate`
2. **Rich Console bug**: `Console` instances must be created at call time (not module-level) for pytest `capsys` to capture output. Use `_out() -> Console(file=sys.stdout)` pattern.
3. **JSON mode is sacred**: The `--json` path is used by VS Code extension; never break it.
4. **Test before shipping**: Run `pytest tests/cli/ -q` before committing CLI changes.
5. **Workspace config**: Always exists at `.synapse/config.yaml`; doctor checks it first.
6. **VectorStore**: Context manager; always use `with VectorStore() as store:`.

---

## Quick Reference: Command Payloads

### drift-check
```json
{
  "workspace": "my-project",
  "target": "backend/signal_processing.py",
  "status": "conflict",
  "checks": [
    {
      "label": "detect_spikes",
      "status": "conflict",
      "summary": "Threshold sigma 2.0 is below required 3-5 range",
      "violations": ["threshold_range"],
      "confidence": "high",
      "findings": [{"issue_type": "threshold_range", "expected": "3-5", "observed": "2.0"}],
      "supporting_sources": [{"source_file": "constraints.md", "score": 0.87}]
    }
  ]
}
```

### ingest
```json
{
  "workspace": "my-project",
  "target": "all",
  "summaries": [
    {
      "kind": "code",
      "path": "backend",
      "result": {"files_processed": 42, "chunks_stored": 387, "errors": 0}
    }
  ]
}
```

### doctor
```json
{
  "workspace": {"name": "my-project", "repo_root": "/path", "config_path": "..."},
  "ok": true,
  "checks": [
    {"name": "workspace_config", "ok": true, "detail": "Loaded ..."},
    {"name": "actian_service", "ok": true, "detail": "Reachable on localhost:50051"}
  ],
  "suggested_fixes": []
}
```

---

## Contact / Questions

- **Code Review UI**: All Rich rendering in `backend/synapse_cli/ui.py`
- **CLI Commands**: Implementation in `backend/synapse_cli/*_command.py`
- **Tests**: `backend/tests/cli/test_*.py`
- **Architecture**: See `CLAUDE.md` in project root

Happy coding! 🚀
