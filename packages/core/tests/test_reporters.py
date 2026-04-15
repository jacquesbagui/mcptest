import json
from xml.etree import ElementTree as ET

from mcpact.report import CheckResult, CheckStatus, Report
from mcpact.reporter import HtmlReporter, JsonReporter, JunitReporter


def _report() -> Report:
    r = Report()
    r.add(CheckResult("echo", "exists", CheckStatus.PASS))
    r.add(CheckResult("echo", "call#1.status", CheckStatus.FAIL, "bad", latency_ms=42.0))
    r.add(CheckResult("ghost", "exists", CheckStatus.SKIP, "absent"))
    return r


def test_json_reporter_roundtrip() -> None:
    payload = json.loads(JsonReporter().render(_report()))
    assert payload["total"] == 3
    assert payload["failed"] == 1
    assert payload["ok"] is False
    assert payload["checks"][1]["latency_ms"] == 42.0


def test_junit_reporter_produces_valid_xml() -> None:
    xml_text = JunitReporter().render(_report())
    root = ET.fromstring(xml_text)
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.attrib["failures"] == "1"
    failure = suite.find("./testcase[@name='call#1.status']/failure")
    assert failure is not None
    assert failure.attrib["message"] == "bad"


def test_html_reporter_escapes_and_renders() -> None:
    r = Report()
    r.add(CheckResult("<evil>", "exists", CheckStatus.FAIL, "oops <script>"))
    html = HtmlReporter().render(r)
    assert "&lt;evil&gt;" in html
    assert "<script>" not in html  # escaped
