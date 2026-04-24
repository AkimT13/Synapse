# Agent Integration

Synapse can be used by coding agents without a custom MCP server.

The current recommended integration surface is the CLI with JSON output.
That works for both Codex and Claude Code because both can shell out to
local commands and parse structured JSON.

## Recommended Commands

### 1. Workspace / runtime check

```bash
synapse doctor --json
```

Use this before running agent workflows to confirm:

- workspace config exists
- model providers are configured
- the vector DB is reachable

### 2. Retrieve relevant domain context

```bash
synapse query code "Behavior: detect spikes with a negative threshold." --json
```

Use this before edits when the agent needs:

- related constraints
- relevant source documents
- likely implementation expectations

### 3. Review a file after edits

```bash
synapse review --file ./sample/code/bad_spike_pipeline.py --json
```

This is the main agent-oriented command right now.

It combines:

- drift findings
- supporting domain context
- per-check status
- source citations

### 4. Run a focused drift check

```bash
synapse drift-check --file ./sample/code/bad_spike_pipeline.py --json
```

Use this when the agent only needs:

- drift status
- violations
- structured findings

### 5. Rebuild the index after model changes

```bash
synapse reindex --json
```

Use this after:

- changing embedding models
- resetting the workspace
- wanting a clean rebuild

## Suggested Agent Workflow

Pre-edit:

1. `doctor --json`
2. `query code ... --json` or `review --file ... --json`
3. make the code change

Post-edit:

1. `review --file ... --json`
2. inspect `drift_status`, `findings`, and `sources`
3. revise code if conflicts remain

## Why CLI First

This avoids extra infrastructure:

- no MCP server required
- no separate HTTP service required
- same commands work for humans and agents
- easier to version and debug

## Multi-Agent Loop

For repeated parallel implementation work, Synapse uses a hub-and-spoke model.

- one hub agent owns milestone planning, integration, verification, commits,
  and pushes
- worker agents own bounded tasks with explicit file or module ownership
- the hub maintains the live cycle contract in `MULTI_AGENT_STATUS.md`
- the operating rules live in `MULTI_AGENT_WORKFLOW.md`

Before starting a long-running multi-agent loop, create a sentinel commit so
the entire run has an obvious rollback anchor.

An MCP server may make sense later if:

- repeated calls become too slow
- multiple agent clients need a richer typed interface
- a long-lived tool server becomes operationally valuable
