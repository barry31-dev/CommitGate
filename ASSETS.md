# Asset manifest

> Zero external assets. Every file in this package was authored for it.
> Counts below come from the same walk `scripts/ci_check_tree.py` performs, so
> the manifest and the tree are checked against each other rather than copied
> by hand.

## Scope

This manifest covers the **release tree only**: `commitgate/`, `fixtures/`,
`scripts/`, `tests/`, `.github/`, `README.md`, `README.zh-CN.md`,
`CHANGELOG.md`, `RELEASE_NOTES.md`, `ASSETS.md`, `requirements-dev.txt` and
`LICENSE`.

`Docs/` is **not** part of the release tree. Neither is `.venv/`: it is a local
virtualenv used to run the suite, not something that ships.

## Inventory (remeasured 2026-10-10)

21 files, 5 extensions:

| Kind | Count | Encoding |
|---|---|---|
| Python (`.py`) | 12 | ASCII |
| Markdown (`.md`) | 6 | UTF-8; `README.zh-CN.md` is the only one with non-ASCII bytes, by design |
| YAML (`.yml`) | 1 | ASCII |
| Text (`.txt`) | 1 | ASCII |
| License (no extension) | 1 | ASCII |

The counts in this table are re-checked on every CI run. A manifest row that
disagrees with the tree is a hard failure, because a number a reader cannot
verify is not evidence.

## Excluded

| Path | Why |
|---|---|
| `Docs/` | internal review notes; not published |
| `.venv/` | local virtualenv |
| `__pycache__/`, `*.pyc` | build artefacts |

## Clean-room

The published tree is scanned on every CI run for internal context
(`scripts/ci_check_tree.py`), including hidden files, because `rg` skips
dot-prefixed paths by default and `.github/` is part of the tree.

Two words are deliberately not treated as internal context, and both are
documented in the scanner rather than silently excluded:

- the GitHub handle this package is published under, which appears in the
  example policy by design;
- `scripts/ci_check_tree.py`, the file carrying the word list as source text,
  so the scan would otherwise report a hit on itself.
