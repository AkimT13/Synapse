from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synapse_cli.drift_check_command import run_drift_check
from synapse_cli.ingest_command import run_ingest
from synapse_cli.init_command import InitOptions, prompt_for_init_options, run_init
from synapse_cli.query_command import run_query
from synapse_cli.status_command import run_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synapse")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="Create a .synapse workspace config in the target repository",
    )
    init_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root where .synapse/config.yaml should be created",
    )
    init_parser.add_argument("--name", help="Workspace name")
    init_parser.add_argument(
        "--code",
        action="append",
        default=[],
        help="Code directory to observe. Repeat for multiple roots.",
    )
    init_parser.add_argument(
        "--knowledge",
        action="append",
        default=[],
        help="Knowledge directory to ingest. Repeat for multiple roots.",
    )
    init_parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="Domain label. Repeat for multiple labels.",
    )
    init_parser.add_argument(
        "--chat-provider",
        choices=["openai", "ollama"],
        default="openai",
    )
    init_parser.add_argument(
        "--chat-model",
        default="gpt-4o-mini",
    )
    init_parser.add_argument(
        "--embedding-provider",
        choices=["openai", "ollama"],
        default="openai",
    )
    init_parser.add_argument(
        "--embedding-model",
        default="text-embedding-3-large",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing .synapse/config.yaml",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Show workspace, model, and vector DB status",
    )
    status_parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the workspace whose .synapse/config.yaml should be loaded",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest configured code and/or knowledge roots into the vector store",
    )
    ingest_parser.add_argument(
        "target",
        nargs="?",
        choices=["all", "code", "knowledge"],
        default="all",
        help="Which configured roots to ingest",
    )
    ingest_parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the workspace whose .synapse/config.yaml should be loaded",
    )
    ingest_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    query_parser = subparsers.add_parser(
        "query",
        help="Run retrieval over the configured workspace",
    )
    query_parser.add_argument(
        "mode",
        choices=["free", "code", "knowledge"],
        help="Which retrieval flow to use",
    )
    query_parser.add_argument(
        "text",
        help="Question or source text to query with",
    )
    query_parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the workspace whose .synapse/config.yaml should be loaded",
    )
    query_parser.add_argument(
        "--k",
        type=int,
        help="Override result count",
    )
    query_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    drift_parser = subparsers.add_parser(
        "drift-check",
        help="Check code against the indexed knowledge base for domain drift",
    )
    drift_input = drift_parser.add_mutually_exclusive_group(required=True)
    drift_input.add_argument(
        "text",
        nargs="?",
        help="Inline code text or behavior description to check",
    )
    drift_input.add_argument(
        "--file",
        help="Path to a Python file to check",
    )
    drift_parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the workspace whose .synapse/config.yaml should be loaded",
    )
    drift_parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of supporting knowledge chunks to consider per check",
    )
    drift_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return _handle_init(args)
    if args.command == "status":
        return _handle_status(args)
    if args.command == "ingest":
        return _handle_ingest(args)
    if args.command == "query":
        return _handle_query(args)
    if args.command == "drift-check":
        return _handle_drift_check(args)

    parser.print_help()
    return 1


def _handle_init(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()

    if args.code or args.knowledge or args.domain or args.name:
        options = InitOptions(
            repo_root=repo_root,
            workspace_name=args.name or repo_root.name,
            code_paths=args.code or ["backend", "frontend"],
            knowledge_paths=args.knowledge or ["sample/knowledge"],
            domains=args.domain or ["domain-aware-development"],
            force=args.force,
            chat_provider=args.chat_provider,
            chat_model=args.chat_model,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
        )
    else:
        options = prompt_for_init_options(
            repo_root=repo_root,
            workspace_name=args.name,
            chat_provider=args.chat_provider,
            chat_model=args.chat_model,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            force=args.force,
        )

    try:
        path = run_init(options)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Created {path}")
    return 0


def _handle_status(args: argparse.Namespace) -> int:
    exit_code, output = run_status(
        start_path=args.repo_root,
        as_json=args.json,
    )

    stream = sys.stderr if exit_code != 0 else sys.stdout
    print(output, file=stream)
    return exit_code


def _handle_ingest(args: argparse.Namespace) -> int:
    progress_sink = None
    if not args.json:
        progress_sink = lambda message: print(f"[progress] {message}", flush=True)

    exit_code, output = run_ingest(
        start_path=args.repo_root,
        target=args.target,
        as_json=args.json,
        progress_sink=progress_sink,
    )

    stream = sys.stderr if exit_code == 2 else sys.stdout
    print(output, file=stream)
    return exit_code


def _handle_query(args: argparse.Namespace) -> int:
    exit_code, output = run_query(
        start_path=args.repo_root,
        mode=args.mode,
        text=args.text,
        as_json=args.json,
        k=args.k,
    )

    stream = sys.stderr if exit_code == 2 else sys.stdout
    print(output, file=stream)
    return exit_code


def _handle_drift_check(args: argparse.Namespace) -> int:
    exit_code, output = run_drift_check(
        start_path=args.repo_root,
        text=args.text,
        file_path=args.file,
        as_json=args.json,
        k=args.k,
    )

    stream = sys.stderr if exit_code in (1, 2) else sys.stdout
    print(output, file=stream)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
