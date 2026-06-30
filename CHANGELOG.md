# Changelog

All notable changes to edd-harness are documented here. This project is pre-1.0; minor versions
may include breaking changes.

## [Unreleased]

### Changed — BREAKING

- **The regression gate now splits by scorer kind.** `edd run --baseline` exits non-zero only on a
  **deterministic** regression (the "blocking" signal). A **judge** regression is reported as
  `ADVISORY` and no longer fails the gate by default. This reflects the empirical finding that
  deterministic relational invariants are stable run-to-run while LLM-judge invariants flip even
  with no change. Pass **`--strict`** to restore the previous behavior (any regression blocks).

### Added

- `Comparison.has_blocking_regression`, `Comparison.blocking_regressions`, and
  `Comparison.advisory_regressions`; each `CheckComparison` now carries its scorer `kind`.
  `Comparison.has_regression` is retained, now meaning "any check regressed" (informational).
- `edd run --strict` flag.
- `bless` persists each check's `kind` alongside its `status` in `baseline.json`. Baselines blessed
  before this change (status only) still load.

### Migration

- CI that relied on judge regressions failing the build: add `--strict` to `edd run --baseline`.
- Code that gated on `compare_run(...).has_regression`: switch to `has_blocking_regression` for the
  deterministic-only gate, or keep `has_regression` if you want to react to any change.
