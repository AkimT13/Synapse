# Synapse VS Code Extension

Synapse brings the public `synapse` CLI into VS Code for demo-friendly review and query workflows. The extension stays thin on purpose: it shells out to the installed CLI, parses JSON output, and shows the results in a dedicated Activity Bar panel.

## What it exposes

- an Activity Bar container with `Status`, `Review`, and `Query` views
- editor and explorer actions for review, drift checks, ingest, and query
- a status bar summary driven by `synapse doctor --json`

V1 intentionally uses only CLI JSON transport and manual actions.

## Demo prerequisites

Before opening the extension in a demo workspace, make sure the host machine has:

- VS Code `1.88+`
- the `synapse` CLI available on `PATH`
- a workspace initialized with `.synapse/config.yaml`
- Synapse services started if the workspace depends on them
- workspace data ingested at least once

Useful setup commands:

```bash
synapse init
synapse services up
synapse ingest
synapse doctor
```

## Install for local demo use

From `vscode-extension/`:

```bash
npm run build
```

Then either:

1. Run the extension in an Extension Development Host from VS Code.
2. Package it as a VSIX and install it into the demo editor.

If you package it, keep the extension dependency-light and rely on the local `synapse` binary instead of bundling backend services.

## Demo flow

Recommended walkthrough for a live demo:

1. Open the target repo workspace in VS Code.
2. Open the `Synapse` Activity Bar container.
3. In `Status`, run `Doctor` and confirm the workspace is healthy.
4. Run `Ingest Workspace` if the workspace is new or has stale data.
5. Open a source file and run `Review Current File`.
6. Show the `Review` panel results and supporting context.
7. Highlight a relevant code snippet and run `Query Selection`.
8. Use `Query Free Text` for a domain question that benefits from citations.

## Failure handling during a demo

The extension is designed to fail into actionable guidance rather than a silent empty panel. If a command fails, check these first:

- `synapse` missing from `PATH`: install or expose the CLI to VS Code
- `.synapse/config.yaml` missing: run `synapse init`
- services unavailable: run `synapse services up`, then reopen logs if needed
- stale or missing data: run `synapse ingest`
- unexpected environment issues: run `synapse doctor`

## Commands

- `Synapse: Review Current File`
- `Synapse: Drift Check Current File`
- `Synapse: Query Selection`
- `Synapse: Query Free Text`
- `Synapse: Ingest Workspace`
- `Synapse: Reindex Workspace`
- `Synapse: Open Service Logs`
- `Synapse: Doctor`
