# Synapse Pipeline Demo Script

## Intro

Developers don't always read the spec. Researchers don't always read the code. Synapse sits between them — it ingests your source code and your domain documents, and continuously checks whether the two are aligned.

Here's how the pipeline works, step by step.

---

## 1. Ingestion

Two inputs: code and knowledge. Code gets parsed with tree-sitter — we pull out every function, its signature, docstring, parameters. Knowledge gets parsed with Docling — PDFs, Word docs, Markdown — keeping track of sections and pages. Both sides produce chunks.

---

## 2. Normalization

Code and spec text look nothing alike, even when they describe the same thing. Normalization rewrites each chunk into a clean natural-language description so they end up in the same semantic space. A function that checks chamber pressure and a spec that says "pressure must not exceed 20 MPa" produce similar descriptions.

---

## 3. Embedding

Each description gets turned into a vector. L2-normalized, ready for cosine similarity. The output carries the full chain back to the original source.

---

## 4. Storage — Actian VectorAI

Vectors go into Actian VectorAI, a vector database running over gRPC. Each workspace gets its own isolated collection. We use Actian's SmartBatcher to upsert in optimized batches, and each point carries filterable metadata — chunk type, domain, language — so we can scope searches at query time.

---

## 5. Retrieval

This is where it comes together. Retrieval is direction-aware — you can go from code to knowledge, knowledge to code, or just ask a free-text question across both. An LLM reads the results and gives you an explanation with citations back to the original source.
