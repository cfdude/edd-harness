## Why

The first real consumer surfaced an empirical finding: deterministic relational invariants are
stable run-to-run (at K ≥ 3 samples), but LLM-judge invariants flip **even with no change** — the
judge is itself stochastic. Today `compare` treats every REGRESSED check identically, so a judge
flip fails the gate exactly like a real deterministic regression. That makes the gate cry wolf and
pushes consumers to bolt their own split on downstream. v2 promotes the split into the engine:
a deterministic regression is do-not-ship; a judge regression is advisory.

## What Changes

- `compare` records each check's **scorer kind** (`deterministic` | `judge`) on every comparison
  item, and `Comparison` exposes `blocking_regressions` (deterministic) vs `advisory_regressions`
  (judge), plus `has_blocking_regression`. `has_regression` stays true if **any** check regressed
  (informational, unchanged meaning).
- **BREAKING:** `edd run --baseline` now exits non-zero only on a **blocking (deterministic)**
  regression. A **judge** regression is reported as `ADVISORY` and does **not** fail the gate.
  (Previously any REGRESSED check — including a judge flip — caused a non-zero exit.)
- New **`--strict`** flag on `edd run` restores the old behavior: treat all regressions (judge
  included) as blocking.
- `bless` persists each check's `kind` alongside its `status` in `baseline.json`. `compare` derives
  a check's kind from the current run, falling back to the baseline-recorded kind.
- `report` shows the blocking-vs-advisory split.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `results-baselines`: the comparison/regression-gate requirement now classifies by scorer kind
  (deterministic blocks, judge advisory, `--strict` blocks any); baseline persists `kind`;
  `Comparison` surfaces blocking vs advisory regressions.
- `eval-core`: `edd run` gains a `--strict` flag.

## Impact

- **Behavior change (BREAKING, pre-1.0):** `edd run --baseline` exit code no longer fails on judge
  regressions by default. Documented in the release notes; `--strict` restores the prior behavior.
- `baseline.json` gains a `kind` field per check. Backward-compatible: baselines blessed before v2
  (status-only) still load — `compare` uses the current run's kind when the baseline lacks it.
- Python API: `Comparison` gains additive fields; `CheckComparison` gains `kind`. No removals.
