# Synapse Milestones

This document lays out the highest-value milestones for turning Synapse
from a useful local demo into a domain-aware development system that
actively prevents software from drifting away from physical, scientific,
or regulatory reality.

The emphasis is on workflows that fit how developers actually work:

- in the editor while writing code
- in the terminal while setting up and operating Synapse
- inside coding agents such as Codex and Claude Code
- in the existing GUI for ingestion, browsing, and investigation

## Product Direction

Synapse should evolve into a domain runtime for software development:

- it indexes code and domain knowledge continuously, not just manually
- it warns when code likely violates real-world constraints
- it gives actionable guidance at authoring time, not only after the fact
- it becomes usable by both humans and coding agents
- it supports local-first workflows, while still allowing richer GUI flows

## First Big Product Move

The first major step in this direction is to turn Synapse into a shared
workspace/runtime layer with a first-class CLI.

That means:

- one workspace model that defines what Synapse observes
- one configuration format shared across GUI, terminal, and future editor tooling
- one machine-friendly interface that humans, VS Code, Codex, and Claude Code
  can all rely on

Why this comes first:

- the current system already has ingestion, retrieval, chat, and a GUI
- what it lacks is a stable operational layer that other clients can use
- without that layer, every future integration becomes a one-off implementation

This first move should produce:

1. A Synapse workspace config.
- code roots
- knowledge roots
- include/exclude globs
- domain tags
- optional provider/runtime settings where appropriate

2. A first-class `synapse` CLI.
- `synapse init`
- `synapse ingest code`
- `synapse ingest knowledge`
- `synapse query`
- `synapse drift-check`
- `synapse status`

3. Machine-friendly outputs and contracts.
- JSON output
- stable exit codes
- explicit request/response shapes for retrieval and diagnostics

4. A shared foundation for future clients.
- GUI uses the same workspace concepts
- VS Code becomes a client of Synapse rather than bespoke glue
- coding agents can call Synapse before, during, and after edits

## Milestone 1: Stabilize The Core Platform

Goal: make the current backend + frontend reliable enough to serve as a
foundation for editor, CLI, and agent integrations.

Why this matters:
- the current app already has ingestion, retrieval, chat, and corpus browsing
- higher-level integrations will be fragile unless the local platform is
  predictable, testable, and scriptable

Substeps:

1. Fix the backend test path and dependency story.
- make `pytest` installation part of the standard backend setup
- resolve the current `mocker` vs `unittest.mock` mismatch in agent tests
- add a documented fast local test command for agent, retrieval, and API tests

2. Harden ingestion and workspace contracts.
- document the exact API surface for code ingestion, knowledge ingestion,
  job streaming, workspace reset, and corpus browsing
- verify upload replacement semantics and error handling
- add focused tests for ingestion job SSE progress and reset behavior

3. Define stable retrieval interfaces.
- make the retrieval pipeline outputs explicit and documented
- add a thin service layer or contract doc that editor, CLI, and agent
  integrations can depend on
- identify which retrieval interfaces are human-facing vs machine-facing

4. Close current behavior gaps in the shipped app.
- implement chat scope filtering or remove the misleading UI affordance
- align onboarding labels with actual capabilities
- document what is supported today: local folder ingestion, local document
  ingestion, retrieval, chat, and corpus browsing

## Milestone 2: Build A Real CLI

Goal: make Synapse usable from the terminal as a developer tool, not just
as a browser app.

Why this matters:
- coding agents and editor plugins need a scriptable interface
- many developers will want to initialize and run Synapse without touching
  the GUI first
- the CLI can become the stable orchestration layer shared by humans,
  VS Code, and agent tools

Substeps:

1. Introduce a first-class `synapse` CLI.
- add commands such as `synapse init`, `synapse ingest code`,
  `synapse ingest knowledge`, `synapse status`, `synapse query`,
  and `synapse doctor`
- keep the CLI local-first and repo-oriented
- make output readable by both humans and machines

2. Add workspace configuration.
- define a config file such as `.synapse/config.yaml` or `synapse.toml`
- let users declare code directories, knowledge directories, file filters,
  language hints, and domain tags
- support multiple corpora and multiple repos over time

3. Add watch and refresh workflows.
- support `synapse watch` to observe configured directories
- re-ingest changed code or knowledge incrementally
- track last-ingested fingerprints so re-indexing is cheap

4. Add machine-friendly output modes.
- support JSON output for retrieval and diagnostics
- expose a non-interactive mode for editor extensions and coding agents
- return stable exit codes for warnings, errors, and drift detections

5. Make the CLI and GUI work together.
- the GUI should be able to read the same configured workspace
- the CLI should be able to seed or update the same underlying corpora
- avoid splitting the product into two separate systems

