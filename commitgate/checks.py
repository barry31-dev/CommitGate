"""The checks a repository must pass before it is published.

Each check exists because of a measured failure, not a hypothetical one. The
docstring of each function records what was observed and what the check does
and does not prove.
"""

from __future__ import annotations

import re

from .models import ERROR, INFO, WARNING, Finding, Policy, Snapshot

CHECK_NAMES = (
    "identity-author",
    "identity-committer",
    "identity-tagger",
    "commit-message",
    "reachability",
)


def check_author(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """Every commit's author must be on the allowed list.

    Why this check exists: a public repository was found with six commits
    authored by one personal identity and a seventh by a second, while the same
    tree's file contents scanned clean. Content scans do not read the author
    field, so no content gate could have caught it.
    """
    findings = []
    for commit in snapshot.commits:
        if not policy.matches(commit.author_name, commit.author_email):
            findings.append(
                Finding(
                    check="identity-author",
                    severity=ERROR,
                    ids=(commit.sha[:12],),
                    detail="author %s <%s> is not an allowed publisher" % (
                        commit.author_name, commit.author_email),
                )
            )
    return findings


def check_committer(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """Every commit's committer must be on the allowed list.

    Checked separately from the author because `--amend` without
    `--reset-author` keeps the previous author and only rewrites the committer,
    so a tool that pins one field can still publish the other. Pinning both and
    checking both is what makes "the identity was pinned" a claim about the
    commit rather than about one of its two records.
    """
    findings = []
    for commit in snapshot.commits:
        if not policy.matches(commit.committer_name, commit.committer_email):
            findings.append(
                Finding(
                    check="identity-committer",
                    severity=ERROR,
                    ids=(commit.sha[:12],),
                    detail="committer %s <%s> is not an allowed publisher" % (
                        commit.committer_name, commit.committer_email),
                )
            )
    return findings


def check_tagger(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """Every annotated tag's tagger must be on the allowed list.

    Why this is not covered by the commit checks: an annotated tag is its own
    object with its own tagger identity, published alongside the release. Five
    annotated tags on a public repository carried a real name as tagger while
    every commit on `main` had already been rewritten to the organisation
    identity -- rewriting commits does not touch tag objects.
    """
    findings = []
    for ref in snapshot.refs:
        if ref.kind != "tag" or ref.tagger_name is None:
            continue
        # `%(taggeremail)` already renders wrapped in angle brackets; strip them
        # once here so the detail line does not print <<...>>.
        email = (ref.tagger_email or "").strip("<>")
        if not policy.matches(ref.tagger_name, email):
            findings.append(
                Finding(
                    check="identity-tagger",
                    severity=ERROR,
                    ids=(ref.name,),
                    detail="tagger %s <%s> is not an allowed publisher" % (
                        ref.tagger_name, email),
                )
            )
    return findings


def check_messages(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """No commit message may contain the internal-context pattern.

    Why the whole history and not a recent slice: a public repository carried
    an internal project name in the message of the commit at `HEAD~6`. A
    "last N commits" window silently truncates the range it reports on, so the
    count in the report would not describe what was actually read.
    """
    if not policy.message_pattern:
        return []
    pattern = re.compile(policy.message_pattern, re.I)
    findings = []
    for commit in snapshot.commits:
        if pattern.search(commit.message):
            findings.append(
                Finding(
                    check="commit-message",
                    severity=WARNING,
                    ids=(commit.sha[:12],),
                    detail="message matches the internal-context pattern",
                )
            )
    return findings


def check_reachability(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """Report how much was read, so a zero-finding report is not empty.

    A report that says "no findings" without saying how many commits were read
    is indistinguishable from a run that read nothing. This check always
    produces one info finding and is what makes the other four falsifiable.
    """
    pull_refs = [r for r in snapshot.refs if r.name.startswith("refs/pull/")]
    return [
        Finding(
            check="reachability",
            severity=INFO,
            ids=(),
            detail="read %d commit(s) across %d ref(s), %d of them refs/pull/*" % (
                snapshot.commit_count, len(snapshot.refs), len(pull_refs)),
        )
    ]


def run_all(snapshot: Snapshot, policy: Policy) -> list[Finding]:
    """Every check, in a fixed order so two runs render identically."""
    findings: list[Finding] = []
    findings += check_author(snapshot, policy)
    findings += check_committer(snapshot, policy)
    findings += check_tagger(snapshot, policy)
    findings += check_messages(snapshot, policy)
    findings += check_reachability(snapshot, policy)
    return findings
