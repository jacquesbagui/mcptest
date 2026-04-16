"""Pretty console reporter built on `rich`."""

from __future__ import annotations

from collections import defaultdict

from rich.console import Console
from rich.text import Text

from ..report import CheckResult, CheckStatus, Report

_SYMBOLS = {
    CheckStatus.PASS: ("✓", "green"),
    CheckStatus.FAIL: ("✗", "red"),
    CheckStatus.SKIP: ("·", "yellow"),
}


class ConsoleReporter:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(self, report: Report) -> None:
        grouped: dict[str, list[CheckResult]] = defaultdict(list)
        for c in report.checks:
            grouped[c.subject].append(c)

        for tool, checks in grouped.items():
            self.console.print(Text(tool, style="bold cyan"))
            for c in checks:
                symbol, color = _SYMBOLS[c.status]
                latency = f" [{c.latency_ms:.0f}ms]" if c.latency_ms is not None else ""
                line = Text.assemble(
                    (f"  {symbol} ", color),
                    (f"{c.check}", "white"),
                    (latency, "dim"),
                )
                self.console.print(line)
                if c.message and c.status is not CheckStatus.PASS:
                    self.console.print(Text(f"    └─ {c.message}", style="dim"))

        self.console.print()
        total = report.total
        summary = (
            f"{total} checks · "
            f"[green]{report.passed} passed[/green] · "
            f"[red]{report.failed} failed[/red]"
        )
        if report.skipped:
            summary += f" · [yellow]{report.skipped} skipped[/yellow]"
        self.console.print(summary)
