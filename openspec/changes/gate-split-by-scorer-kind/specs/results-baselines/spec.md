## MODIFIED Requirements

### Requirement: Before/after comparison and regression gate
When a run is invoked with `--baseline` (`baseline=True`) and a blessed baseline exists for the current axis key, the engine SHALL join the current run to the baseline per `(scenario_id, scorer_name)` for the same axis key and classify each as NEW, REGRESSED, FIXED, STABLE, or INDETERMINATE. Each REGRESSED check SHALL be partitioned by scorer kind: a **deterministic** REGRESSED is **blocking**, a **judge** REGRESSED is **advisory**. `edd run --baseline` SHALL exit non-zero when there is any blocking (deterministic) regression; advisory (judge) regressions SHALL be reported but MUST NOT by themselves cause a non-zero exit. When `--strict` is supplied, ALL regressions (deterministic and judge) SHALL be treated as blocking. INDETERMINATE results MUST be excluded from regression accounting and MUST never be classified as REGRESSED. Comparison and the gate are owned by `edd run --baseline` (and reported by `edd report`); `bless` never gates.

#### Scenario: Deterministic regression blocks the gate
- **WHEN** `edd run --baseline` is invoked and a deterministic check that was `pass` in the baseline is now `fail`
- **THEN** it is classified REGRESSED + blocking and the run exits non-zero

#### Scenario: Judge regression is advisory
- **WHEN** `edd run --baseline` is invoked and a judge check that was `pass` in the baseline is now `fail` (verified true→false), with no deterministic regression
- **THEN** it is classified REGRESSED + advisory, reported as ADVISORY, and the run exits zero

#### Scenario: Strict mode blocks on a judge regression
- **WHEN** `edd run --baseline --strict` is invoked and a judge check regresses
- **THEN** the run exits non-zero

#### Scenario: Indeterminate is not a regression
- **WHEN** a check that was `pass` in the baseline is now indeterminate
- **THEN** it is excluded from regression accounting and does not cause a non-zero exit

#### Scenario: No baseline for the current axis
- **WHEN** `edd run --baseline` is invoked but the current `{model_under_test, judge_model}` axis key has no blessed baseline entry (e.g. a deliberate model or judge swap)
- **THEN** every check is classified NEW and the run does NOT exit non-zero (there is no prior baseline for that axis to regress against)

## ADDED Requirements

### Requirement: Comparison surfaces scorer kind and blocking vs advisory regressions
Each comparison item SHALL carry the scorer `kind` (`deterministic` | `judge`). The `Comparison` result SHALL expose `blocking_regressions` (deterministic REGRESSED), `advisory_regressions` (judge REGRESSED), and `has_blocking_regression`. `has_regression` SHALL remain true when ANY check regressed (deterministic or judge) and is informational; the default gate is driven by `has_blocking_regression`.

#### Scenario: Judge-only regression is non-blocking
- **WHEN** a comparison contains a judge REGRESSED and no deterministic REGRESSED
- **THEN** `has_blocking_regression` is false, `has_regression` is true, and `advisory_regressions` lists the judge check

### Requirement: Baseline persists scorer kind
`bless` SHALL record each check's `kind` alongside its `status` in `baseline.json`. `compare` SHALL derive a check's kind from the current run, falling back to the baseline-recorded kind when the check is absent from the current run. Baselines blessed before this capability (status only) SHALL still load.

#### Scenario: Bless records kind
- **WHEN** `bless` writes the baseline
- **THEN** each check entry includes its `kind` alongside `status`

#### Scenario: Pre-existing baseline without kind still loads
- **WHEN** a baseline entry has only `status` (no `kind`)
- **THEN** `compare` still classifies the check, using the current run's kind
