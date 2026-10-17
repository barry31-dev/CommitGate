# Changelog

All notable changes to this package are recorded here. Nothing has been
released yet; this file starts at the first prepared version.

## Unreleased

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
