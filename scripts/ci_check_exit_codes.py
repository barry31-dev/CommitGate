#!/usr/bin/env python3
"""Assert the exit-code contract against real throwaway repositories.

Run:  python3 scripts/ci_check_exit_codes.py .

The point is that the four codes are four different facts. A caller that
collapses "could not read" into "nothing found" publishes an identity it never
looked at, so that collapse has to turn the job red rather than pass quietly.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ALLOWED_EMAIL = "publisher@users.noreply.github.com"
BARRY = {
    "GIT_AUTHOR_NAME": "publisher", "GIT_AUTHOR_EMAIL": ALLOWED_EMAIL,
    "GIT_COMMITTER_NAME": "publisher", "GIT_COMMITTER_EMAIL": ALLOWED_EMAIL,
}
FOREIGN = {
    "GIT_AUTHOR_NAME": "Ada Lovelace", "GIT_AUTHOR_EMAIL": "ada@example.com",
    "GIT_COMMITTER_NAME": "Ada Lovelace", "GIT_COMMITTER_EMAIL": "ada@example.com",
}


def git(repo, *args, env=None):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                   text=True, env=dict(os.environ, **(env or BARRY)))


def make_repo(commits=1, env=None):
    repo = tempfile.mkdtemp(prefix="cg-ci-")
    git(repo, "init", "-q", "-b", "main")
    for i in range(commits):
        with open(os.path.join(repo, "f%d.txt" % i), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "c%d" % i, env=env)
    return repo


def run(root, *args):
    return subprocess.run(
        [sys.executable, "-m", "commitgate", *args],
        capture_output=True, text=True, cwd=root,
    )


def main(root: str) -> int:
    failures = []

    clean = make_repo(2)
    got = run(root, clean, "--allow", "publisher <%s>" % ALLOWED_EMAIL)
    if got.returncode != 0:
        failures.append("clean repository: expected exit 0, got %d (%s)"
                        % (got.returncode, got.stderr[:120]))

    foreign = make_repo(1, env=FOREIGN)
    got = run(root, foreign, "--allow", "publisher <%s>" % ALLOWED_EMAIL)
    if got.returncode != 1:
        failures.append("foreign identity: expected exit 1, got %d" % got.returncode)

    # A directory that is not a repository must not be reported as clean.
    got = run(root, tempfile.mkdtemp(prefix="cg-ci-none-"),
              "--allow", "publisher <%s>" % ALLOWED_EMAIL)
    if got.returncode != 2:
        failures.append("unreadable repository: expected exit 2, got %d" % got.returncode)

    # An empty policy must be refused, not reported clean about nothing.
    got = subprocess.run([sys.executable, "-m", "commitgate", make_repo(1)],
                         capture_output=True, text=True, cwd=root)
    if got.returncode == 0:
        failures.append("empty policy: expected a refusal, got exit 0")

    if failures:
        print("FAIL exit-code contract")
        for line in failures:
            print("  - " + line)
        return 1
    print("exit-code contract: 0 / 1 / 2 all reached, empty policy refused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
