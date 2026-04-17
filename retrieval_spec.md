# Retrieval Specification

**Version:** 0.1
**Status:** Draft

---

## Overview

The retrieval layer is the first point where domain knowledge and code interact. It takes a query — either a raw text question, a code chunk, or a domain knowledge chunk — embeds it, searches Actian VectorAI DB for the K nearest chunks of the appropriate type, and returns ranked results with similarity scores. An LLM explanation layer then interprets the retrieved pairs and surfaces conflicts, gaps, or explanations in plain language.

This spec covers: the Actian storage schema, index configuration, query preprocessing, retrieval patterns, scoring and thresholds, the LLM explanation layer, and the CLI commands that expose retrieval to the user.

---

## Actian VectorAI DB Storage Schema

### Collection: `synapse_chunks`

All chunks — both knowledge and code — live in a single collection. This is intentional: a single HNSW index over a shared embedding space is what enables cross-modal retrieval. Type filtering narrows results at query time.

### Document Schema

Each document inserted into Actian has the following fields:

```
{
    "id":                str,       # unique chunk identifier (content hash)
    "type":              str,       # "knowledge" | "code"
    "vector":            [float],   # 768-dim L2-normalized embedding
    "embed_text":        str,       # the text that was embedded
    "raw_content":       str,       # original content before summarization
    "source_file":       str,       # path to source document or code file
    "domain":            str,       # e.g. "spectroscopy", "aerospace"
    "content_type":      str,       # knowledge: "constraint", "definition", "procedure", "reference", "table"
                                    # code: "function", "class", "module"
    "section":           str,       # document section or module path
    "knowledge_type":    str,       # knowledge only: "physical_constraint", "regulatory", "best_practice", etc.
    "function_name":     str,       # code only: function or class name
    "calls":             [str],     # code only: functions this chunk calls
    "called_by":         [str],     # code only: functions that call this chunk
    "language":          str,       # code only: programming language
    "vector_model":      str,       # embedding model identifier
    "vector_dimension":  int,       # embedding dimension (768)
    "content_hash":      str,       # SHA-256 of raw_content for dedup and incremental updates
    "ingested_at":       str        # ISO 8601 timestamp
}
```

### Metadata Filters

VectorAI DB supports filtered search — metadata filters are applied before similarity scoring, which reduces the search space and improves both speed and relevance. The following filters are used at query time:

| Filter | Purpose |
|---|---|
| `type == "knowledge"` | Retrieve only domain knowledge chunks |
| `type == "code"` | Retrieve only code chunks |
| `domain == X` | Scope to a specific domain when multiple domains are ingested |
| `content_type == X` | Narrow to constraints only, or functions only |
| `language == X` | Scope code results to a specific language |

Filters are combined with AND logic. No filter returns both types ranked together.

---

## Index Configuration

### HNSW Parameters

VectorAI DB uses HNSW-based indexing. The following parameters control the speed/recall tradeoff:

| Parameter | Value | Rationale |
|---|---|---|
| `M` | 16 | Default for datasets under 1M vectors. Higher M improves recall but increases memory and index build time. |
| `ef_construction` | 200 | Controls index quality at build time. 200 is standard for high recall. |
| `ef_search` | 128 | Controls query-time recall. Higher values improve recall at the cost of latency. For Synapse's use case (sub-second CLI queries over tens of thousands of chunks), 128 provides high recall without perceptible delay. |

### Distance Metric

**Cosine similarity** (via inner product on L2-normalized vectors).

Both nomic-embed-text-v1.5 and CodeXEmbed-400M produce L2-normalized vectors. On normalized vectors, cosine similarity is equivalent to inner product, which is the fastest distance computation. Actian should be configured to use inner product as the distance metric.

### Index Lifecycle

The HNSW index is built after the initial ingestion of a knowledge base or codebase. Subsequent incremental updates (new or changed chunks) are inserted into the existing index — VectorAI DB supports real-time indexing, so new documents are searchable immediately without a full rebuild.

A full reindex is required only when:
- The embedding model changes
- HNSW parameters are tuned
- The collection exceeds 10x its size at last index build (recall may degrade)

---

## Query Preprocessing

Every query — whether from the CLI, a code chunk, or a programmatic call — goes through the same preprocessing pipeline before hitting Actian:

