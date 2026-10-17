# CommitGate release notes

**v0.1 is published** (2026-10-17, `github.com/barry31-dev/CommitGate`, tag
`v0.1`). The feature set is frozen at what this repository ships: new requests
go to the `v0.2` backlog, and `v0.1` accepts only documentation corrections,
security or privacy fixes, and the identity gate itself.

## What the first release was meant to prove

Not that it is useful to anyone else, which is untested. What it is meant to
prove is narrower and checkable: that the identity a repository claims was
published by can be checked mechanically, before the push, across every
reachable ref including the ones a history rewrite cannot reach.
