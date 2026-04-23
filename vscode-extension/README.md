# Synapse VS Code Extension

This package exposes the public `synapse` CLI inside VS Code through:

- an Activity Bar container with `Status`, `Review`, and `Query` views
- editor and explorer actions for review, drift checks, ingest, and query
- a status bar summary driven by `synapse doctor --json`

V1 intentionally uses only CLI JSON transport and manual actions.