Definition of done for this milestone:

- a developer can run `synapse init` in a repo
- Synapse can persist code and knowledge roots in a shared config
- ingestion can run without opening the browser
- retrieval and drift-check can be invoked from scripts and coding agents
- the GUI can operate against the same configured workspace model

## Milestone 3: Add Domain Drift Detection That Feels Real

Goal: move beyond generic retrieval into explicit detection of likely
mismatches between code behavior and domain constraints.

Why this matters:
- retrieval is helpful, but warnings and decisions are where the product
  becomes truly differentiated
- domain-sensitive code needs stronger signals than "here are related docs"

Substeps:

1. Define drift signal types.
- threshold mismatch
- unit mismatch
- missing validation
- outdated assumption
- constraint violation
- suspicious omission

2. Add structured rule generation from knowledge.
- extract constraints, units, conditions, failure modes, and decision context
- distinguish hard constraints from soft guidance
- keep provenance so every warning points back to a source

3. Add code-side detectors.
- detect functions touching domain-relevant constants, thresholds, ranges,
  validation logic, conversions, calibration paths, or model assumptions
- classify whether code appears domain-sensitive enough to merit checking
- support both AST-based and retrieval-based matching

4. Produce actionable warnings.
- warnings should explain what looks risky, why it may violate reality,
  and which source supports the claim
- warnings should include severity, confidence, and likely remediation paths
- allow developer decisions to be stored as agent memory or review memory

5. Track decisions over time.
- persist accepted warnings, dismissed warnings, and baselines
- detect when a previously dismissed warning should be reconsidered because
  the code or knowledge changed
- expose these decisions in CLI and GUI

## Milestone 4: Ship A VS Code Extension

Goal: surface domain-aware suggestions and warnings inside the editor while
developers are writing code.

Why this matters:
- this is the most natural daily workflow for the target user
- Synapse becomes proactive instead of purely search-driven

Substeps:

1. Build the editor-to-Synapse bridge.
- let the extension discover a local Synapse workspace
- call the CLI or a local API for retrieval, diagnostics, and file status
- handle offline and not-running cases gracefully

2. Detect relevant coding moments.
- on file open for domain-relevant files
- on selection of a function or class
- on save when code changed materially
- on hover or code action request near thresholds, units, constraints,
  or validation logic

3. Add a Synapse side panel.
- show related domain knowledge for the current file or symbol
- show warnings, citations, and prior decisions
- let the user jump directly to supporting documents and related code

4. Add inline affordances.
- diagnostics for likely drift or missing checks
- code actions such as "show related constraints", "explain this warning",
  or "mark as reviewed"
- lightweight hover cards for cited knowledge

5. Make the extension configurable.
- let users tune strictness, trigger modes, and watched scopes
- allow per-workspace domain settings
- support both local and team-shared policies later

## Milestone 5: Integrate With Coding Agents

Goal: make Synapse directly useful to Codex, Claude Code, and other coding
agents during implementation, refactoring, and review.

Why this matters:
- coding agents can write a lot of code quickly
- they are especially dangerous in domain-heavy systems if they only reason
  from source code and not from real-world constraints

Substeps:

1. Define agent-facing primitives.
- retrieve relevant knowledge for a file, symbol, diff, or prompt
- retrieve related code for a domain constraint
- run a drift check on a proposed change
- store a decision or review memory

2. Make these primitives available in machine-friendly form.
- CLI commands with JSON output
- a local HTTP API if needed
- clear request and response schemas with citations and confidence fields

3. Support pre-edit and post-edit workflows.
- before editing: fetch relevant constraints and warnings
- during editing: query a specific function or patch
- after editing: run a drift review over the changed code

4. Create promptable integration patterns.
- "before writing code in this file, ask Synapse for related domain constraints"
- "after modifying this function, run a Synapse drift check"
- "when a warning is dismissed, record the rationale as memory"

5. Add review-oriented summaries.
- summarize likely domain risks in a diff
- highlight changes that alter thresholds, ranges, units, or safety checks
- generate source-backed review notes instead of vague comments

## Milestone 6: Add Continuous Project Awareness

Goal: make Synapse maintain awareness of a live project instead of behaving
like a one-time ingest tool.

Why this matters:
- real repositories and domain docs evolve continuously
- static indexing is not enough for an always-useful assistant

Substeps:

1. Support incremental ingestion.
- re-index only changed code and changed documents
- preserve deterministic lineage
- prune or mark stale chunks cleanly

2. Add file and directory watchers.
- watch configured code and knowledge directories
- debounce noisy changes
- surface index freshness in CLI and GUI

3. Add knowledge version awareness.
- detect when a document revision changes an important constraint
- highlight which code areas may need re-review
- track recency and source authority in retrieval results

