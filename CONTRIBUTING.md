# Contributing

This is a small, personal tool, not a maintained framework. Contributions
are welcome, but keep expectations proportionate to that.

## Before opening a PR

- Match the existing style in the file you're touching rather than
  introducing a new convention.
- No new dependencies without a reason in the PR description, this tool is
  deliberately stdlib-only Python plus two `osascript`-run JS helpers.
- Run what the README lists under "Verify it works" before opening the
  PR, and say what you ran.
- No fabricated benchmarks or claims. If you didn't measure it, don't
  assert it.

## Bug reports

Open an issue with: what you ran, what you expected, what happened
instead, your macOS version, and whether `.calibration.json` existed at
the time (relevant for `dom`/`fill`/`select` issues).
