## Context

v1 ships a uniform regression gate: `compare` classifies each check NEW/REGRESSED/FIXED/STABLE/
INDETERMINATE and `edd run --baseline` exits non-zero if any check REGRESSED. The first consumer's
empirical data (two no-change K≥3 runs) showed deterministic invariants hold identically while
judge invariants flip — so judge regressions are noise, not signal. The consumer split its own gate
downstream (`deterministic block` vs `judge review`). This change promotes that split into the
engine. The pieces are already mostly present: `CheckResult.kind` is recorded on every run, so
`compare` (which iterates the current run's checks) already has the kind in hand.

## Goals / Non-Goals

**Goals:**
- A deterministic REGRESSED blocks the gate; a judge REGRESSED is advisory (reported, exit 0).
- `--strict` restores block-on-any for consumers who want it.
- Keep the change small and backward-compatible at the data layer.

**Non-Goals:** changing the fold/verdict logic, the "vanished check" case (a check in the baseline
but absent from the current run — still deferred), or anything about how scores are produced.

## Decisions

- **Default = deterministic-only gate (breaking).** The empirical finding is that judge-blocking is
  wrong, so the safe default must reflect it. We are pre-1.0 with a known consumer that already does
  this split, so a default behavior change is acceptable; documented in release notes. *Alternative
  considered:* keep block-on-any default + opt-in `--split`. Rejected — it leaves the unsafe default
  as the path of least resistance.
- **`kind` source = current run, with baseline fallback.** `compare` iterates current-run checks,
  each carrying `CheckResult.kind`, so the gate needs no baseline change to function. We still
  persist `kind` in `baseline.json` (cheap) so a future "vanished check" feature and audits have it.
  Reading a pre-v2 baseline (status-only) is tolerated.
- **`Comparison` API is additive.** Add `CheckComparison.kind`; add `Comparison.blocking_regressions`,
  `advisory_regressions`, `has_blocking_regression`. Keep `has_regression` meaning "any regressed"
  (informational). The CLI gate reads `has_blocking_regression` (or `has_regression` under `--strict`).
- **One new knob only:** `--strict`. No `--advisory-fail` or per-kind thresholds in v2.

## Risks / Trade-offs

- [A CI pipeline relying on judge regressions failing the build will stop failing] → mitigation:
  release note calls it out; `--strict` restores prior behavior exactly.
- [Older baselines lack `kind`] → mitigation: `compare` falls back to the current run's kind; no
  migration required.
- [Consumers who built their own downstream split now have redundancy] → harmless; they can drop
  their shim and rely on the engine, or keep it.
