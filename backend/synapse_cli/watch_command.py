from __future__ import annotations

import fnmatch
import json
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from jobs.ingest_code import CodeIngestionJob
from jobs.ingest_knowledge import KnowledgeIngestionJob
from storage.vector_store import VectorStore
from workspace import init_models_from_workspace
from workspace.loader import LoadedWorkspaceConfig, ResolvedSourceRoot, load_workspace_config


@dataclass(frozen=True)
class WatchTarget:
    kind: str
    path: Path
    include: list[str]
    exclude: list[str]
    metadata: dict[str, list[str]]


@dataclass(frozen=True)
class FileFingerprint:
    mtime_ns: int
    size: int


def run_watch(
    *,
    start_path: str | Path = ".",
    poll_interval: float = 1.0,
    debounce_ms: int | None = None,
    as_json: bool = False,
    progress_sink=None,
    max_cycles: int | None = None,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    init_models_from_workspace(workspace)
    progress_sink = progress_sink or (lambda message: None)
    debounce_seconds = (
        debounce_ms / 1000.0
        if debounce_ms is not None
        else workspace.config.watch.debounce_ms / 1000.0
    )

    targets = _build_targets(workspace)
    if not targets:
        return 1, "No watchable code_roots or knowledge_roots configured."

    snapshots = {target.path: _scan_target(target) for target in targets}
    pending: dict[Path, float] = {}
    events: list[dict] = []

    progress_sink(f"[watch] watching {len(targets)} roots")

    cycles = 0
    try:
        with VectorStore() as store:
            while True:
                now = time.monotonic()
                for target in targets:
                    current = _scan_target(target)
                    previous = snapshots[target.path]
                    change_count = _count_changes(previous, current)
                    if change_count:
                        snapshots[target.path] = current
                        pending[target.path] = now + debounce_seconds
                        progress_sink(
                            f"[watch] detected {change_count} changed file(s) under {target.path}"
                        )

                due_paths = [
                    target.path
                    for target in targets
                    if target.path in pending and pending[target.path] <= now
                ]
                for path in due_paths:
                    target = next(item for item in targets if item.path == path)
                    event = _run_target_ingest(target=target, store=store, progress_sink=progress_sink)
                    events.append(event)
                    del pending[path]

                cycles += 1
                if max_cycles is not None and cycles >= max_cycles:
                    break

                time.sleep(poll_interval)
    except KeyboardInterrupt:
        progress_sink("[watch] stopped")

    payload = {
        "workspace": workspace.config.workspace.name,
        "watching": [str(target.path) for target in targets],
        "events": events,
    }
    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_watch(payload)


def _build_targets(workspace: LoadedWorkspaceConfig) -> list[WatchTarget]:
    targets: list[WatchTarget] = []
    for root in workspace.code_roots:
        targets.append(_make_target("code", root))
    for root in workspace.knowledge_roots:
        targets.append(_make_target("knowledge", root))
    return targets


def _make_target(kind: str, root: ResolvedSourceRoot) -> WatchTarget:
    return WatchTarget(
        kind=kind,
        path=root.path,
        include=list(root.include),
        exclude=list(root.exclude),
        metadata=dict(root.metadata),
    )


def _scan_target(target: WatchTarget) -> dict[str, FileFingerprint]:
    if not target.path.exists():
        return {}

    snapshot: dict[str, FileFingerprint] = {}
    for path in target.path.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(target.path).as_posix()
        if not _matches(relative, target.include, target.exclude):
            continue
        stat = path.stat()
        snapshot[str(path)] = FileFingerprint(mtime_ns=stat.st_mtime_ns, size=stat.st_size)
    return snapshot


def _matches(relative_path: str, include: list[str], exclude: list[str]) -> bool:
    path = PurePosixPath(relative_path)
    included = any(_match_pattern(path, pattern) for pattern in include) if include else True
    excluded = any(_match_pattern(path, pattern) for pattern in exclude)
    return included and not excluded


def _match_pattern(path: PurePosixPath, pattern: str) -> bool:
    normalized = pattern.lstrip("/")
    if "__pycache__" in normalized and "__pycache__" in path.parts:
        return True
    return path.match(normalized) or fnmatch.fnmatch(path.as_posix(), normalized)


def _count_changes(
    previous: dict[str, FileFingerprint],
    current: dict[str, FileFingerprint],
) -> int:
    changed = 0
    all_paths = set(previous) | set(current)
    for path in all_paths:
        if previous.get(path) != current.get(path):
            changed += 1
    return changed


def _run_target_ingest(
    *,
    target: WatchTarget,
    store: VectorStore,
    progress_sink,
) -> dict:
    progress_sink(f"[watch] reindexing {target.kind} root {target.path}")

    if target.kind == "code":
        result = CodeIngestionJob(
            vector_store=store,
            should_use_llm=True,
            on_progress=lambda message: progress_sink(f"[watch][code] {message}"),
        ).run(
            str(target.path),
            languages=target.metadata.get("language_hints") or None,
        )
    else:
        result = KnowledgeIngestionJob(
            vector_store=store,
            should_use_llm=True,
            on_progress=lambda message: progress_sink(f"[watch][knowledge] {message}"),
        ).run(str(target.path))

    progress_sink(
        f"[watch] updated {target.kind} root {target.path} "
        f"(files={result.files_processed}, stored={result.chunks_stored}, errors={len(result.errors)})"
    )
    return {
        "kind": target.kind,
        "path": str(target.path),
        "result": result.model_dump(),
    }


def _render_text_watch(payload: dict) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Watching ({len(payload['watching'])}):",
    ]
    lines.extend(f"  - {path}" for path in payload["watching"])
    lines.append("")
    lines.append(f"Events: {len(payload['events'])}")
    for event in payload["events"]:
        result = event["result"]
        lines.append(
            "  - "
            f"{event['kind']} {event['path']}: "
            f"files={result['files_processed']}, "
            f"parsed={result['chunks_parsed']}, "
            f"stored={result['chunks_stored']}, "
            f"errors={len(result['errors'])}"
        )
    return "\n".join(lines)