```
raw input
    |
    v
embed_text construction
    |  - if raw text query: use as-is
    |  - if code file/function: generate NL description via LLM (same as code ingestion)
    |  - if knowledge chunk: use its embed_text directly
    |
    v
metadata prefix (same format as ingestion)
    |  Domain: {domain}
    |  Source: {source}
    |  Type: {type}
    |
    v
embedding via FastEmbed / nomic-embed-text-v1.5
    |
    v
L2 normalization check (should already be normalized by model)
    |
    v
query vector ready
```

The metadata prefix at query time must match the format used at ingestion time. If ingestion prepends `Domain: spectroscopy`, the query must also prepend `Domain: spectroscopy` when scoped to that domain. Mismatched prefixes degrade retrieval quality because the embedding model weights early tokens heavily.

For free text queries where the user does not specify a domain, the prefix is omitted and retrieval runs unscoped.

---

## Retrieval Patterns

### Pattern 1 — Code to Knowledge

**Trigger:** `synapse check <file_or_function>`

**Behavior:** For each code chunk in the specified file, retrieve the K nearest knowledge chunks.

```
Input:  code chunk embed_text (NL description of the function)
Filter: type == "knowledge"
K:      10
Output: list of (knowledge_chunk, similarity_score) pairs
```

This is the primary use case — checking whether code respects domain constraints. Each code chunk is compared against the full knowledge base. Results below the similarity threshold are discarded.

### Pattern 2 — Knowledge to Code

**Trigger:** `synapse coverage <domain>` or `synapse coverage <document>`

**Behavior:** For each knowledge chunk (optionally filtered by domain or source document), retrieve the K nearest code chunks.

```
Input:  knowledge chunk embed_text (NL summary of the constraint/definition)
Filter: type == "code"
K:      5
Output: list of (code_chunk, similarity_score) pairs
```

This pattern answers: "which parts of the codebase implement or relate to this domain constraint?" If a knowledge chunk has no code neighbors above the similarity threshold, it may represent an unimplemented constraint — a coverage gap.

### Pattern 3 — Free Text Query

**Trigger:** `synapse query "<question>"`

**Behavior:** Embed the raw question and retrieve the K nearest chunks of any type.

```
Input:  raw question text
Filter: none (returns both knowledge and code)
K:      10
Output: list of (chunk, similarity_score, type) triples, mixed
```

This pattern supports open-ended questions from either developers or domain experts. Results are returned in similarity order regardless of type, so a query like "wavelength normalization" might return a mix of code functions and spec sections.

### Pattern 4 — Batch Cross-Check

**Trigger:** `synapse scan` (runs on entire codebase)

**Behavior:** Iterates over all code chunks, runs Pattern 1 for each, and aggregates results into a report. This is the full-codebase drift detection pass.

```
For each code chunk in Actian where type == "code":
    retrieve K=5 nearest knowledge chunks
    if top similarity score > conflict_threshold:
        pass to LLM for conflict analysis
    if top similarity score < coverage_threshold:
        flag as "no domain context found"
```

This is computationally expensive (one query per code chunk) and is intended to run as a background job or CI step, not interactively.

---

## Scoring and Thresholds

### Similarity Score Interpretation

Cosine similarity on nomic-embed-text-v1.5 embeddings produces scores in the range [0, 1] for L2-normalized vectors (inner product). Based on empirical behavior of text embedding models:

| Score Range | Interpretation |
|---|---|
| 0.85 - 1.00 | Strong match — high semantic overlap |
| 0.70 - 0.85 | Relevant — related content, worth surfacing |
| 0.50 - 0.70 | Weak — tangentially related, may contain noise |
| Below 0.50 | Irrelevant — discard |

### Configurable Thresholds

These thresholds are stored in `.env` and are tunable per deployment:

```
SYNAPSE_RELEVANCE_THRESHOLD=0.65
SYNAPSE_CONFLICT_THRESHOLD=0.75
SYNAPSE_COVERAGE_GAP_THRESHOLD=0.50
SYNAPSE_DEFAULT_K=10
```

- `RELEVANCE_THRESHOLD`: minimum similarity score to include a result in output. Results below this are not shown to the user.
- `CONFLICT_THRESHOLD`: minimum similarity for a code-knowledge pair to be passed to the LLM for conflict analysis. Below this, the pair is assumed unrelated and no LLM call is made.
- `COVERAGE_GAP_THRESHOLD`: if the best match for a knowledge chunk scores below this, the chunk is flagged as having no corresponding code — a potential gap.
- `DEFAULT_K`: number of neighbors to retrieve per query. Can be overridden per command.