4. Add project-level health views.
- which code areas have good domain coverage
- which important docs have no code linkage
- which warnings are unresolved or frequently dismissed

## Milestone 7: Improve Knowledge Ingestion Quality

Goal: make Synapse more trustworthy by improving how domain material is
parsed, normalized, and prioritized.

Why this matters:
- better retrieval depends on better chunks
- many failures in domain tools come from weak extraction of constraints

Substeps:

1. Improve source handling.
- support PDFs, DOCX, Markdown, HTML, plain text robustly
- normalize headings, tables, footnotes, and appendices better
- separate procedural text from hard constraints

2. Add source ranking and trust models.
- mark documents by authority, recency, and type
- rank standards/specs above drafts or notes when appropriate
- preserve confidence and provenance through retrieval

3. Support curated metadata.
- domains, subsystems, units, jurisdictions, standards, owners
- let users annotate important docs manually when needed
- use metadata to filter and improve retrieval

4. Detect contradictory knowledge.
- identify conflicting constraints across docs
- surface this explicitly instead of hiding it in retrieval noise
- support human review and resolution workflows

## Milestone 8: Evolve The GUI Into An Investigation Console

Goal: make the current frontend more than an ingestion demo by turning it
into a place where developers and domain experts can investigate drift,
coverage, and evidence.

Why this matters:
- the GUI is already a usable browsing and chat surface
- it can become the review and triage interface that complements the CLI
  and editor plugin

Substeps:

1. Add a drift review view.
- list current warnings by severity, confidence, subsystem, and status
- show cited evidence from both code and knowledge
- support accept, dismiss, and baseline actions

2. Add code-to-knowledge and knowledge-to-code traceability views.
- visualize which docs map to which files and symbols
- reveal coverage gaps
- show confidence and unresolved ambiguity

3. Add workspace configuration UI.
- inspect and edit the same workspace config used by the CLI
- manage watched directories and domain filters
- show ingestion freshness and indexing status

4. Add team-facing review flows later.
- share warning states
- assign owners
- track decision history

## Milestone 9: Support Multi-Repository And Larger Teams

Goal: expand Synapse from a single local workspace into a system that can
cover larger engineering environments.

Why this matters:
- many real domain problems span services, libraries, and standards repos
- the highest-value use cases usually involve multiple codebases and
  multiple knowledge sources

Substeps:

1. Support multiple code roots and knowledge roots.
- shared workspace config
- clear corpus labeling
- scoped retrieval and scoped warnings

2. Add repo-aware and subsystem-aware retrieval.
- understand which results belong to which repo or service
- improve ranking with path, ownership, and subsystem metadata
- let users narrow checks intentionally

3. Plan for collaboration primitives.
- shared warning states
- shared memory and rationale
- policy packs for teams or domains

## Milestone 10: Reach A Strong V1

Goal: package Synapse as a coherent product with one clear developer loop.

Target V1 experience:

1. Run `synapse init`.
2. Point Synapse at code directories and knowledge directories.
3. Start `synapse watch` or open the GUI.
4. Write code in VS Code with Synapse suggestions active.
5. Let coding agents query Synapse before and after edits.
6. Review warnings and decisions in the GUI or terminal.

V1 completion checklist:

- stable local workspace config
- reliable CLI for ingest, query, watch, and diagnostics
- solid retrieval and drift-check APIs
- working VS Code extension with side panel and basic diagnostics
- coding-agent integration via CLI or local API
- GUI views for ingestion, traceability, drift review, and decision history

## Suggested Build Order

Recommended order of execution:

1. Stabilize core platform and tests
2. Build CLI and shared workspace config
3. Add incremental ingestion and watch mode
4. Define drift signal types and warning outputs
5. Integrate coding agents through the CLI
6. Build the VS Code extension
7. Expand the GUI into a review console
8. Improve knowledge quality and contradiction handling
9. Add multi-repo and team features

## Immediate Next Slice

If the goal is to start moving now, the best near-term implementation
sequence is:

1. Create a shared workspace config format.
- this is the first concrete implementation step
- define code roots, knowledge roots, include/exclude globs, and domain tags
- choose where the config lives, for example `.synapse/config.yaml` or
  `synapse.toml`
- define how the backend and future CLI will load it

2. Build `synapse init` and `synapse ingest`.
- make Synapse operable without the GUI

3. Add `synapse query` and `synapse drift-check`.
- give coding agents and editor integrations a stable machine interface

4. Add `synapse watch`.
- make the index stay fresh with minimal developer effort

5. Build the first VS Code side panel.
- start with selection-based retrieval and warnings before attempting
  deep inline diagnostics
