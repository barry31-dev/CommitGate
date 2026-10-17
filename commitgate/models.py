"""Data shapes shared by the scanner, checks and reporters."""

from __future__ import annotations

from dataclasses import dataclass

ERROR = "error"
WARNING = "warning"
INFO = "info"


@dataclass(frozen=True)
class Ref:
    """One reachable ref and what it points at.

    `refs/pull/*` is included on purpose: a pull request head ref keeps its
    commits reachable on the remote after the branch that introduced them is
    rewritten, so a history rewrite on `main` cannot remove an identity that
    was published through a PR. That was measured, not assumed.
    """

    name: str
    sha: str
    kind: str
    tagger_name: str | None = None
    tagger_email: str | None = None


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message: str


@dataclass(frozen=True)
class Finding:
    """One reported problem, tagged with the check that produced it.

    `check` is part of the payload because a report that lists findings alone
    cannot be read as evidence: with zero findings it is indistinguishable from
    a run in which nothing was checked.
    """

    check: str
    severity: str
    ids: tuple[str, ...]
    detail: str

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "ids": list(self.ids),
            "detail": self.detail,
        }


@dataclass
class Snapshot:
    """Everything the checks see: the refs and commits of one repository."""

    refs: list[Ref]
    commits: list[Commit]

    @property
    def commit_count(self) -> int:
        return len(self.commits)


@dataclass
class Policy:
    """What counts as an acceptable publisher identity.

    `allowed` holds (name, email) pairs and anything else is a finding. There
    is no "probably fine" tier, because the failure this tool exists to catch
    is an identity the author did not realise was being published.
    """

    allowed: tuple[tuple[str, str], ...]
    message_pattern: str = ""

    def matches(self, name: str, email: str) -> bool:
        return (name, email) in self.allowed
