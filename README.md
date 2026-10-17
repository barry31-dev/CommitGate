# CommitGate

> **Status: not published.** This repository is being prepared for a first
> public release. Read-only, standard library only, no network access.

## The problem it exists for

File scanners do not read your git author field.

A repository can pass a content scan with zero hits while its history says who
really wrote it. That is not a theoretical concern: it was measured on a public
repository where

- 6 of 12 commits had `author` **and** `committer` set to a personal identity,
- 1 more used a second personal identity,
- all 5 annotated tags carried that same identity as `tagger`,

while the same tree's file contents and commit messages scanned clean. Every
gate on that repository read files. None of them read the author field, so none
of them could have caught it.

Two properties make this worse than a tidy-up:

- **Rewriting history does not fix it.** A pull request head ref
  (`refs/pull/2/head`) keeps its commits reachable after the branch that
  introduced them is rewritten. A leak published through a PR survives a
  rewrite of `main`.
- **An annotated tag is a second surface.** A tag object carries its own
  `tagger` identity. Rewriting commits leaves tag objects untouched, so a clean
  `main` can still publish a tag signed by the wrong person.

The only moment this can be stopped is **before the push**.

## What it does

`commitgate` reads every ref and every reachable commit in a repository and
reports each one whose `author`, `committer`, or annotated-tag `tagger` is not
on an allow-list you provide. It also scans every commit message against an
optional internal-context pattern.

```bash
python3 -m commitgate . --allow "you <you@users.noreply.github.com>"
```

Run it from the repository root; the package is imported from source and is not
installed. Output is Markdown by default, JSON with `--format json`.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | a report was produced and nothing but `info` was found |
| `1` | at least one error or warning was found, so **do not push** |
| `2` | the repository could not be read, or the policy was missing |
| `3` | the report was computed but could not be written to `--output` |

`2` is separate from `1` on purpose. "Your history contains a foreign identity"
and "this tool never managed to read your history" are different facts. A caller
that treats a failed read as a clean run publishes an identity it never looked
at, which is the one outcome a gate must never produce.

## Checks

| Check | What it reports |
|---|---|
| `identity-author` | a commit whose `author` is not on the allow-list |
| `identity-committer` | a commit whose `committer` is not on the allow-list |
| `identity-tagger` | an annotated tag whose `tagger` is not on the allow-list |
| `commit-message` | a commit message matching the internal-context pattern |
| `reachability` | always reports how many commits and refs were read |

The last one is not a courtesy. A report that says "no findings" without saying
how much was read is indistinguishable from a run that read nothing.

## Why author and committer are checked separately

`git commit --amend` without `--reset-author` keeps the previous **author** and
rewrites only the **committer**. A tool that pins one of the two fields can
still publish the other. CommitGate checks both.

Related, and worth knowing if you are writing your own gate: git resolves
identity from the `GIT_AUTHOR_NAME` / `GIT_COMMITTER_NAME` environment
variables **before** it reads `user.name` from config. Passing
`-c user.name=...` alone does not protect you against an inherited environment
variable; both channels have to be pinned.

## The policy

An allow-list of `Name <email>` pairs, supplied either by repeating `--allow`
or by a file passed to `--policy`:

```
# allowed publishers
you <you@users.noreply.github.com>
```

There is no "probably fine" tier. An identity that is not on the list is a
finding, because the failure this tool exists to catch is an identity the author
did not realise was being published.

Running with an empty policy is refused outright rather than reporting clean
about nothing.

## Requirements

Python 3, standard library only. No third-party packages, no network access, no
credentials, no database. `pytest` is needed only to run the test suite.

## Verified

Measured on 2026-10-10, CPython 3.14.3:

- the 14-case suite passes;
- a leak reachable only through `refs/pull/2/head`, with `main` clean, is
  reported and exits 1;
- commits fully clean with one annotated tag tagged by a foreign identity is
  reported and exits 1;
- a leak in the oldest commit's message, under eight clean commits, is reported
  (so the message scan is not a recent window);
- a directory that is not a repository exits 2, not 0;
- the tree check was given a real internal-context word and turned red, then
  turned green again once it was removed.

## Not verified

- **Python 3.8 and 3.12 have not been run here.** They are the versions the CI
  matrix covers; on the machine this was written on only 3.14.3 and 3.9.6
  (the latter without pytest) were available. Treat "works on 3.8" as untested
  until CI reports it.
- **Not run against a real public repository end to end.** Every case above is
  a throwaway repository built for the test.
- **No remotes are contacted.** The tool reads local refs only. Whether a given
  host keeps `refs/pull/*` forever is a hosting behaviour, not something this
  tool can guarantee.

## Not included

- It does not rewrite history. Rewriting published history is an owner
  decision, and doing it silently is how a leak becomes unrecoverable.
- It does not check file contents. Use a content scanner for that; this tool
  looks at the one field content scanners do not read.
- It does not know about hosting providers, accounts, or permissions.
