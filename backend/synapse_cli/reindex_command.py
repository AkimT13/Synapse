from __future__ import annotations

import json
from pathlib import Path

from synapse_cli.ingest_command import run_ingest
from synapse_cli.reset_command import run_reset


def run_reindex(
    *,
    start_path: str | Path = ".",
    target: str = "all",
    as_json: bool = False,
    progress_sink=None,
) -> tuple[int, str]:
    progress_sink = progress_sink or (lambda message: None)

    reset_exit_code, reset_output = run_reset(
        start_path=start_path,
        as_json=True,
    )
    if reset_exit_code != 0:
        return reset_exit_code, reset_output

    progress_sink("[reindex] reset complete")

    ingest_exit_code, ingest_output = run_ingest(
        start_path=start_path,
        target=target,
        as_json=True,
        progress_sink=progress_sink,
    )
    if ingest_exit_code not in (0, 3):
        return ingest_exit_code, ingest_output

    reset_payload = json.loads(reset_output)
    ingest_payload = json.loads(ingest_output)
    payload = {
        "workspace": ingest_payload["workspace"],
        "target": target,
        "reset": reset_payload,
        "ingest": ingest_payload,
    }

    if as_json:
        return ingest_exit_code, json.dumps(payload, indent=2, sort_keys=True)

    return ingest_exit_code, _render_text_reindex(payload)


def _render_text_reindex(payload: dict) -> str:
    reset = payload["reset"]
    ingest = payload["ingest"]
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Target: {payload['target']}",
        f"Reset: deleted_collection={reset['deleted']}",
        "",
        "Results:",
    ]

    for item in ingest["summaries"]:
        result = item["result"]
        lines.append(
            "  - "
            f"{item['kind']} {item['path']}: "
            f"files={result['files_processed']}, "
            f"parsed={result['chunks_parsed']}, "
            f"stored={result['chunks_stored']}, "
            f"errors={len(result['errors'])}"
        )
        for error in result["errors"]:
            lines.append(f"    error: {error}")

    return "\n".join(lines)
