# Multi-Agent Status

This file is the live contract and execution log for the Synapse hub agent.

Update it at the start and end of every multi-agent cycle.

## Sentinel

- Start commit: `sentinel: start multi-agent polish loop`
- Current mode: hub-integrated multi-agent loop

## Current Milestone

- Milestone: make the GUI scientist-friendly for drift review
- Goal: add a browser-based drift review workflow that emphasizes evidence, comparison, and review states over generic retrieval
- Success criteria:
  - the GUI has a dedicated drift review surface
  - uploaded code files can be reviewed through an API-backed drift workflow
  - evidence and conflicts are presented in a scientist-friendly format
  - frontend and backend verification for the new flow pass

## Worker Ownership

- Hub:
  - integration
  - route integration
  - cross-surface contract cleanup
  - verification
  - commits and pushes
- Worker A:
  - backend API review surface
  - API tests
- Worker B:
  - frontend drift review page and components
  - navigation and frontend tests if needed

## Shared Contracts

- The hub is the only integration authority for the cycle.
- Worker tasks must be bounded and decision-complete before execution starts.
- Workers do not edit overlapping files unless the hub explicitly approves it.
- Every worker task includes tests or an explicit test rationale.
- No GitHub push happens until the hub finishes the verification gate.

## Verification Gate

- Touched tests pass
- Cross-surface contracts still align
- Ownership conflicts are resolved
- Residual risks are recorded
- This file is updated before the hub commits

## Current Cycle Tasks

- Add an API-backed drift review endpoint for uploaded code files
- Add a scientist-friendly drift review page to the GUI
- Connect the new page into workspace navigation
- Re-run frontend and backend verification before integration

## Blockers

- None

## Latest Cycle Summary

- Added a dedicated `/drift` workspace page for scientist-friendly browser review
- Added an API-backed `/api/review/file` flow that reuses the existing CLI-style review payload
- Connected drift review into the workspace sidebar and added evidence/comparison-focused UI treatment
- Verification:
  - `../.venv/bin/python -m pytest tests/api/test_review.py tests/cli/test_review.py -q` in `backend/`
  - `npx tsc --noEmit` in `frontend/`
