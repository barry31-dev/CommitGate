# Fixtures

The fixtures here are **synthetic**. They exist so the package can be run
end to end without a real repository, and they prove nothing about any real
project's history.

`fixtures/` is not a git repository and the package is not invoked against it.
The guard scripts and the test suite build their own throwaway repositories at
run time instead, because the behaviour under test is what git records, and a
checked-in repository would be a copy of someone's history.
