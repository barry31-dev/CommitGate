#!/usr/bin/env python3
"""Assert that a clean scan says how much it read, in both output formats.

Run:  python3 scripts/ci_check_report.py .

Why this is a hard check: the one report that must not be trustworthy is the
empty one. "No findings" without a count is indistinguishable from a run that
read nothing, and that ambiguity is exactly what let an identity leak stand.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from check_common import make_repo, run_cli

ALLOWED_EMAIL = "publisher@users.noreply.github.com"


def main(root: str) -> int:
    failures = []
    repo = make_repo(3)

    got = run_cli(root, repo, 3)
    if got.returncode != 0:
        failures.append("clean repository: expected exit 0, got %d (%s)"
                        % (got.returncode, got.stderr[:120]))
        print("FAIL report contract")
        for line in failures:
            print("  - " + line)
        return 1

    if "read 3 commit(s)" not in got.stdout:
        failures.append("markdown report does not state how many commits were read")

    out = os.path.join(tempfile.mkdtemp(prefix="cg-ci-out-"), "report.json")
    got_json = run_cli(root, repo, 3, "--format", "json", "--output", out)
    if got_json.returncode != 0:
        failures.append("json output: expected exit 0, got %d" % got_json.returncode)
    else:
        payload = json.load(open(out, encoding="utf-8"))
        if payload.get("commit_count") != 3:
            failures.append("json commit_count: expected 3, got %r" % payload.get("commit_count"))
        reachability = [f for f in payload["findings"] if f["check"] == "reachability"]
        if len(reachability) != 1:
            failures.append("json must carry exactly one reachability finding, got %d"
                            % len(reachability))
        if "reachability" not in payload.get("checks_run", []):
            failures.append("reachability is missing from checks_run")

    if failures:
        print("FAIL report contract")
        for line in failures:
            print("  - " + line)
        return 1
    print("report contract: markdown and json both state what was read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