These thresholds are initial estimates and must be calibrated during Phase 1 validation on a real codebase + knowledge base. The calibration process is:

1. Ingest a known codebase and its domain documents
2. Manually identify 20-30 ground truth code-knowledge pairs
3. Run retrieval and record similarity scores for true positives and true negatives
4. Set thresholds at the point that maximizes recall without flooding the user with false positives

---

## LLM Explanation Layer

### Purpose

Raw retrieval results are lists of chunks with similarity scores. The LLM explanation layer converts these into actionable information: conflict detection, gap identification, and plain language explanations.

### When the LLM Is Called

The LLM is not called for every retrieval result. It is called only when:

- A code-knowledge pair scores above `CONFLICT_THRESHOLD` (Pattern 1 and Pattern 4)
- The user runs `synapse query` and expects a conversational answer (Pattern 3)
- A knowledge chunk has no code neighbors above `COVERAGE_GAP_THRESHOLD` (Pattern 2)

For batch operations (Pattern 4), LLM calls are the bottleneck. Each call processes one code chunk + its top K knowledge neighbors in a single prompt.

### Model

Gemma4-E4B via Ollama, running locally. No external API calls.

### Prompt Templates

#### Conflict Analysis (Pattern 1, Pattern 4)

```
You are a domain-aware code reviewer. You are given a code function
and a set of domain knowledge constraints that are semantically
related to it.

Your task:
1. Determine if the code is consistent with the domain constraints.
2. If there is a conflict, describe it precisely — what the code
   assumes vs what the domain knowledge states.
3. If there is no conflict, state that clearly.
4. Rate confidence: HIGH, MEDIUM, LOW.

CODE:
  File: {source_file}
  Function: {function_name}
  Description: {code_embed_text}
  Raw code:
  ```
  {raw_content}
  ```

DOMAIN KNOWLEDGE (ranked by relevance):
{for each knowledge chunk:}
  [{similarity_score}] {knowledge_embed_text}
  Source: {source_file}, Section: {section}
{end for}

Respond in this format:
CONFLICT: YES | NO | UNCLEAR
CONFIDENCE: HIGH | MEDIUM | LOW
EXPLANATION: <one paragraph>
SUGGESTION: <one paragraph, only if conflict detected>
```

#### Coverage Gap Analysis (Pattern 2)

```
You are a domain knowledge analyst. You are given a domain
constraint or specification that has no closely matching code
in the codebase.

Your task:
1. Determine if this constraint should have a code implementation.
2. If yes, describe what kind of code would implement it.
3. If no (e.g. it is a definition or context-only statement),
   explain why no code is expected.

DOMAIN CONSTRAINT:
  {knowledge_embed_text}
  Source: {source_file}
  Type: {knowledge_type}

Nearest code matches (all below relevance threshold):
{for each code chunk:}
  [{similarity_score}] {code_embed_text} — {function_name}
{end for}

Respond in this format:
IMPLEMENTATION_EXPECTED: YES | NO
EXPLANATION: <one paragraph>
SUGGESTED_LOCATION: <file path or module, only if implementation expected>
```

#### Free Text Query (Pattern 3)

```
You are a technical assistant for a codebase that operates in
the domain of {domain}. You have access to both the codebase
and the domain knowledge base.

A user asked: "{query}"

Here are the most relevant results from the knowledge base
and codebase:

{for each chunk, interleaved by score:}
  [{type}] [{similarity_score}] {embed_text}
  Source: {source_file}
  {if type == "code": "Function: " + function_name}
{end for}

Answer the user's question using only the information above.
If the retrieved results do not contain enough information to
answer confidently, say so. Do not fabricate information.
```

### Output Structure

LLM responses are parsed into structured results:

```python
@dataclass
class ConflictResult:
    code_chunk_id: str
    knowledge_chunk_ids: list[str]
    conflict: bool | None       # True, False, or None (unclear)
    confidence: str             # "HIGH", "MEDIUM", "LOW"
    explanation: str
    suggestion: str | None

@dataclass
class CoverageGapResult:
    knowledge_chunk_id: str
    implementation_expected: bool
    explanation: str
    suggested_location: str | None

@dataclass
class QueryResult:
    query: str
    answer: str
    sources: list[dict]         # chunk id, type, score, source_file
```

Parsing is done via simple string matching on the structured response format. If the LLM does not follow the format, the raw response is returned with a parse failure flag and the user sees the unstructured text.

---

## Incremental Updates

