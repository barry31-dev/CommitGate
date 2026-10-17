"""Read the refs, commits and commit messages of one repository.

Everything here fails loudly. The failure this tool exists to prevent is an
identity being published because nobody looked, so "could not read this" must
never be reported as "read it and found nothing". Every read therefore returns
either parsed records or an error, and the checks turn any error into a finding.
"""

from __future__ import annotations

import os
import subprocess

from .models import Commit, Ref, Snapshot

# Record framing for `git log`. A commit message is multi-line, so neither
# line-splitting nor splitting on a single separator can find the boundary
# between one message and the next sha. The record terminator goes *before*
# each record because git appends its own newline after every formatted
# commit: used as a suffix it lands inside the next record's sha field.
# Both are literal placeholder strings, not the characters themselves: git
# expands `%x01` / `%x1f` in a --format, while Python's subprocess rejects an
# argument containing a real NUL byte ("ValueError: embedded null byte"), so
# `%x00` can be passed to git but the resulting byte cannot be used to split in
# Python without going through a pipe. Using two placeholders git expands, and
# splitting on the expanded characters, keeps one code path for both halves.
RECORD_SEP = "\x01"
FIELD_SEP = "\x1f"

LOG_FORMAT = "%x01%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B"

# Two commands, two placeholder dialects. `git log` expands `%x01` and `%x00`
# but prints `%09` literally; `git for-each-ref` expands `%09` and prints
# `%x01`/`%x00` literally. Getting this wrong produces one unparseable line
# rather than a fielded read, which is exactly the silent failure class the
# checks below are written to refuse.
REFS_FORMAT = "%(refname)%09%(objecttype)%09%(objectname)%09%(taggername)%09%(taggeremail)"


class ScanError(Exception):
    """Raised when the repository could not be read at all."""


def _run(args: list[str], cwd: str) -> str:
    try:
        proc = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True
        )
    except OSError as exc:
        raise ScanError("cannot run git: %s" % exc) from exc
    if proc.returncode != 0:
        raise ScanError("git %s failed (%d): %s" % (args[0], proc.returncode, (proc.stderr or proc.stdout).strip()[:200]))
    return proc.stdout


def is_repository(path: str) -> bool:
    """True only when git agrees this directory is inside a work tree."""
    if not os.path.isdir(path):
        return False
    try:
        out = _run(["rev-parse", "--is-inside-work-tree"], path)
    except ScanError:
        return False
    return out.strip() == "true"


def read_refs(repo: str) -> list[Ref]:
    """Every ref, including `refs/pull/*` and annotated tag objects."""
    out = _run(["for-each-ref", "--format=" + REFS_FORMAT], repo)
    refs: list[Ref] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 5:
            raise ScanError("cannot parse ref record (%d fields): %r" % (len(fields), line[:120]))
        name, objtype, sha, tagger_name, tagger_email = (f.strip() for f in fields)
        refs.append(
            Ref(
                name=name,
                sha=sha,
                kind=objtype,
                # git prints the literal placeholder for `%(taggername)` on a
                # lightweight tag; that means "no tagger", not "a tagger whose
                # name starts with %(".
                tagger_name=None if not tagger_name or tagger_name.startswith("%(") else tagger_name,
                tagger_email=None if not tagger_email or tagger_email.startswith("%(") else tagger_email,
            )
        )
    return refs


def read_commits(repo: str) -> list[Commit]:
    """Every commit reachable from any ref, with its author and committer."""
    out = _run(["log", "--all", "--date-order", "--format=" + LOG_FORMAT], repo)
    commits: list[Commit] = []
    for record in out.split(RECORD_SEP):
        if not record.strip():
            continue
        fields = record.split(FIELD_SEP)
        if len(fields) != 6:
            raise ScanError("cannot parse commit record (%d fields): %r" % (len(fields), record[:120]))
        sha, an, ae, cn, ce, message = (f.strip() for f in fields)
        commits.append(
            Commit(
                sha=sha,
                author_name=an,
                author_email=ae,
                committer_name=cn,
                committer_email=ce,
                message=message,
            )
        )
    return commits


def scan(repo: str) -> Snapshot:
    """Read the repository. Raises ScanError if it cannot be read."""
    if not is_repository(repo):
        raise ScanError("not a git work tree: %s" % repo)
    refs = read_refs(repo)
    commits = read_commits(repo)
    return Snapshot(refs=refs, commits=commits)
