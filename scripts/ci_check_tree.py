#!/usr/bin/env python3
"""Audit the shipped tree: counts, encodings, and the clean-room word list.

Run:  python3 scripts/ci_check_tree.py .

Hard failures are facts that make the published package wrong. The word list is
the important one: this package exists to stop internal context being published,
so it must not itself contain any.

`--hidden` is not optional here. `rg` skips dot-prefixed paths by default, so
once `.github/` is part of the tree a scan without it would skip exactly the
directory it was added to cover, and would print "0 hits" about files it never
read.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

# Words that must never appear in the published package.
#
# `barry31-dev` is deliberately NOT on this list. It is the public GitHub
# handle this package is published under, and it appears in the README, the
# allow-list fixture and the CI policy by design. The internal word list that
# carries it is about the SSH alias `github-barry` and the account's other
# identities, which do not occur here. Copying that list verbatim made the scan
# fire on the package's own example policy, which is a scanner reporting a hit
# on itself rather than on internal context.
CLEANROOM_PATTERN = "|".join((
    "mywork", "desktop/lx", "/Users/", "lx-m2", "lx-m3",
    "github-barry", "automation_id", "qwen3", "hy4",
    "deepseek", "gpt-6", "steadywork",
))

# Directories that are never part of the release tree.
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "Docs"}


def walk_files(root: str) -> list[str]:
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in files:
            if name.endswith(".pyc"):
                continue
            found.append(os.path.relpath(os.path.join(base, name), root))
    return sorted(found)


def main(root: str) -> int:
    failures = []

    files = walk_files(root)
    if not files:
        print("FAIL published tree: no files found under %s" % root)
        return 1

    # Counts are a hard failure against ASSETS.md when it exists: a manifest
    # that disagrees with the tree is a claim the reader cannot check.
    assets = os.path.join(root, "ASSETS.md")
    if os.path.isfile(assets):
        text = open(assets, encoding="utf-8").read()
        match = re.search(r"^(\d+) files?, (\d+) extensions?[.:]", text, re.M)
        if match:
            declared_files, declared_exts = int(match.group(1)), int(match.group(2))
            exts = {os.path.splitext(f)[1] or "(none)" for f in files}
            if declared_files != len(files) or declared_exts != len(exts):
                failures.append(
                    "ASSETS.md says %d files / %d extensions, the walk found %d / %d"
                    % (declared_files, declared_exts, len(files), len(exts)))

    if shutil.which("rg") is None:
        failures.append("rg not found -- cannot run the clean-room scan, "
                        "refusing to call the tree clean")
    else:
        # This file carries the pattern as source text, so the scan matches
        # itself. That is a scanner reporting on its own word list rather than
        # on internal context, so it is excluded explicitly -- and noted here,
        # because an exclusion with no reason is how a real hit gets ignored.
        proc = subprocess.run(
            ["rg", "-l", "-i", "--hidden", "-g", "!.git/**", "-g", "!.venv/**",
             "-g", "!scripts/ci_check_tree.py", CLEANROOM_PATTERN, root],
            capture_output=True, text=True)
        hits = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        if proc.returncode >= 2:
            failures.append("rg exited %d (error, not 'no match'): %s"
                            % (proc.returncode, proc.stderr.strip()[:160]))
        elif hits:
            failures.append("clean-room scan hits: %s" % "; ".join(hits[:6]))

    non_ascii = []
    for rel in files:
        path = os.path.join(root, rel)
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        # `README.zh-CN.md` is the one text file expected to be non-ASCII: the
        # package ships an English and a Chinese README side by side, and the
        # Chinese one cannot be written in ASCII. Excluding it by name rather
        # than by extension keeps the check meaningful for every other file.
        if rel == "README.zh-CN.md":
            continue
        if rel.endswith((".md", ".txt", ".py", ".yml")):
            if any(b > 127 for b in data):
                non_ascii.append(rel)
    if non_ascii:
        failures.append("non-ASCII bytes in text files: %s" % ", ".join(non_ascii[:6]))

    if failures:
        print("FAIL published tree")
        for line in failures:
            print("  - " + line)
        return 1
    print("published tree: %d files, %d extensions, clean-room scan 0 hits"
          % (len(files), len({os.path.splitext(f)[1] or "(none)" for f in files})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
