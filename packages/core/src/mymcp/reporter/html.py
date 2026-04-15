"""Standalone HTML reporter — single file, no external assets."""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..report import CheckResult, CheckStatus, Report

_CSS = """
body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #111; }
h1 { margin: 0 0 .25rem; }
.summary { color: #555; margin-bottom: 1.5rem; }
.tool { margin-bottom: 1.25rem; }
.tool > h2 { font-size: 1.05rem; margin: 0 0 .4rem; }
.check { padding: .25rem .5rem; border-left: 3px solid #ccc; margin: .15rem 0; font-family: ui-monospace, monospace; font-size: .9rem; }
.pass { border-color: #16a34a; }
.fail { border-color: #dc2626; background: #fef2f2; }
.skip { border-color: #ca8a04; }
.msg { color: #7f1d1d; font-size: .85rem; margin-left: 1.25rem; }
.latency { color: #6b7280; margin-left: .5rem; }
"""


class HtmlReporter:
    def render(self, report: Report, out: Path | None = None, title: str = "mymcp report") -> str:
        rows: list[str] = []
        grouped: dict[str, list[CheckResult]] = {}
        for c in report.checks:
            grouped.setdefault(c.tool, []).append(c)

        for tool, checks in grouped.items():
            rows.append(f'<section class="tool"><h2>{escape(tool)}</h2>')
            for c in checks:
                cls = c.status.value
                latency = (
                    f'<span class="latency">{c.latency_ms:.0f} ms</span>'
                    if c.latency_ms is not None
                    else ""
                )
                rows.append(
                    f'<div class="check {cls}">{escape(c.check)}{latency}</div>'
                )
                if c.message and c.status is not CheckStatus.PASS:
                    rows.append(f'<div class="msg">{escape(c.message)}</div>')
            rows.append("</section>")

        summary = (
            f"{report.total} checks · "
            f"{report.passed} passed · {report.failed} failed · {report.skipped} skipped"
        )
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{escape(title)}</title><style>{_CSS}</style></head>
<body>
<h1>{escape(title)}</h1>
<div class="summary">{escape(summary)}</div>
{''.join(rows)}
</body></html>
"""
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
        return html