### Content Hashing

Every chunk stores a `content_hash` (SHA-256 of `raw_content`). When re-ingesting a file:

1. Parse and chunk the file
2. Compute content hashes for each new chunk
3. Query Actian for existing chunks from the same `source_file`
4. Compare hashes:
   - Hash match: skip (chunk unchanged)
   - Hash mismatch: upsert (update vector and metadata)
   - New hash: insert
   - Old hash not in new set: delete (chunk was removed from source)

### Upsert Strategy

VectorAI DB supports upsert by document ID. The `id` field is derived from `source_file + section/function_name + content_hash`, ensuring that changed content gets a new ID and the old version is explicitly deleted.

```python
def chunk_id(source_file: str, section: str, content_hash: str) -> str:
    raw = f"{source_file}::{section}::{content_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

The 16-character hex prefix is sufficient to avoid collisions at the scale Synapse operates (tens of thousands of chunks, not millions).

---

## CLI Commands

### `synapse check <path>`

Check a file or directory against the knowledge base.

```bash
# check a single file
synapse check ./src/signal/processing.py

# check a directory
synapse check ./src/signal/

# check with custom K and threshold
synapse check ./src/signal/processing.py --k 20 --threshold 0.60
```

Output:

```
Checking processing.py (4 functions)

  normalize_wavelength()
    CONFLICT (HIGH confidence)
    Code assumes linear wavelength scale. Domain spec states
    spectrometer uses nonlinear dispersion below 400nm.
    Suggestion: Add dispersion correction for wavelengths < 400nm.
    Sources:
      [0.91] Spectrometer Operating Manual, Section 3.2
      [0.87] Calibration Standard ISO-12345, Section 7.1

  validate_spectral_range()
    OK — no conflicts detected
    Sources:
      [0.83] Spectrometer Operating Manual, Section 2.1

  compute_resolution_delta()
    CONFLICT (MEDIUM confidence)
    Code computes resolution to 0.01nm precision. Domain spec states
    instrument resolution limit is 0.5nm.
    Suggestion: Clamp resolution output to 0.5nm minimum.
    Sources:
      [0.88] Resolution Limits, Technical Note TN-2024-003

  apply_baseline_correction()
    No domain context found (best match: 0.42)
    This function may operate outside documented domain constraints.
```

### `synapse query "<question>"`

Ask a free text question.

```bash
synapse query "is my wavelength normalization physically correct"
```

Output:

```
Based on the knowledge base and codebase:

normalize_wavelength() in signal/processing.py normalizes relative
to a 632.8nm HeNe reference. The spectrometer manual confirms
632.8nm as the standard reference wavelength (Section 2.3).

However, the function does not account for temperature-dependent
wavelength drift documented in Calibration Note CN-2024-01.
At temperatures above 35C, the reference can shift by up to 0.02nm.

Sources:
  [code]      normalize_wavelength() — signal/processing.py
  [knowledge] HeNe Reference Standard — Operating Manual, S2.3
  [knowledge] Temperature Drift — Calibration Note CN-2024-01
```

### `synapse coverage [--domain <domain>]`

Report which domain constraints have no matching code.

```bash
synapse coverage --domain spectroscopy
```

Output:

```
Coverage Report — spectroscopy (47 constraints)

  Covered (39):
    Resolution limit 0.5nm .......... validate_spectral_range()
    HeNe reference 632.8nm .......... normalize_wavelength()
    ...

  Gaps (5):
    Temperature drift correction .... no matching code found
      Expected: temperature compensation in normalization pipeline
      Suggested location: src/signal/calibration.py

    Stray light subtraction ......... no matching code found
      Expected: stray light correction before spectral analysis
      Suggested location: src/signal/preprocessing.py

    ...

  Unclear (3):
    "Operator shall verify calibration daily"
      Not expected to have code implementation (procedural requirement)
    ...
```

### `synapse scan`

Full codebase cross-check (batch, runs all code chunks through Pattern 4).

```bash
synapse scan
synapse scan --output report.json
synapse scan --ci  # exit code 1 if any HIGH confidence conflicts found
```

The `--ci` flag is designed for CI/CD integration: the command returns exit code 0 if no high-confidence conflicts are found, and exit code 1 otherwise. This allows Synapse to gate deployments.

---

## Actian VectorAI DB Client Integration

### Connection

```python
from actian_vectorai import Client

