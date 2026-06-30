# Implementation Tasks — gate-split-by-scorer-kind

> TDD (RED→GREEN), one conventional commit per task. Engine stays domain-agnostic; tests use
> FakeJudge + a deterministic check — no consumer data.

## 1. Comparison carries scorer kind

- [ ] 1.1 `compare.py`: add `kind` to `CheckComparison`, sourced from the current run's
  `CheckResult.kind`; populate it for every item
- [ ] 1.2 `compare.py`: add `Comparison.blocking_regressions` (deterministic REGRESSED),
  `advisory_regressions` (judge REGRESSED), and `has_blocking_regression`; keep `has_regression`
  meaning "any regressed"

## 2. Baseline persists kind

- [ ] 2.1 `store.py`: `bless` writes `{status, kind}` per check; baseline reader tolerates pre-v2
  entries that have only `status`
- [ ] 2.2 `compare.py`: derive each check's kind from the current run (baseline-persisted `kind`
  is forward-looking for the deferred vanished-check feature; no fallback logic in v2)

## 3. Gate semantics + CLI

- [ ] 3.1 `cli.py`: `run --baseline` exits non-zero on `has_blocking_regression` only; judge
  regressions print as `ADVISORY` and do not gate
- [ ] 3.2 `cli.py`: add `--strict` — treat all regressions as blocking (exit non-zero on any)
- [ ] 3.3 `cli.py`: `report` / `_format_comparison` shows the blocking-vs-advisory split

## 4. Docs + verification

- [ ] 4.1 Docs: update `docs/integration-guide.md` (the split is now native — drop the "until the
  engine promotes the split, do it in your CI" caveat) + a release note for the BREAKING
  exit-code default change (and that `--strict` restores prior behavior)
- [ ] 4.2 Verification gate: full suite + ruff green; a generic synthetic test (FakeJudge that
  flips while a deterministic `check()` stays stable) asserts: judge-only regression → exit 0,
  deterministic regression → exit 1, `--strict` → exit 1 on the judge regression; domain-purity
  test still passes
