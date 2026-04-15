"""JUnit XML reporter — consumed by CI test-publish actions."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from ..report import CheckStatus, Report


class JunitReporter:
    def render(self, report: Report, out: Path | None = None, suite: str = "mcpcheck") -> str:
        testsuite = ET.Element(
            "testsuite",
            {
                "name": suite,
                "tests": str(report.total),
                "failures": str(report.failed),
                "skipped": str(report.skipped),
            },
        )
        for c in report.checks:
            tc = ET.SubElement(
                testsuite,
                "testcase",
                {
                    "classname": c.tool,
                    "name": c.check,
                    "time": f"{(c.latency_ms or 0) / 1000:.3f}",
                },
            )
            if c.status is CheckStatus.FAIL:
                ET.SubElement(tc, "failure", {"message": c.message or "failed"}).text = c.message
            elif c.status is CheckStatus.SKIP:
                ET.SubElement(tc, "skipped", {"message": c.message or "skipped"})

        suites = ET.Element("testsuites")
        suites.append(testsuite)
        ET.indent(suites, space="  ")
        text = ET.tostring(suites, encoding="unicode", xml_declaration=True)
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
        return text