client = Client(
    host=settings.ACTIAN_HOST,       # default: "localhost"
    port=settings.ACTIAN_PORT,       # default: 8080
)
```

### Collection Setup

```python
collection = client.get_or_create_collection(
    name="synapse_chunks",
    dimension=768,
    metric="cosine",
)
```

### Insert

```python
collection.upsert(
    ids=[chunk.id],
    vectors=[chunk.vector],
    metadata={
        "type": chunk.type,
        "domain": chunk.domain,
        "source_file": chunk.source_file,
        "content_type": chunk.content_type,
        "section": chunk.section,
        "embed_text": chunk.embed_text,
        "raw_content": chunk.raw_content,
        "content_hash": chunk.content_hash,
        "vector_model": chunk.vector_model,
        "vector_dimension": chunk.vector_dimension,
        "ingested_at": chunk.ingested_at,
        # code-specific fields (null for knowledge chunks)
        "function_name": chunk.function_name,
        "calls": chunk.calls,
        "called_by": chunk.called_by,
        "language": chunk.language,
        # knowledge-specific fields (null for code chunks)
        "knowledge_type": chunk.knowledge_type,
    }
)
```

### Search

```python
results = collection.search(
    vector=query_vector,
    k=settings.DEFAULT_K,
    filters={"type": "knowledge"},
)

# results: list of {id, score, metadata}
```

### Filtered Search (Hybrid)

```python
# scoped to a domain and content type
results = collection.search(
    vector=query_vector,
    k=10,
    filters={
        "type": "knowledge",
        "domain": "spectroscopy",
        "content_type": "constraint",
    },
)
```

Note: the exact filter syntax may differ from what is shown here depending on the VectorAI DB Python client API at launch. The client is installed via `pip install actian-vectorai`. The patterns above follow the conventions from the hackathon documentation and RAG example. The abstraction layer in Synapse (see below) isolates the rest of the codebase from client API changes.

---

## Abstraction Layer

Synapse does not call the Actian client directly from CLI commands or the LLM layer. All database operations go through a `VectorStore` protocol:

```python
from typing import Protocol

class VectorStore(Protocol):
    def upsert(self, chunks: list[NormalizedChunk]) -> None: ...
    def search(
        self,
        vector: list[float],
        k: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]: ...
    def delete(self, ids: list[str]) -> None: ...
    def get_by_source(self, source_file: str) -> list[StoredChunk]: ...
    def count(self, filters: dict | None = None) -> int: ...

@dataclass
class SearchResult:
    id: str
    score: float
    metadata: dict
    embed_text: str
    raw_content: str
```

The Actian implementation lives in `backend/storage/actian.py`. This protocol allows:
- Swapping Actian for another vector DB without touching retrieval logic
- Using an in-memory implementation for tests
- Mocking storage in unit tests for the LLM explanation layer

---

## Open Questions

- **Hybrid search (dense + sparse):** VectorAI DB supports hybrid fusion (combining semantic search with keyword/BM25 search via RRF or DBSF). This could improve retrieval for queries with specific technical terms (e.g. "ISO-12345" or "HeNe laser") that embed poorly but match exactly via keyword search. Decision deferred to Phase 2 after measuring baseline dense-only retrieval quality.

- **Re-ranking:** A lightweight cross-encoder re-ranker (e.g. ms-marco-MiniLM) applied to the top K results could improve precision. This adds latency (one forward pass per result) but may be worth it for Pattern 1 and Pattern 3 where result quality directly affects user trust. Decision deferred to Phase 2.

- **Named vectors / multimodal:** VectorAI DB supports named vectors (multiple vector fields per document). A future iteration could store both a code-description vector and a raw-code vector (via CodeXEmbed) on code chunks, enabling retrieval by either semantic meaning or syntactic similarity. Not needed for Phase 1.

- **LLM prompt calibration:** The prompt templates above are first drafts. They need to be tested against real code-knowledge pairs and refined based on output quality. The structured response format (CONFLICT/CONFIDENCE/EXPLANATION) may need adjustment if the local LLM struggles to follow it consistently.

- **Batch query optimization:** Pattern 4 (full scan) generates one Actian query per code chunk. For large codebases (10k+ functions), this could take minutes. Actian may support batch vector queries — needs investigation. Alternatively, queries can be parallelized across threads since each is independent.

- **Score calibration across domains:** Similarity score distributions may vary by domain. A threshold of 0.65 might be appropriate for spectroscopy but too strict or too lenient for aerospace. Per-domain threshold profiles may be needed.
