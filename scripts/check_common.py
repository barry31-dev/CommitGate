#!/usr/bin/env python3
"""Helpers shared by the CI guard scripts.

Only `git`, `tempfile` and `subprocess` are used, so these helpers run on every
Python the matrix covers without adding a dependency.
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


def run_cli(root, repo, commits=1, *extra):
    """Run the CLI against a repository, with the shared allow-list."""
    return subprocess.run(
        [sys.executable, "-m", "commitgate", repo,
         "--allow", "publisher <%s>" % ALLOWED_EMAIL, *extra],
        capture_output=True, text=True, cwd=root,
    )
