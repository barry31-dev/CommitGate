# Changelog

All notable changes to this package are recorded here, starting at the
first published version.

## [0.1.0] - 2026-10-17

First published release: `github.com/barry31-dev/CommitGate` at tag `v0.1`.
Everything below was written while the release was still being prepared; it is
the content of `v0.1`, not a description of work that has not happened.

### Added

- `identity-author`, `identity-committer` and `identity-tagger` checks over
  every reachable ref, including `refs/pull/*`.
- `commit-message` check over the whole history rather than a recent window.
- `reachability`, an always-present `info` finding that states how many commits
  and refs were read, so an empty report is not ambiguous.
- Markdown and JSON output, and the four-code exit contract (0 clean,
  1 findings, 2 unreadable, 3 undeliverable).
- `--allow` and `--policy` for the publisher allow-list.
- CI workflow `commitgate-ci` on Python 3.12 and 3.8, plus the three guard
  scripts it calls.
