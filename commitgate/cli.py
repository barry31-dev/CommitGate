"""Command line entry point.

Exit codes, and why there are three:

  0  a report was produced and nothing but `info` was found;
  1  at least one error or warning was found -- do not push;
  2  the repository could not be read, or the policy could not be loaded.

2 is separate from 1 on purpose. "Your history has a foreign identity" and
"this tool never managed to read your history" are different facts, and a
caller that treats a failed read as a clean run publishes an identity it never
looked at. That is the one outcome a gate must never produce.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import checks, report
from .models import Policy
from .scanner import ScanError, scan

DEFAULT_MESSAGE_PATTERN = ""


def load_policy(path: str | None, allow: list[str]) -> Policy:
    """Build the policy from --allow pairs, or from a file if one is given.

    The file form is plain lines of `Name <email>` so a policy can be reviewed
    without running anything and kept in the repository it protects.
    """
    pairs: list[tuple[str, str]] = []
    if path:
        if not os.path.isfile(path):
            raise SystemExit("commitgate: policy file not found: %s" % path)
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, email = line.partition("<")
                pairs.append((name.strip(), email.strip("> ").strip()))
    for item in allow:
        name, _, email = item.partition("<")
        pairs.append((name.strip(), email.strip("> ").strip()))
    if not pairs:
        raise SystemExit(
            "commitgate: no allowed identity given; pass --allow 'Name <email>' "
            "or --policy FILE. Refusing to run with an empty policy, because a "
            "gate with no policy reports clean about nothing."
        )
    return Policy(allowed=tuple(pairs), message_pattern=DEFAULT_MESSAGE_PATTERN)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="commitgate",
        description="Check who a repository says published it, before you push.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="repository to check")
    parser.add_argument("--allow", action="append", default=[],
                        help="an allowed publisher, as 'Name <email>'; repeatable")
    parser.add_argument("--policy", default=None,
                        help="file of 'Name <email>' lines, one per line")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", default="", help="write here instead of stdout")
    args = parser.parse_args(argv)

    policy = load_policy(args.policy, args.allow)

    try:
        snapshot = scan(args.repo)
    except ScanError as exc:
        print("commitgate: %s" % exc, file=sys.stderr)
        return 2

    findings = checks.run_all(snapshot, policy)
    text = (
        report.render_json(findings, snapshot.commit_count)
        if args.format == "json"
        else report.render_markdown(findings, snapshot.commit_count)
    )

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            print("commitgate: cannot write %s: %s" % (args.output, exc), file=sys.stderr)
            return 3
    else:
        print(text, end="")

    if any(f.severity in ("error", "warning") for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
