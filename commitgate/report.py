"""Markdown and JSON rendering. Rendering only; no judgement happens here."""

from __future__ import annotations

import json
from collections import Counter

from .checks import CHECK_NAMES
from .models import Finding


def _cell(text: str) -> str:
    """Spell one value for a Markdown table cell.

    A `|` inside a cell ends it early and shifts every later column, and a raw
    newline ends the row. Both can reach here through an identity the operator
    controls, so they are escaped rather than trusted to stay table-safe.
    """
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(findings: list[Finding], commit_count: int) -> str:
    lines = ["# CommitGate report", ""]
    lines.append("Commits checked: %d" % commit_count)
    lines.append("Findings: %d" % len(findings))
    lines.append("")

    # The report names the checks it ran, not only the ones that fired. A report
    # that lists findings alone cannot be read as evidence: with zero findings
    # it is indistinguishable from a report where no check ran at all.
    lines.append("Checks run (%d): %s" % (len(CHECK_NAMES), ", ".join(CHECK_NAMES)))
    lines.append("")

    counts = Counter(f.severity for f in findings)
    for severity in ("error", "warning", "info"):
        if counts.get(severity):
            lines.append("- %s: %d" % (severity, counts[severity]))
    lines.append("")

    lines.append("| severity | check | ids | detail |")
    lines.append("|---|---|---|---|")
    for finding in findings:
        ids = ", ".join(finding.ids) or "-"
        lines.append(
            "| %s | %s | %s | %s |" % (
                _cell(finding.severity), _cell(finding.check),
                _cell(ids), _cell(finding.detail))
        )
    lines.append("")
    lines.append(
        "A clean report means every reachable commit and tag was read and "
        "matched the policy. It does not mean the repository is ready to "
        "publish."
    )
    return "\n".join(lines) + "\n"


def render_json(findings: list[Finding], commit_count: int) -> str:
    payload = {
        "commit_count": commit_count,
        "finding_count": len(findings),
        "checks_run": list(CHECK_NAMES),
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
