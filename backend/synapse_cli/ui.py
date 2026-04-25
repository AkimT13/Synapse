from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

# Spinners/status → stderr so they don't pollute stdout pipelines.
console = Console(stderr=True)

_BANNER = r"""
 ____  _  _  __ _   __   ____  ____  ____
/ ___)( \/ )(  ( \ / _\ (  _ \/ ___)(  __)
\___ \ )  / /    //    \ ) __/\___ \ ) _)
(____/(__/  \_)__)\_/\_/(__)  (____/(____)
  domain-aware review · drift detection · retrieval
"""

_STATUS_COLORS = {
    "aligned": "green",
    "warning": "yellow",
    "conflict": "red",
    "unknown": "dim",
}

_STATUS_ICONS = {
    "aligned": "✓ aligned",
    "warning": "⚠ warning",
    "conflict": "✖ conflict",
    "unknown": "? unknown",
}


def _out() -> Console:
    """Return a stdout Console resolved at call time (picks up pytest capsys)."""
    return Console(file=sys.stdout, highlight=False)


def print_banner() -> None:
    console.print(_BANNER, style="bold cyan", highlight=False)


@contextmanager
def spinner(label: str) -> Iterator[None]:
    with console.status(f"[bold cyan]{label}[/bold cyan]", spinner="dots"):
        yield


