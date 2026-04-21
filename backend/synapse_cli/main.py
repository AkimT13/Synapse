from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synapse_cli.init_command import InitOptions, prompt_for_init_options, run_init
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return _handle_init(args)
    if args.command == "status":
        return _handle_status(args)

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


if __name__ == "__main__":
    raise SystemExit(main())
