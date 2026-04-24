# Synapse Multi-Agent Workflow

This document defines the default multi-agent execution model for Synapse.

The goal is to ship features and polish faster without creating merge churn,
contract drift, or shallow parallel work that has to be rewritten later.

## Default Model

Synapse uses a hub-and-spoke workflow:

- one hub agent owns milestone planning, integration, verification, commits,
  and GitHub pushes
- two or three worker agents own bounded implementation tasks in parallel
- workers do not self-organize or change shared contracts without hub approval
- the hub is the only integration authority for the cycle

Default Git strategy:

- workers complete bounded changes
- hub reviews and integrates those changes locally
- hub runs verification
- hub creates the official commit(s)
- hub pushes to GitHub

## Start Marker

Before beginning a multi-agent loop, create a sentinel commit on `main`:

```bash
git commit -m "sentinel: start multi-agent polish loop"
```

This commit is the rollback anchor for the entire loop. Every commit after it
is part of the coordinated agent run.

Recommended use:

- use the sentinel commit for full rollback if the loop goes off track
- diff everything after the sentinel when preparing demos or triaging regressions
- branch from the sentinel if only part of the post-sentinel work should survive

## Role Definitions

### Hub agent

The hub agent owns:

- milestone selection
- task decomposition
- shared contracts and interface decisions
- integration and conflict resolution
- repo-wide verification
- commit history quality
- GitHub pushes

The hub agent must maintain `MULTI_AGENT_STATUS.md` during the loop.

### Worker agents

Workers own bounded scopes for the current cycle. Default lanes:

- Worker A: backend foundations
  - ingestion
  - normalization
  - embeddings
  - retrieval
  - storage
- Worker B: product surfaces
  - API
  - frontend
  - VS Code extension
- Worker C: quality and polish
  - tests
  - fixtures
  - CLI UX
  - docs
  - demo flow

Workers may be reassigned to a narrow vertical slice for a specific milestone,
but each cycle still needs explicit ownership boundaries.

## Cycle Contract

Every worker task must be decision-complete before execution starts.

Each task contract must include:

- owned files or modules
- read-only areas
- required tests
- exact done condition
- any allowed interface changes
- explicit instruction not to revert or overwrite others' work

Workers should not edit overlapping files unless the hub explicitly approves it.

## Execution Loop

Run each cycle in this order:

1. Hub updates `MULTI_AGENT_STATUS.md` with the milestone, task owners, shared
   contracts, blockers, and verification gate.
2. Hub assigns bounded tasks to workers.
3. Workers execute in parallel.
4. Hub continues non-overlapping work while workers run:
   - reviewing contracts
   - preparing integration notes
   - checking overlap risk
   - planning the next cycle
5. Hub reviews worker outputs and resolves interface mismatches.
6. Hub runs the verification gate.
7. Hub commits integrated changes.
8. Hub pushes to GitHub.
9. Hub updates `MULTI_AGENT_STATUS.md` with results and the next target.

## Verification Gate

No integration commit should be created until:

- touched tests pass
- cross-surface contracts still align
- no unresolved ownership conflicts remain
- residual risks are recorded
- the cycle summary is updated in `MULTI_AGENT_STATUS.md`

At minimum, the hub should capture:

- tests run
- failures or skipped checks
- known follow-up work

## When To Use Subsystem vs Vertical Ownership

Use subsystem ownership when:

- the milestone changes shared foundations
- interface stability matters more than raw parallelism
- multiple surfaces depend on one backend contract

Use a narrow vertical slice when:

- the feature is small enough to be owned end-to-end
- contracts are already stable
- the work can remain isolated without broad overlap

Default to subsystem ownership if there is any doubt.

## Failure Modes

Pause the loop and re-scope if any of these happen repeatedly:

- workers edit the same files without approval
- test failures appear only after integration
- worker outputs depend on incompatible assumptions
- the hub keeps rewriting completed worker output
- status reporting is larger than implementation progress

If the loop is failing, shorten the cycle, reduce the number of workers, and
make the task contracts narrower.