def make_ingest_progress() -> Progress:
    """Return a Rich Progress configured for ingest operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )


# ---------------------------------------------------------------------------
# Rich renderers
# ---------------------------------------------------------------------------


def render_drift(payload: dict) -> None:
    out = _out()
    status = payload.get("status", "unknown")
    color = _STATUS_COLORS.get(status, "dim")
    checks = payload.get("checks", [])

    out.print()
    out.print(f"[bold]Workspace:[/bold] {payload.get('workspace', '')}")
    out.print(f"[bold]Target:[/bold] {payload.get('target', '')}")
    out.print(f"[bold]Status:[/bold] [{color}]{status}[/{color}]")
    out.print(f"\nChecks ({len(checks)}):")

    for check in checks:
        _render_check_card(out, check)


def render_review(payload: dict) -> None:
    out = _out()
    status = payload.get("drift_status", "unknown")
    color = _STATUS_COLORS.get(status, "dim")

    out.print()
    out.print(f"[bold]Workspace:[/bold] {payload.get('workspace', '')}")
    out.print(f"[bold]Target:[/bold] {payload.get('target', '')}")
    out.print(f"[bold]Drift status:[/bold] [{color}]{status}[/{color}]")
    out.print()

    drift_entries = payload.get("drift", [])
    context_entries = payload.get("context", [])

    out.rule("[bold]Drift Findings[/bold]")
    for check in drift_entries:
        _render_check_card(out, check)

    if context_entries:
        out.print()
        out.rule("[dim]Supporting Context[/dim]")
        for ctx in context_entries:
            sources = ctx.get("sources", [])
            if not sources:
                continue
            tbl = Table(show_header=True, header_style="dim", box=None, padding=(0, 1))
            tbl.add_column("Source", style="dim")
            tbl.add_column("Kind", style="dim")
            tbl.add_column("Score", style="dim", justify="right")
            for src in sources[:5]:
                tbl.add_row(
                    src.get("source_file", ""),
                    src.get("kind", ""),
                    f"{src.get('score', 0):.3f}",
                )
            out.print(
                Panel(
                    tbl,
                    title=f"[dim]{ctx.get('label', '')}[/dim]",
                    border_style="dim",
                    expand=False,
                )
            )


def render_ingest(payload: dict) -> None:
    out = _out()
    tbl = Table(show_header=True, header_style="bold", expand=False)
    tbl.add_column("Kind")
    tbl.add_column("Path")
    tbl.add_column("Files", justify="right")
    tbl.add_column("Stored", justify="right")
    tbl.add_column("Errors", justify="right")

    for item in payload.get("summaries", []):
        result = item.get("result", {})
        errors = len(result.get("errors", []))
        tbl.add_row(
            item.get("kind", ""),
            item.get("path", ""),
            str(result.get("files_processed", 0)),
            str(result.get("chunks_stored", 0)),
            f"[red]{errors}[/red]" if errors else "0",
        )

    out.print()
    out.print(f"[bold]Workspace:[/bold] {payload.get('workspace', '')}")
    out.print(f"[bold]Target:[/bold] {payload.get('target', '')}")
    out.print()
    out.print(tbl)


def render_reindex(payload: dict) -> None:
    out = _out()
    reset = payload.get("reset", {})
    ingest = payload.get("ingest", {})

    out.print()
    out.print(f"[bold]Workspace:[/bold] {payload.get('workspace', '')}")
    out.print(f"[bold]Target:[/bold] {payload.get('target', '')}")
    out.print(f"[bold]Reset:[/bold] deleted_collection={reset.get('deleted', False)}")
    out.print()

    # Re-use ingest table for the ingest summary
    tbl = Table(show_header=True, header_style="bold", expand=False)
    tbl.add_column("Kind")
    tbl.add_column("Path")
    tbl.add_column("Files", justify="right")
    tbl.add_column("Stored", justify="right")
    tbl.add_column("Errors", justify="right")

    for item in ingest.get("summaries", []):
        result = item.get("result", {})
        errors = len(result.get("errors", []))
        tbl.add_row(
            item.get("kind", ""),
            item.get("path", ""),
            str(result.get("files_processed", 0)),
            str(result.get("chunks_stored", 0)),
            f"[red]{errors}[/red]" if errors else "0",
        )

    if ingest.get("summaries"):
        out.print(tbl)


def render_doctor(payload: dict) -> None:
    out = _out()
    ws = payload.get("workspace", {})
    out.print()
    out.print(f"[bold]Workspace:[/bold] {ws.get('name', '')}")
    out.print(f"[bold]Repo root:[/bold] {ws.get('repo_root', '')}")
    out.print(f"[bold]Config:[/bold] {ws.get('config_path', '')}")
    out.print(f"[bold]Runtime compose:[/bold] {ws.get('runtime_compose_path', '')}")

    overall_ok = payload.get("ok", False)
    out.print(f"[bold]Overall:[/bold] {'ok' if overall_ok else 'fail'}")
    out.print()

    tbl = Table(show_header=True, header_style="bold", expand=False)
    tbl.add_column("Check")
    tbl.add_column("Status", justify="center")
    tbl.add_column("Detail")

    for check in payload.get("checks", []):
        ok = check.get("ok", False)
        status_cell = "[green]✔[/green]" if ok else "[red]✖[/red]"
        tbl.add_row(check.get("name", ""), status_cell, check.get("detail", ""))

    out.print(tbl)

    fixes = payload.get("suggested_fixes", [])
    if fixes:
        out.print()
        out.print("[bold]Suggested fixes:[/bold]")
        for fix in fixes:
            out.print(f"  [yellow]→[/yellow] {fix}")


def render_query(payload: dict) -> None:
    out = _out()
    mode = payload.get("mode", "")
    out.print()
    out.print(f"[bold]Mode:[/bold] {mode}")
    out.print(f"[bold]Query:[/bold] {payload.get('query', '')}")
    out.print()

    if "answer" in payload:
        out.print(Panel(payload["answer"], title="Answer:", border_style="green"))

    if "explanation" in payload:
        out.print(Panel(payload["explanation"], title="Explanation:", border_style="cyan"))

    for flag, label in (
        ("has_conflict", "Has conflict"),
        ("used_fallback", "Used fallback"),
        ("is_implemented", "Is implemented"),
    ):
        if flag in payload:
            value = payload[flag]
            color = "red" if (flag == "has_conflict" and value) else ("green" if value else "yellow")
            out.print(f"[bold]{label}:[/bold] [{color}]{value}[/{color}]")

    results = payload.get("results", [])
    if results:
        out.print()
        out.print(f"Results ({len(results)}):")
        tbl = Table(show_header=True, header_style="bold", expand=False)
        tbl.add_column("#", justify="right")
        tbl.add_column("Type")
        tbl.add_column("Kind")
        tbl.add_column("Source")
        tbl.add_column("Score", justify="right")
        for i, r in enumerate(results, start=1):
            tbl.add_row(
                str(i),
                r.get("chunk_type", ""),
                r.get("kind", ""),
                r.get("source_file", ""),
                f"{r.get('score', 0):.3f}",
            )
        out.print(tbl)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _render_check_card(out: Console, check: dict) -> None:
    status = check.get("status", "unknown")
    color = _STATUS_COLORS.get(status, "dim")
    confidence = check.get("confidence", "")
    label = check.get("label", "")

    title = f"{label}  [{color}]{_STATUS_ICONS.get(status, status)} · {confidence}[/{color}]"

    body_lines: list[str] = []
    summary = check.get("summary", "")
    if summary:
        body_lines.append(summary)

    line_range = check.get("line_range")
    if line_range:
        body_lines.append(
            f"\n[dim]Lines {line_range['start']}–{line_range['end']}[/dim]"
        )

    findings = check.get("findings", [])
    violations = check.get("violations", [])

    if findings:
        tbl = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        tbl.add_column("Expected")
        tbl.add_column("Observed")
        for f in findings:
            tbl.add_row(f.get("expected", ""), f.get("observed", ""))
        out.print(
            Panel(
                tbl,
                title=title,
                border_style=color,
            )
        )
    else:
        body_text = "\n".join(body_lines)
        if violations:
            body_text += "\n"
            for v in violations:
                body_text += f"\n[red]• {v}[/red]"
        out.print(
            Panel(
                body_text or summary,
                title=title,
                border_style=color,
            )
        )


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------


def run_interactive_menu(repo_root: str = ".") -> int:
    menu_out = _out()
    menu_out.print("[bold]What would you like to do?[/bold]\n")
    menu_out.print("  [cyan][1][/cyan] Review a file")
    menu_out.print("  [cyan][2][/cyan] Drift check a file")
    menu_out.print("  [cyan][3][/cyan] Ingest workspace")
    menu_out.print("  [cyan][4][/cyan] Run doctor")
    menu_out.print("  [cyan][5][/cyan] Query free text")
    menu_out.print("  [cyan][6][/cyan] Install agent skills (Claude Code / Codex)")
    menu_out.print("  [cyan][7][/cyan] Install VS Code extension")
    menu_out.print("  [cyan][8][/cyan] Launch GUI")
    menu_out.print()

    choices = [str(i) for i in range(1, 9)]
    choice = IntPrompt.ask("Choose", choices=choices, console=menu_out)

    if choice == 1:
        file_path = Prompt.ask("File path", console=menu_out)
        from synapse_cli.review_command import run_review
        with spinner("Analyzing…"):
            exit_code, json_output = run_review(
                start_path=repo_root, file_path=file_path, as_json=True
            )
        if exit_code not in (0,):
            console.print(f"[red]{json_output}[/red]")
            return exit_code
        render_review(json.loads(json_output))
        return exit_code

    if choice == 2:
        file_path = Prompt.ask("File path", console=menu_out)
        from synapse_cli.drift_check_command import run_drift_check
        with spinner("Analyzing…"):
            exit_code, json_output = run_drift_check(
                start_path=repo_root, file_path=file_path, as_json=True
            )
        if exit_code not in (0,):
            console.print(f"[red]{json_output}[/red]")
            return exit_code
        render_drift(json.loads(json_output))
        return exit_code

    if choice == 3:
        from synapse_cli.ingest_command import run_ingest

        def sink(msg: str) -> None:
            console.print(f"[dim]{msg}[/dim]")

        exit_code, json_output = run_ingest(
            start_path=repo_root, as_json=True, progress_sink=sink
        )
        if exit_code not in (0, 3):
            console.print(f"[red]{json_output}[/red]")
            return exit_code
        render_ingest(json.loads(json_output))
        return exit_code

    if choice == 4:
        from synapse_cli.doctor_command import run_doctor
        with spinner("Running checks…"):
            exit_code, json_output = run_doctor(start_path=repo_root, as_json=True)
        render_doctor(json.loads(json_output))
        return exit_code

    if choice == 5:
        text = Prompt.ask("Query text", console=menu_out)
        from synapse_cli.query_command import run_query
        with spinner("Querying…"):
            exit_code, json_output = run_query(
                start_path=repo_root, mode="free", text=text, as_json=True
            )
        if exit_code not in (0,):
            console.print(f"[red]{json_output}[/red]")
            return exit_code
        render_query(json.loads(json_output))
        return exit_code

    if choice == 6:
        from synapse_cli.install_skill_command import run_install_skill
        menu_out.print()
        menu_out.print("  [cyan][1][/cyan] Claude Code only")
        menu_out.print("  [cyan][2][/cyan] Codex only")
        menu_out.print("  [cyan][3][/cyan] Both")
        menu_out.print()
        agent_choice = IntPrompt.ask("Choose", choices=["1", "2", "3"], console=menu_out)
        agent_map = {1: "claude", 2: "codex", 3: "both"}
        exit_code, output = run_install_skill(
            start_path=repo_root,
            agent=agent_map[agent_choice],
            force=True,
        )
        if exit_code != 0:
            console.print(f"[red]{output}[/red]")
        else:
            menu_out.print(f"\n{output}")
        return exit_code

    if choice == 7:
        from synapse_cli.vscode_command import run_vscode_install
        return run_vscode_install()

    if choice == 8:
        from synapse_cli.ui_command import run_ui
        return run_ui()

    return 0
