"""JSON reporter — machine-readable output for CI and tooling."""

from __future__ import annotations

import json
from pathlib import Path

from ..report import Report


class JsonReporter:
    def render(self, report: Report, out: Path | None = None) -> str:
        payload = {
            "ok": report.ok,
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "checks": [
                {
                    "subject": c.subject,
                    "check": c.check,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for c in report.checks
            ],
        }
        text = json.dumps(payload, indent=2)
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
        return text
