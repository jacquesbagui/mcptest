"""Typer-based CLI: `mcpact run|snapshot|diff|validate`."""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from . import __version__
from .client import build_client
from .client.base import McpClient
from .client.stdio import StdioClient
from .contract import ContractError, load_contract
from .contract.engine import run_contract
from .contract.models import Contract, ServerConfig, Transport
from .report import Report
from .reporter.console import ConsoleReporter
from .reporter.html import HtmlReporter
from .reporter.json_reporter import JsonReporter
from .reporter.junit import JunitReporter
from .snapshot import capture_snapshot, diff_snapshots, load_snapshot, save_snapshot

app = typer.Typer(
    name="mcpact",
    help="Contract testing and regression detection for MCP servers.",
    no_args_is_help=True,
    add_completion=False,
)
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mcpact {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """mcpact — pytest for your MCP server."""


# ---------- run ----------

@app.command("run")
def run_cmd(
    contract: Annotated[Path, typer.Option("--contract", "-c", help="Contract YAML file.")],
    reporter: Annotated[
        str, typer.Option("--reporter", help="console | json | junit | html")
    ] = "console",
    out: Annotated[Path | None, typer.Option("--out", help="Write report to file.")] = None,
    fail_fast: Annotated[bool, typer.Option("--fail-fast", help="Stop on first failure.")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Forward server stderr to this terminal.")
    ] = False,
    no_hooks: Annotated[
        bool, typer.Option("--no-hooks", help="Skip before/after hooks (safety).")
    ] = False,
) -> None:
    """Run contract assertions against an MCP server."""
    contract_obj = _load_or_exit(contract)
    report = asyncio.run(_run(contract_obj, fail_fast=fail_fast, verbose=verbose, no_hooks=no_hooks))
    _emit_report(report, reporter, out)
    raise typer.Exit(code=0 if report.ok else 1)


# ---------- snapshot ----------

@app.command("snapshot")
def snapshot_cmd(
    out: Annotated[Path, typer.Option("--out", help="Snapshot output file.")],
    contract: Annotated[
        Path | None, typer.Option("--contract", "-c", help="Use server from this contract.")
    ] = None,
    server: Annotated[
        str | None, typer.Option("--server", help="Server command (stdio) or URL (http/sse).")
    ] = None,
    transport: Annotated[
        str, typer.Option("--transport", help="stdio | http | sse")
    ] = "stdio",
) -> None:
    """Capture the current tool surface of a server into a snapshot file."""
    config = _resolve_server(contract, server, transport)
    snap = asyncio.run(_with_client(config, lambda c: capture_snapshot(c, config.name)))
    save_snapshot(snap, out)
    typer.echo(f"✓ snapshot written to {out} ({len(snap.tools)} tools)")


# ---------- diff ----------

@app.command("diff")
def diff_cmd(
    baseline: Annotated[Path, typer.Option("--baseline", help="Baseline snapshot file.")],
    contract: Annotated[
        Path | None, typer.Option("--contract", "-c", help="Use server from this contract.")
    ] = None,
    server: Annotated[
        str | None, typer.Option("--server", help="Server command (stdio) or URL.")
    ] = None,
    transport: Annotated[str, typer.Option("--transport")] = "stdio",
    fail_on_breaking: Annotated[
        bool, typer.Option("--fail-on-breaking/--no-fail-on-breaking")
    ] = True,
) -> None:
    """Compare current server state against a baseline snapshot."""
    base = load_snapshot(baseline)
    config = _resolve_server(contract, server, transport)
    current = asyncio.run(_with_client(config, lambda c: capture_snapshot(c, config.name)))
    diff = diff_snapshots(base, current)

    if not diff.has_changes:
        typer.echo("✓ no changes")
        raise typer.Exit(code=0)

    console = Console()
    console.print("[bold]Snapshot diff:[/bold]")
    for entry in diff.entries:
        if entry.kind.value == "added":
            console.print(f"  [green]+[/green] {entry.tool}  (new tool)")
        elif entry.kind.value == "removed":
            console.print(f"  [red]-[/red] {entry.tool}  (removed — breaking)")
        else:
            marker = "[red]✗[/red]" if entry.breaking else "[yellow]~[/yellow]"
            console.print(f"  {marker} {entry.tool}")
            for d in entry.details:
                console.print(f"    [dim]└─ {d}[/dim]")

    raise typer.Exit(code=1 if fail_on_breaking and diff.has_breaking else 0)


# ---------- watch ----------

@app.command("watch")
def watch_cmd(
    contract: Annotated[Path, typer.Option("--contract", "-c", help="Contract YAML file.")],
    watch_path: Annotated[
        list[Path] | None,
        typer.Option(
            "--watch",
            "-w",
            help="Extra file/directory to watch. Repeat for multiple paths.",
        ),
    ] = None,
    fail_fast: Annotated[bool, typer.Option("--fail-fast", help="Stop on first failure.")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Forward server stderr.")
    ] = False,
) -> None:
    """Re-run the contract on file changes. Exits on Ctrl-C."""
    from watchfiles import watch as _watch

    contract_path = contract.resolve()
    extras = watch_path or []
    paths = [contract_path, *[p.resolve() for p in extras]]
    console = Console()

    def _once() -> None:
        try:
            obj = load_contract(contract_path)
        except ContractError as e:
            err_console.print(f"[red]Contract error:[/red] {e}")
            return
        report = asyncio.run(_run(obj, fail_fast=fail_fast, verbose=verbose))
        ConsoleReporter(console).render(report)
        console.print()

    console.print(f"[dim]watching {len(paths)} path(s); Ctrl-C to stop[/dim]")
    _once()
    try:
        for _ in _watch(*[str(p) for p in paths]):
            console.rule("[dim]change detected[/dim]")
            _once()
    except KeyboardInterrupt as e:
        raise typer.Exit(code=0) from e


# ---------- validate ----------

@app.command("validate")
def validate_cmd(
    contract: Annotated[Path, typer.Option("--contract", "-c", help="Contract YAML file.")],
) -> None:
    """Validate a contract file without running it."""
    _load_or_exit(contract)
    typer.echo(f"✓ {contract} is valid")


# ---------- helpers ----------

def _load_or_exit(path: Path) -> Contract:
    try:
        return load_contract(path)
    except ContractError as e:
        err_console.print(f"[red]Contract error:[/red] {e}")
        raise typer.Exit(code=2) from e


def _resolve_server(
    contract: Path | None, server: str | None, transport: str
) -> ServerConfig:
    if contract is not None:
        return _load_or_exit(contract).server
    if server is None:
        err_console.print("[red]--contract or --server is required[/red]")
        raise typer.Exit(code=2)
    if transport not in ("stdio", "http", "sse"):
        err_console.print(f"[red]Unknown transport:[/red] {transport}")
        raise typer.Exit(code=2)
    t: Transport = transport  # type: ignore[assignment]
    if t == "stdio":
        parts = shlex.split(server)
        return ServerConfig(transport=t, command=parts[0], args=parts[1:])
    return ServerConfig(transport=t, url=server)


async def _run(
    contract_obj: Contract, *, fail_fast: bool = False, verbose: bool = False, no_hooks: bool = False
) -> Report:
    client = build_client(contract_obj.server, verbose=verbose)
    try:
        try:
            await client.connect()
        except Exception as e:
            _dump_captured_stderr(client, context="connection")
            err_console.print(f"[red]Failed to connect to server:[/red] {e}")
            raise typer.Exit(code=1) from e
        return await run_contract(contract_obj, client, fail_fast=fail_fast, no_hooks=no_hooks)
    finally:
        await client.close()


def _dump_captured_stderr(client: McpClient, *, context: str) -> None:
    if isinstance(client, StdioClient):
        captured = client.captured_stderr
        if captured.strip():
            err_console.print(f"[yellow]--- server stderr (during {context}) ---[/yellow]")
            err_console.print(captured.rstrip())
            err_console.print("[yellow]--- end stderr ---[/yellow]")


async def _with_client(config: ServerConfig, fn):  # type: ignore[no-untyped-def]
    client: McpClient = build_client(config, verbose=False)
    try:
        await client.connect()
        return await fn(client)
    finally:
        await client.close()


def _emit_report(report: Report, reporter: str, out: Path | None) -> None:
    if reporter == "console":
        ConsoleReporter().render(report)
        return
    if reporter == "json":
        text = JsonReporter().render(report, out)
    elif reporter == "junit":
        text = JunitReporter().render(report, out)
    elif reporter == "html":
        text = HtmlReporter().render(report, out)
    else:
        err_console.print(f"[red]Unknown reporter:[/red] {reporter}")
        raise typer.Exit(code=2)
    if out is None:
        typer.echo(text)


if __name__ == "__main__":
    app()
