"""Code-level test cases for the CommitGate checks.

Each docstring records the input, the branch taken, the expected assertion and
what the case does NOT prove. `from __future__ import annotations` keeps the
PEP 585 subscripts in these signatures from being evaluated at import time, so
the suite collects on Python 3.8 like the package itself does.

These cases build real throwaway repositories rather than mocking git. The
tool's whole claim is about what git records, and a mock of git would only
prove the code agrees with itself.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

import pytest

from commitgate import checks, cli, report, scanner
from commitgate.models import Policy

ALLOWED = "publisher@users.noreply.github.com"
BARRY = {
    "GIT_AUTHOR_NAME": "publisher", "GIT_AUTHOR_EMAIL": ALLOWED,
    "GIT_COMMITTER_NAME": "publisher", "GIT_COMMITTER_EMAIL": ALLOWED,
}
# The negative case is a plausible personal identity, deliberately generic: a
# public package must not ship a real person's name or address as a fixture,
# even to illustrate the failure it prevents. What matters to the assertions is
# only that it is NOT on the allow-list.
LEAKY = {
    "GIT_AUTHOR_NAME": "Ada Lovelace", "GIT_AUTHOR_EMAIL": "ada@example.com",
    "GIT_COMMITTER_NAME": "Ada Lovelace", "GIT_COMMITTER_EMAIL": "ada@example.com",
}


def git(repo: str, *args: str, env: dict | None = None) -> None:
    merged = dict(os.environ, **(env or BARRY))
    subprocess.run(["git", "-C", repo, *args], check=True,
                   capture_output=True, text=True, env=merged)


def make_repo(commits: int = 1, env: dict | None = None) -> str:
    repo = tempfile.mkdtemp(prefix="cg-test-")
    git(repo, "init", "-q", "-b", "main")
    for i in range(commits):
        with open(os.path.join(repo, "f%d.txt" % i), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "commit %d" % i, env=env)
    return repo


def policy(pattern: str = "") -> Policy:
    return Policy(allowed=(("publisher", ALLOWED),), message_pattern=pattern)


def run_cli(repo: str, *extra: str):
    return subprocess.run(
        ["python3", "-m", "commitgate", repo, "--allow", "publisher <%s>" % ALLOWED, *extra],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )


# --- scanner -----------------------------------------------------------------

def test_clean_repo_scans_with_no_identity_findings():
    """Input: two commits by the allowed identity. Expected: zero identity findings.

    Does not prove the repository is safe to publish; only that every reachable
    commit was read and matched.
    """
    snapshot = scanner.scan(make_repo(2))
    assert snapshot.commit_count == 2
    assert checks.check_author(snapshot, policy()) == []
    assert checks.check_committer(snapshot, policy()) == []


def test_reachability_finding_reports_how_much_was_read():
    """A zero-finding report must say how much was read.

    Without this, "no findings" is indistinguishable from "read nothing".
    """
    snapshot = scanner.scan(make_repo(3))
    found = checks.check_reachability(snapshot, policy())
    assert len(found) == 1
    assert "read 3 commit(s)" in found[0].detail


def test_pull_ref_commits_are_read_even_when_not_on_main():
    """Input: a leaky commit reachable only through `refs/pull/2/head`.

    This is the case a history rewrite cannot fix: the commit is off `main` but
    still reachable, and therefore still published. Expected: reported.
    Does not prove the remote keeps the ref forever -- that is GitHub behaviour
    observed once, not a guarantee.
    """
    repo = make_repo(1)
    with open(os.path.join(repo, "pr.txt"), "w", encoding="utf-8") as fh:
        fh.write("y\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "on the pr branch", env=LEAKY)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    git(repo, "update-ref", "refs/pull/2/head", sha)
    git(repo, "reset", "-q", "--hard", "HEAD~1")

    main_shas = subprocess.run(["git", "-C", repo, "log", "main", "--format=%H"],
                               capture_output=True, text=True).stdout.split()
    assert sha not in main_shas, "leak must be off main for this case to mean anything"

    findings = checks.check_author(scanner.scan(repo), policy())
    assert len(findings) == 1
    assert findings[0].ids[0] == sha[:12]


def test_annotated_tag_tagger_is_checked_separately():
    """Input: commits fully clean, one annotated tag tagged by a foreign identity.

    Proves the tagger is its own field: rewriting commits leaves tag objects
    untouched, which is what made the 2026-10-09 rewrite insufficient.
    """
    repo = make_repo(1)
    subprocess.run(["git", "-C", repo, "tag", "-a", "v0.1", "-m", "m"], check=True,
                   capture_output=True, text=True, env=dict(os.environ, **LEAKY))
    snapshot = scanner.scan(repo)
    assert checks.check_author(snapshot, policy()) == []
    tagger_findings = checks.check_tagger(snapshot, policy())
    assert len(tagger_findings) == 1
    assert tagger_findings[0].ids == ("refs/tags/v0.1",)
    assert "<" in tagger_findings[0].detail and "<<" not in tagger_findings[0].detail


def test_lightweight_tag_has_no_tagger_and_is_not_a_finding():
    """A lightweight tag carries no tagger object; it must not be reported."""
    repo = make_repo(1)
    subprocess.run(["git", "-C", repo, "tag", "v0.1"], check=True,
                   capture_output=True, text=True, env=dict(os.environ, **BARRY))
    assert checks.check_tagger(scanner.scan(repo), policy()) == []


def test_message_check_scans_the_whole_history_not_a_recent_window():
    """Input: the pattern appears in the OLDEST commit, not a recent one.

    A "last N commits" window would miss this, and the report would still claim
    to have checked. Expected: reported.
    """
    repo = make_repo(1)
    git(repo, "commit", "-q", "--amend", "-m", "mentions InternalProjectX", env=BARRY)
    for i in range(8):
        with open(os.path.join(repo, "g%d.txt" % i), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "clean follow-up %d" % i, env=BARRY)
    findings = checks.check_messages(scanner.scan(repo), policy("InternalProjectX"))
    assert len(findings) == 1


def test_unreadable_repository_raises_rather_than_reporting_clean():
    """A path that is not a repository is a read failure, not a clean result."""
    with pytest.raises(scanner.ScanError):
        scanner.scan(tempfile.mkdtemp(prefix="cg-none-"))


# --- CLI contract ------------------------------------------------------------

def test_clean_repository_exits_zero():
    assert run_cli(make_repo(2)).returncode == 0


def test_foreign_identity_exits_one():
    assert run_cli(make_repo(1, env=LEAKY)).returncode == 1


def test_unreadable_repository_exits_two():
    """Exit 2 must never collapse into 0: a failed read is not a clean run."""
    result = run_cli(tempfile.mkdtemp(prefix="cg-cli-none-"))
    assert result.returncode == 2
    assert "not a git work tree" in result.stderr


def test_empty_policy_is_refused():
    """A gate with no policy would report clean about nothing; refuse instead."""
    repo = make_repo(1)
    result = subprocess.run(["python3", "-m", "commitgate", repo],
                            capture_output=True, text=True,
                            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert result.returncode != 0
    assert "no allowed identity" in result.stderr


def test_json_output_has_the_expected_contract():
    """The JSON shape is what a CI job asserts against, so it is pinned."""
    result = run_cli(make_repo(2), "--format", "json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["commit_count"] == 2
    assert payload["checks_run"] == list(checks.CHECK_NAMES)
    assert payload["finding_count"] == len(payload["findings"])


def test_policy_file_is_accepted_and_comments_ignored():
    repo = make_repo(1)
    path = os.path.join(repo, "policy.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# allowed publishers\npublisher <%s>\n" % ALLOWED)
    result = subprocess.run(
        ["python3", "-m", "commitgate", repo, "--policy", path],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert result.returncode == 0


# --- report ------------------------------------------------------------------

def test_markdown_escapes_pipe_and_newline_in_identities():
    """An identity is operator-controlled text; a `|` would shift the table.

    Does not prove every control character is handled -- only the two that
    break a Markdown table row.
    """
    from commitgate.models import Finding
    finding = Finding(check="identity-author", severity="error",
                      ids=("abc",), detail="author bad|name <a@b>\nsecond line")
    text = report.render_markdown([finding], 1)
    assert "\\|" in text
    assert "\nsecond line" not in text
